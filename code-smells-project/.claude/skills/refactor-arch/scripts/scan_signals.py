#!/usr/bin/env python3
"""Varredura determinística de sinais (Fase 2 da skill refactor-arch).

Cada sinal aponta arquivo:linha e o id do anti-pattern no catálogo
(references/antipatterns-catalog.md). Sinal não é achado: quem audita lê o
trecho, confirma ou descarta e decide a severidade final.

Também roda três detectores estruturais que regex de linha não pega:
- consulta ao banco dentro de laço (N+1);
- blocos de código repetidos (janela de linhas normalizadas);
- imports sem uso em Python (via ast).

Valores de segredo nunca são impressos: o literal é trocado por ***.

Uso: python3 scan_signals.py [RAIZ_DO_PROJETO] [--out ARQUIVO.json]
"""
import ast
import hashlib
import json
import os
import re
import sys

IGNORED_DIRS = {
    ".git", ".claude", "node_modules", ".venv", "venv", "env", "__pycache__",
    "instance", "dist", "build", "coverage", ".pytest_cache", "reports", ".refactor-arch",
}
LANG_BY_EXT = {".py": "py", ".js": "js", ".mjs": "js", ".cjs": "js", ".ts": "js"}

SQL_WORD = r"(?:SELECT|INSERT|UPDATE|DELETE|WHERE|VALUES|SET|AND|OR|LIKE|FROM)"
SECRET_NAME = r"(?:secret|passw|senha|pwd|pass\b|api_?key|apikey|token|private_?key|gateway_?key|\w*key\b)"

# (id do sinal, id do anti-pattern, linguagens, regex, descrição curta, segredo?)
SIGNALS = [
    ("sql-concat", "AP01", "py,js",
     re.compile(r"""(?i)(?:"[^"]*\b""" + SQL_WORD + r"""\b[^"]*"|'[^']*\b""" + SQL_WORD + r"""\b[^']*'|`[^`]*\b""" + SQL_WORD + r"""\b[^`]*`)\s*\+|\+\s*(?:"[^"]*|'[^']*|`[^`]*)\b""" + SQL_WORD + r"""\b"""),
     "SQL montado por concatenação", False),
    ("sql-fstring", "AP01", "py",
     re.compile(r"""(?i)\bf["'][^"']*\b(?:SELECT|INSERT|UPDATE|DELETE)\b[^"']*\{"""),
     "SQL montado com f-string", False),
    ("sql-template", "AP01", "js",
     re.compile(r"""(?i)`[^`]*\b(?:SELECT|INSERT|UPDATE|DELETE)\b[^`]*\$\{"""),
     "SQL montado com template string", False),
    ("sql-format", "AP01", "py",
     re.compile(r"""(?i)["'][^"']*\b(?:SELECT|INSERT|UPDATE|DELETE)\b[^"']*["']\s*(?:%|\.format\()"""),
     "SQL montado com % ou .format", False),
    ("sql-from-request", "AP02", "py,js",
     re.compile(r"""(?i)(?:\.get\(\s*["'](?:sql|query)["']|body\.(?:sql|query)\b|\[["']sql["']\])"""),
     "SQL recebido do cliente", False),
    ("execute-variable", "AP01", "py,js",
     re.compile(r"""\.(?:execute|exec|run|all|query)\(\s*(?:query|sql|q|stmt)\s*[,)]"""),
     "execução de SQL guardado em variável (conferir a origem)", False),
    ("hardcoded-secret", "AP03", "py,js",
     re.compile(r"""(?i)\b\w*""" + SECRET_NAME + r"""\w*["']?\]?\s*[:=]\s*(["'])(?!\s*\1)([^"'\n]{3,})\1"""),
     "credencial ou chave literal no código", True),
    ("live-key", "AP03", "py,js",
     re.compile(r"""\b(?:sk|pk|rk)_live_[A-Za-z0-9]{6,}"""),
     "chave de produção literal", True),
    ("debug-on", "AP04", "py,js",
     re.compile(r"""(?i)(?:\bdebug\s*=\s*True\b|["']DEBUG["']\]\s*=\s*True)"""),
     "modo debug ligado no código", False),
    ("bind-all", "AP04", "py,js",
     re.compile(r"""host\s*=\s*["']0\.0\.0\.0["']"""),
     "servidor escutando em todas as interfaces", False),
    ("weak-hash", "AP05", "py,js",
     re.compile(r"""(?i)(?:hashlib\.(?:md5|sha1)\(|createHash\(\s*["'](?:md5|sha1)["'])"""),
     "hash fraco (MD5/SHA1)", False),
    ("base64-password", "AP05", "py,js",
     re.compile(r"""(?i)(?:(?:pwd|pass|senha|password)\w*\)?\.toString\(\s*["']base64|b64encode\(\s*\w*(?:pwd|pass|senha))"""),
     "senha codificada em base64 (não é hash)", False),
    ("password-serialized", "AP05", "py,js",
     re.compile(r"""(?i)["'](?:senha|password|passwd|pass|pwd)["']\s*:\s*(?:row|self|user|u|usuario|data)\b"""),
     "senha incluída na serialização/resposta", False),
    ("password-compare-plain", "AP05", "py,js",
     re.compile(r"""(?i)(?:senha|password|pass)\s*=\s*['"]?\s*\+\s*\w+|AND\s+(?:senha|password)\s*="""),
     "senha comparada em texto puro na query", False),
    ("fake-auth", "AP06", "py,js",
     re.compile(r"""(?i)fake[-_ ]?(?:jwt|token)"""),
     "token de autenticação falso", False),
    ("admin-route", "AP06", "py,js",
     re.compile(r"""(?i)(?:route|add_url_rule|\.(?:get|post|put|patch|delete))\(\s*["'`][^"'`]*/(?:admin|reset|debug|internal)\b"""),
     "rota administrativa/destrutiva (conferir autenticação)", False),
    ("destructive-route", "AP06", "py,js",
     re.compile(r"""(?:\.delete\(\s*["'`]/|methods\s*=\s*\[[^\]]*["']DELETE["'])"""),
     "rota de exclusão (conferir autenticação e autorização)", False),
    ("sensitive-log", "AP07", "py,js",
     re.compile(r"""(?i)(?:console\.(?:log|info|warn|error)|print|logger\.\w+|logging\.\w+)\(.*(?:\bcc\b|card|cart[aã]o|cvv|\bpan\b|senha|password|token|\w*key\b|\bemail\b)"""),
     "dado sensível escrito em log", False),
    ("error-leak", "AP08", "py,js",
     re.compile(r"""(?:jsonify\(.*str\(\s*e\s*\)|["'](?:erro|error|detalhes|details)["']\s*:\s*str\(\s*e\s*\)|res\.\w+\(.*\berr(?:or)?\.(?:message|stack)\b)"""),
     "mensagem interna de exceção devolvida ao cliente", False),
    ("bare-except", "AP08", "py",
     re.compile(r"""^\s*except\s*:"""),
     "except sem tipo", False),
    ("broad-except", "AP08", "py",
     re.compile(r"""^\s*except\s+Exception\b"""),
     "except Exception genérico", False),
    ("ignored-callback-error", "AP08", "js",
     re.compile(r"""\(\s*err\s*(?:,\s*\w+\s*)?\)\s*=>\s*\{\s*$|function\s*\(\s*err\s*(?:,\s*\w+)?\)\s*\{\s*$"""),
     "callback com err (conferir se o erro é tratado)", False),
    ("global-state-py", "AP09", "py",
     re.compile(r"""^\s+global\s+\w+"""),
     "estado global mutável (global)", False),
    ("global-state-js", "AP09", "js",
     re.compile(r"""^(?:let|var)\s+\w+\s*=\s*(?:\{\}|\[\]|0|null|""|'')\s*;?\s*$"""),
     "estado global mutável no módulo", False),
    ("shared-connection", "AP09", "py",
     re.compile(r"""check_same_thread\s*=\s*False"""),
     "conexão SQLite compartilhada entre threads", False),
    ("cors-open", "AP10", "py,js",
     re.compile(r"""(?:\bCORS\(\s*app\s*\)|\bcors\(\s*\)|Access-Control-Allow-Origin["']?\s*,\s*["']\*)"""),
     "CORS aberto para qualquer origem", False),
    ("unguarded-cast", "AP11", "py",
     re.compile(r"""\b(?:int|float)\(\s*(?:request\.\w+|data\[|dados\[|\w+)\s*[\])]?\s*\)"""),
     "conversão de tipo de entrada (conferir try/400)", False),
    ("unvalidated-compare", "AP11", "py,js",
     re.compile(r"""(?i)\b(?:data|dados|body|item)\[["']\w+["']\]\s*[<>]=?\s*-?\d"""),
     "campo da requisição comparado sem checar tipo", False),
    ("string-method-on-input", "AP11", "js",
     re.compile(r"""\b(?:cc|card|pwd|email|eml|\w+)\.(?:startsWith|endsWith|includes|trim|toLowerCase)\("""),
     "método de string em valor de entrada (tipo garantido?)", False),
    ("fake-side-effect", "AP12", "py,js",
     re.compile(r"""(?i)(?:print|console\.log)\(\s*f?["'`](?:ENVIANDO|SENDING|NOTIFICA|EMAIL|SMS|PUSH)"""),
     "efeito colateral simulado com print/log", False),
    ("print-logging", "AP13", "py,js",
     re.compile(r"""^\s*(?:print\(|console\.log\()"""),
     "print/console.log como log", False),
    ("create-all-import", "AP14", "py",
     re.compile(r"""^\s*(?:db\.)?create_all\(\)"""),
     "criação de schema no import/boot", False),
    ("callback-nesting", "AP15", "js",
     re.compile(r"""^\s{16,}\S.*(?:function\s*\(|=>\s*\{)\s*$"""),
     "callback aninhado em 4+ níveis", False),
    ("dep-utcnow", "AP16", "py",
     re.compile(r"""\bdatetime\.utcnow\b|\butcnow\(\)"""),
     "datetime.utcnow() deprecated (Python 3.12+)", False),
    ("dep-utcfromtimestamp", "AP16", "py",
     re.compile(r"""\butcfromtimestamp\("""),
     "datetime.utcfromtimestamp() deprecated (Python 3.12+)", False),
    ("dep-query-get", "AP16", "py",
     re.compile(r"""\b[A-Z]\w*\.query\.get(?:_or_404)?\("""),
     "Model.query.get() legado (SQLAlchemy 2.0)", False),
    ("dep-model-query", "AP16", "py",
     re.compile(r"""\b[A-Z]\w*\.query\.(?!get\()"""),
     "interface Model.query legada (Flask-SQLAlchemy 3 / SQLAlchemy 2.0)", False),
    ("dep-flask", "AP16", "py",
     re.compile(r"""(?:before_first_request|flask\.json\.JSONEncoder|from flask import .*\b(?:escape|Markup)\b|json_encoder\s*=)"""),
     "API do Flask removida/deprecated", False),
    ("dep-python", "AP16", "py",
     re.compile(r"""(?:^\s*import (?:imp|distutils|asynchat|asyncore)\b|from collections import (?:Mapping|MutableMapping|Sequence)\b|pkg_resources|asyncio\.get_event_loop\(\))"""),
     "módulo/API Python removido ou deprecated", False),
    ("dep-node", "AP16", "js",
     re.compile(r"""(?:new Buffer\(|\breq\.param\(|\bapp\.del\(|\burl\.parse\(|\bfs\.exists\(|\butil\.is(?:Array|Date|Error)\(|crypto\.createCipher\(|res\.send\(\s*\d{3}\s*\)|res\.json\([^,()]+,\s*\d{3}\s*\)|\.substr\()"""),
     "API do Node/Express removida ou deprecated", False),
]

DB_CALL = re.compile(r"""(?:\.execute\(|\.query\.|\bquery\.get\(|db\.(?:get|all|run|each)\(|\.find(?:One|ById)?\(|session\.(?:get|execute|query)\(|\.(?:tasks|items|children)\b)""")
PY_LOOP = re.compile(r"""^(\s*)for\s+.+\s+in\s+.+:\s*$""")
JS_LOOP = re.compile(r"""(?:\.forEach\(|\.map\(|\bfor\s*\()""")


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            lang = LANG_BY_EXT.get(os.path.splitext(name)[1])
            if lang:
                yield os.path.join(dirpath, name), lang


def redact(line):
    line = re.sub(r"""(["'])(?:(?!\1).){3,}\1""", lambda m: m.group(1) + "***" + m.group(1), line)
    return re.sub(r"""\b(?:sk|pk|rk)_live_[A-Za-z0-9]+""", "***", line)


def is_comment(line, lang):
    s = line.strip()
    return s.startswith("#") if lang == "py" else s.startswith(("//", "*", "/*"))


def scan_lines(rel, lines, lang):
    hits = []
    for idx, line in enumerate(lines, 1):
        if is_comment(line, lang):
            continue
        for sid, ap, langs, rx, desc, secret in SIGNALS:
            if lang not in langs.split(","):
                continue
            m = rx.search(line)
            if not m:
                continue
            if sid == "hardcoded-secret":
                value = m.group(2)
                if re.match(r"(?i)^(?:\*+|x+|changeme|your[-_].*|<.*>|\$\{.*\}|%\(.*\)s|os\.environ.*)$", value):
                    continue
                if re.search(r"""(?i)(?:environ|getenv|process\.env)""", line):
                    continue
            if sid == "unguarded-cast" and not re.search(r"(?i)request|args|data|dados|body|param|query|priority|user_id|preco|quant", line):
                continue
            if sid == "string-method-on-input" and not re.search(r"\b(?:cc|card|pwd|eml|email|cid|usr)\.", line):
                continue
            if sid == "hardcoded-secret":
                code = line.strip().replace(m.group(2), "***")
            elif secret:
                code = redact(line.strip())
            else:
                code = line.strip()
            hits.append({"signal": sid, "antipattern": ap, "file": rel, "line": idx,
                         "description": desc, "code": code[:160]})
    return hits


def scan_loops_py(rel, lines):
    hits, stack = [], []
    for idx, line in enumerate(lines, 1):
        if not line.strip() or is_comment(line, "py"):
            continue
        indent = len(line) - len(line.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        m = PY_LOOP.match(line)
        if stack and DB_CALL.search(line):
            loop_line = stack[-1][1]
            hits.append({"signal": "query-in-loop", "antipattern": "AP17", "file": rel, "line": idx,
                         "description": f"consulta ao banco dentro de laço (laço na linha {loop_line})",
                         "code": line.strip()[:160]})
        if m:
            stack.append((indent, idx))
    return hits


def scan_loops_js(rel, lines):
    hits, loops, depth = [], [], 0
    for idx, line in enumerate(lines, 1):
        if is_comment(line, "js"):
            continue
        if JS_LOOP.search(line):
            loops.append((depth, idx))
        if loops and DB_CALL.search(line) and idx != loops[-1][1]:
            hits.append({"signal": "query-in-loop", "antipattern": "AP17", "file": rel, "line": idx,
                         "description": f"consulta ao banco dentro de laço (laço na linha {loops[-1][1]})",
                         "code": line.strip()[:160]})
        depth += line.count("{") - line.count("}")
        while loops and depth <= loops[-1][0] and idx != loops[-1][1]:
            loops.pop()
    return hits


def unused_imports_py(rel, source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.append(((a.asname or a.name).split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != "*":
                    imported.append((a.asname or a.name, node.lineno))
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    exported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            exported |= {e.value for e in getattr(node.value, "elts", []) if isinstance(e, ast.Constant)}
    if os.path.basename(rel) == "__init__.py":
        return []
    return [{"signal": "unused-import", "antipattern": "AP18", "file": rel, "line": line,
             "description": f"import sem uso: {name}", "code": name}
            for name, line in imported if name not in used and name not in exported]


def norm(line):
    s = re.sub(r"\s+", " ", line.strip())
    return s


def duplicate_blocks(files, window=5):
    index = {}
    for rel, lines in files.items():
        normed = [norm(line) for line in lines]
        for i in range(len(normed) - window + 1):
            chunk = normed[i:i + window]
            if any(len(c) < 8 for c in chunk) or any(c.startswith(("import ", "from ", "#", "//")) for c in chunk):
                continue
            key = hashlib.sha1("\n".join(chunk).encode()).hexdigest()
            index.setdefault(key, []).append((rel, i + 1))
    groups, seen = [], set()
    for key, locs in index.items():
        if len(locs) < 2:
            continue
        sig = tuple(locs)
        if any((r, l - d) in seen for r, l in locs for d in range(1, window)):
            for r, l in locs:
                seen.add((r, l))
            continue
        for r, l in locs:
            seen.add((r, l))
        groups.append(locs)
    hits = []
    for locs in groups:
        where = ", ".join(f"{r}:{l}" for r, l in locs)
        hits.append({"signal": "duplicate-block", "antipattern": "AP19", "file": locs[0][0], "line": locs[0][1],
                     "description": f"bloco de {window}+ linhas repetido em {len(locs)} lugares: {where}",
                     "code": ""})
    return hits


def repeated_literals(files):
    rx = re.compile(r"""\[\s*(?:["'][^"'\n]+["']\s*,\s*){2,}["'][^"'\n]+["']\s*\]|r?["']\^[^"'\n]{10,}["']""")
    seen = {}
    for rel, lines in files.items():
        for idx, line in enumerate(lines, 1):
            for m in rx.finditer(line):
                seen.setdefault(re.sub(r"\s+", "", m.group(0)), []).append((rel, idx))
    hits = []
    for lit, locs in seen.items():
        if len(locs) >= 2:
            where = ", ".join(f"{r}:{l}" for r, l in locs)
            hits.append({"signal": "repeated-literal", "antipattern": "AP20", "file": locs[0][0], "line": locs[0][1],
                         "description": f"lista/regex literal repetida {len(locs)}x: {where}", "code": lit[:80]})
    return hits


def main():
    args = sys.argv[1:]
    out = None
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i:i + 2]
    root = os.path.abspath(args[0] if args else ".")

    hits, sources = [], {}
    for path, lang in walk(root):
        rel = os.path.relpath(path, root)
        with open(path, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        lines = source.splitlines()
        sources[rel] = lines
        hits += scan_lines(rel, lines, lang)
        if lang == "py":
            hits += scan_loops_py(rel, lines)
            hits += unused_imports_py(rel, source)
        else:
            hits += scan_loops_js(rel, lines)
    hits += duplicate_blocks(sources)
    hits += repeated_literals(sources)
    hits.sort(key=lambda h: (h["antipattern"], h["file"], h["line"]))

    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"root": root, "total": len(hits), "signals": hits}, fh, ensure_ascii=False, indent=2)

    by_ap = {}
    for h in hits:
        by_ap.setdefault(h["antipattern"], []).append(h)
    print(f"{len(hits)} sinais em {len(sources)} arquivos ({root})")
    for ap in sorted(by_ap):
        group = by_ap[ap]
        print(f"\n[{ap}] {len(group)} sinal(is)")
        for h in group[:25]:
            code = f"  | {h['code']}" if h["code"] else ""
            print(f"  {h['file']}:{h['line']}  {h['signal']}: {h['description']}{code}")
        if len(group) > 25:
            print(f"  ... +{len(group) - 25} (ver JSON)")
    if out:
        print(f"\nJSON completo: {out}")


if __name__ == "__main__":
    main()

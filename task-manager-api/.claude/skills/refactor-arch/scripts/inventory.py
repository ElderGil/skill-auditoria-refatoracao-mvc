#!/usr/bin/env python3
"""Inventário determinístico de um projeto (Fase 1 da skill refactor-arch).

Levanta fatos, sem opinião: manifestos e dependências, linguagem dominante,
framework e banco prováveis, arquivos e linhas, endpoints, tabelas, pontos de
entrada e pastas de camada. A interpretação (arquitetura, domínio, grau de
organização) fica com quem lê o JSON.

Uso: python3 inventory.py [RAIZ_DO_PROJETO] [--out ARQUIVO.json]
Só usa a biblioteca padrão. Não escreve nada dentro do projeto.
"""
import json
import os
import re
import sys

IGNORED_DIRS = {
    ".git", ".claude", "node_modules", ".venv", "venv", "env", "__pycache__",
    "instance", "dist", "build", "coverage", ".pytest_cache", ".mypy_cache",
    ".idea", ".vscode", "reports", ".refactor-arch",
}
SOURCE_EXT = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".java": "Java", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".kt": "Kotlin",
}
MANIFESTS = [
    "requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "package.json",
    "go.mod", "pom.xml", "build.gradle", "Gemfile", "composer.json",
]
FRAMEWORKS = {
    "flask": "Flask", "django": "Django", "fastapi": "FastAPI", "express": "Express",
    "koa": "Koa", "fastify": "Fastify", "@nestjs/core": "NestJS", "hapi": "hapi",
    "@hapi/hapi": "hapi", "rails": "Rails", "laravel/framework": "Laravel",
    "spring-boot-starter-web": "Spring Boot", "github.com/gin-gonic/gin": "Gin",
}
DB_DEPS = {
    "sqlite3": "SQLite", "better-sqlite3": "SQLite", "flask-sqlalchemy": "SQLAlchemy (ORM)",
    "sqlalchemy": "SQLAlchemy (ORM)", "psycopg2": "PostgreSQL", "psycopg2-binary": "PostgreSQL",
    "pg": "PostgreSQL", "pymysql": "MySQL", "mysql2": "MySQL", "mongoose": "MongoDB",
    "pymongo": "MongoDB", "sequelize": "Sequelize (ORM)", "prisma": "Prisma (ORM)",
    "@prisma/client": "Prisma (ORM)", "typeorm": "TypeORM (ORM)",
}
DB_CODE_HINTS = [
    (re.compile(r"sqlite3\.connect\(|sqlite:///|new sqlite3\.Database|require\(['\"]sqlite3"), "SQLite"),
    (re.compile(r":memory:"), "SQLite em memória"),
    (re.compile(r"postgres(ql)?://"), "PostgreSQL"),
    (re.compile(r"mysql://"), "MySQL"),
    (re.compile(r"mongodb(\+srv)?://"), "MongoDB"),
]
LAYER_DIRS = {
    "models", "model", "entities", "domain", "routes", "router", "routers", "views",
    "controllers", "controller", "handlers", "services", "service", "repositories",
    "repository", "repos", "utils", "helpers", "middlewares", "middleware", "config",
    "schemas", "dto", "templates",
}

ROUTE_PATTERNS = [
    # Flask/Quart/FastAPI: @bp.route('/x', methods=['GET']) | @app.get('/x')
    re.compile(r"@(?P<obj>\w+)\.route\(\s*['\"](?P<path>[^'\"]+)['\"](?P<rest>[^)]*)\)"),
    re.compile(r"@(?P<obj>\w+)\.(?P<verb>get|post|put|patch|delete)\(\s*['\"](?P<path>[^'\"]+)['\"]"),
    # Flask add_url_rule("/x", "nome", func, methods=["GET"])
    re.compile(r"\.add_url_rule\(\s*['\"](?P<path>[^'\"]+)['\"](?P<rest>.*)\)"),
    # Express/Koa/Fastify: app.get('/x', ...) | router.post(`/x`, ...)
    re.compile(r"\b(?P<obj>\w+)\.(?P<verb>get|post|put|patch|delete|all)\(\s*['\"`](?P<path>/[^'\"`]*)['\"`]"),
]
METHODS_RE = re.compile(r"methods\s*=\s*\[([^\]]*)\]")
TABLE_PATTERNS = [
    re.compile(r"CREATE TABLE(?: IF NOT EXISTS)?\s+[`\"]?(\w+)", re.I),
    re.compile(r"__tablename__\s*=\s*['\"](\w+)['\"]"),
]
ENTRY_PATTERNS = [
    re.compile(r"if __name__ == ['\"]__main__['\"]"),
    re.compile(r"\.listen\("),
    re.compile(r"\bapp\.run\("),
]
PORT_RE = re.compile(r"port\s*[=:]\s*(\d{2,5})", re.I)


def walk_sources(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            ext = os.path.splitext(name)[1]
            if ext in SOURCE_EXT:
                yield os.path.join(dirpath, name)


def read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def parse_requirements(path):
    deps = {}
    for line in read_lines(path):
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"([A-Za-z0-9_.\-\[\]]+)\s*(.*)", line)
        if m:
            deps[m.group(1).lower().split("[")[0]] = m.group(2).strip() or "(sem versão fixada)"
    return deps


def parse_package_json(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    deps = {}
    for key in ("dependencies", "devDependencies"):
        for name, ver in (data.get(key) or {}).items():
            deps[name.lower()] = ver
    meta = {
        "main": data.get("main"),
        "scripts": data.get("scripts") or {},
        "engines": data.get("engines") or {},
        "dev_dependencies": sorted((data.get("devDependencies") or {}).keys()),
    }
    return deps, meta


def detect_routes(rel, lines):
    found = []
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "*")):
            continue
        for pat in ROUTE_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            gd = m.groupdict()
            path = gd.get("path")
            verb = gd.get("verb")
            obj = gd.get("obj") or ""
            if verb and obj in {"request", "req", "res", "os", "dict", "data", "args", "json", "params",
                                 "query", "headers", "session", "cache", "config", "environ", "self"}:
                continue
            if verb:
                methods = ["GET" if verb == "all" else verb.upper()]
            else:
                mm = METHODS_RE.search(gd.get("rest") or "")
                methods = [x.strip().strip("'\"").upper() for x in mm.group(1).split(",")] if mm else ["GET"]
            for method in methods:
                if method:
                    found.append({"method": method, "path": path, "file": rel, "line": idx})
            break
    return found


def main():
    args = sys.argv[1:]
    out = None
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i:i + 2]
    root = os.path.abspath(args[0] if args else ".")

    manifests = [m for m in MANIFESTS if os.path.exists(os.path.join(root, m))]
    deps, pkg_meta = {}, {}
    if "requirements.txt" in manifests:
        deps.update(parse_requirements(os.path.join(root, "requirements.txt")))
    if "package.json" in manifests:
        d, pkg_meta = parse_package_json(os.path.join(root, "package.json"))
        deps.update(d)

    files, lang_lines = [], {}
    endpoints, tables, entrypoints, db_hints, ports = [], [], [], set(), set()
    for path in walk_sources(root):
        rel = os.path.relpath(path, root)
        lines = read_lines(path)
        loc = sum(1 for line in lines if line.strip())
        lang = SOURCE_EXT[os.path.splitext(path)[1]]
        lang_lines[lang] = lang_lines.get(lang, 0) + loc
        files.append({"file": rel, "lines": len(lines), "loc": loc})
        endpoints.extend(detect_routes(rel, lines))
        text = "\n".join(lines)
        for pat in TABLE_PATTERNS:
            for m in pat.finditer(text):
                if m.group(1) not in tables:
                    tables.append(m.group(1))
        for pat, label in DB_CODE_HINTS:
            if pat.search(text):
                db_hints.add(label)
        for idx, line in enumerate(lines, 1):
            if any(p.search(line) for p in ENTRY_PATTERNS):
                entrypoints.append({"file": rel, "line": idx, "code": line.strip()[:120]})
                pm = PORT_RE.search(line)
                if pm:
                    ports.add(int(pm.group(1)))
            elif re.search(r"\bport\s*:\s*\d{2,5}", line):
                ports.add(int(PORT_RE.search(line).group(1)))

    language = max(lang_lines, key=lang_lines.get) if lang_lines else "desconhecida"
    frameworks = [{"name": FRAMEWORKS[d], "declared": deps[d]} for d in deps if d in FRAMEWORKS]
    databases = sorted({DB_DEPS[d] for d in deps if d in DB_DEPS} | db_hints)

    top_dirs = sorted(
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and d not in IGNORED_DIRS and not d.startswith(".")
    )
    layer_dirs = set()
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
        for d in dirnames:
            if d.lower() in LAYER_DIRS:
                layer_dirs.add(os.path.relpath(os.path.join(dirpath, d), root))

    seen, unique_endpoints = set(), []
    for ep in endpoints:
        key = (ep["method"], ep["path"])
        if key not in seen:
            seen.add(key)
            unique_endpoints.append(ep)

    result = {
        "root": root,
        "project": os.path.basename(root),
        "language": language,
        "lines_by_language": lang_lines,
        "manifests": manifests,
        "dependencies": deps,
        "package_json": pkg_meta,
        "frameworks": frameworks,
        "databases": databases,
        "source_files": len(files),
        "total_lines": sum(f["lines"] for f in files),
        "total_loc": sum(f["loc"] for f in files),
        "files": sorted(files, key=lambda f: -f["lines"]),
        "top_level_dirs": top_dirs,
        "layer_dirs": sorted(layer_dirs),
        "endpoints": unique_endpoints,
        "tables": tables,
        "entrypoints": entrypoints,
        "hardcoded_ports": sorted(ports),
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(payload)

    fw = ", ".join(f"{f['name']} {f['declared']}" for f in frameworks) or "nenhum detectado"
    print(f"Projeto:        {result['project']}")
    print(f"Linguagem:      {language}  {lang_lines}")
    print(f"Manifestos:     {', '.join(manifests) or 'nenhum'}")
    print(f"Framework:      {fw}")
    print(f"Banco:          {', '.join(databases) or 'nenhum detectado'}")
    print(f"Arquivos-fonte: {len(files)} ({result['total_lines']} linhas, {result['total_loc']} não vazias)")
    for f in result["files"][:8]:
        print(f"  {f['lines']:>5}  {f['file']}")
    print(f"Pastas de camada: {', '.join(result['layer_dirs']) or 'nenhuma'}")
    print(f"Tabelas:        {', '.join(tables) or 'nenhuma detectada'}")
    print(f"Endpoints:      {len(unique_endpoints)}")
    for ep in unique_endpoints:
        print(f"  {ep['method']:<6} {ep['path']:<40} {ep['file']}:{ep['line']}")
    print(f"Entrada:        " + "; ".join(f"{e['file']}:{e['line']}" for e in entrypoints))
    print(f"Portas fixas:   {result['hardcoded_ports'] or 'nenhuma'}")
    if out:
        print(f"JSON completo:  {out}")


if __name__ == "__main__":
    main()

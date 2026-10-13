#!/usr/bin/env python3
"""Baseline e validação de endpoints (Fases 1 e 3 da skill refactor-arch).

Sobe a aplicação numa CÓPIA temporária do projeto (o banco e os arquivos
originais nunca são tocados), numa porta livre, executa as requisições do
plano, registra status e formato das respostas e derruba o processo.

  baseline  roda o plano no código atual e grava o retrato do contrato
  compare   roda o mesmo plano no código refatorado e compara com o baseline

Saída: exit 0 = tudo certo; exit 2 = falha, com um bloco por violação
(requisição, esperado, obtido, como investigar). Exit 1 = erro de uso.

Uso:
  python3 smoke.py baseline --plan PLANO.json --project DIR --work DIR
  python3 smoke.py compare  --plan PLANO.json --project DIR --work DIR

Formato do plano: ver references/project-analysis.md (seção "Plano de fumaça").
"""
import argparse
import fnmatch
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_EXCLUDE = [".git", ".claude", "node_modules", ".venv", "venv", "__pycache__", "instance",
                   "*.db", "*.sqlite", "*.sqlite3", ".env", "reports", ".refactor-arch"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_in_use(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def fill(text, ctx):
    for key, value in ctx.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def pick(value, mode):
    """Campos do plano podem ser um valor único ou {"before": ..., "after": ...}."""
    if isinstance(value, dict) and ("before" in value or "after" in value):
        return value.get("before" if mode == "baseline" else "after")
    return value


def prepare_copy(project, dest, plan, ctx):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    patterns = DEFAULT_EXCLUDE + plan.get("copy_exclude", [])

    def ignore(_dir, names):
        return {n for n in names if any(fnmatch.fnmatch(n, p) for p in patterns)}

    shutil.copytree(project, dest, ignore=ignore, symlinks=True)
    links = plan.get("link") or {}
    if isinstance(links, list):
        links = {name: os.path.join(project, name) for name in links}
    for name, src in links.items():
        src = fill(src, ctx)
        if os.path.exists(src) and not os.path.exists(os.path.join(dest, name)):
            os.symlink(src, os.path.join(dest, name))


class App:
    def __init__(self, cmd, cwd, env, log_path, port, timeout):
        self.cmd, self.cwd, self.env = cmd, cwd, env
        self.log_path, self.port, self.timeout = log_path, port, timeout
        self.proc = None

    def start(self):
        log = open(self.log_path, "a")
        log.write(f"\n=== start: {self.cmd} (porta {self.port})\n")
        log.flush()
        self.proc = subprocess.Popen(self.cmd, shell=True, cwd=self.cwd, env=self.env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False
            if port_in_use(self.port):
                time.sleep(0.3)
                return True
            time.sleep(0.2)
        return False

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def log_tail(self, n=25):
        try:
            with open(self.log_path, encoding="utf-8", errors="replace") as fh:
                return "".join(fh.readlines()[-n:])
        except OSError:
            return ""


def call(port, req):
    url = f"http://127.0.0.1:{port}{req['path']}"
    data, headers = None, dict(req.get("headers") or {})
    if "json" in req:
        data = json.dumps(req["json"]).encode()
        headers.setdefault("Content-Type", "application/json")
    elif "raw" in req:
        data = req["raw"].encode()
    r = urllib.request.Request(url, data=data, method=req.get("method", "GET"), headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=req.get("timeout", 10)) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers.get("Content-Type", ""), err.read()
    except (urllib.error.URLError, ConnectionError, socket.timeout, TimeoutError) as err:
        return 0, "", str(err).encode()


def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        merged = {}
        for item in value[:5]:
            s = shape(item)
            if isinstance(s, dict):
                merged.update(s)
            else:
                return [s]
        return [merged] if merged else []
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    return "string"


def body_shape(ctype, raw):
    try:
        return "json", shape(json.loads(raw.decode("utf-8")))
    except (ValueError, UnicodeDecodeError):
        return ("html" if b"<html" in raw[:300].lower() or b"<!doctype" in raw[:300].lower() else "text"), None


def key_paths(s, prefix=""):
    paths = set()
    if isinstance(s, dict):
        for k, v in s.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.add(p)
            paths |= key_paths(v, p)
    elif isinstance(s, list) and s:
        paths |= key_paths(s[0], prefix + "[]")
    return paths


def run(mode, plan, project, work):
    run_dir = os.path.join(work, f"run-{mode}")
    fixed = pick(plan.get("port"), mode)
    port = int(fixed) if fixed else free_port()
    if fixed and port_in_use(port):
        print(f"[FALHA] porta fixa {port} já está em uso nesta máquina; libere a porta ou faça a app ler PORT.")
        return None, 2
    ctx = {"port": port, "work": work, "src": project, "run": run_dir}
    prepare_copy(project, run_dir, plan, ctx)
    env = dict(os.environ)
    env.update({k: fill(str(v), ctx) for k, v in (plan.get("env") or {}).items()})
    env.update({k: fill(str(v), ctx) for k, v in (pick(plan.get("env_mode"), mode) or {}).items()})
    env["PORT"] = str(port)
    log_path = os.path.join(work, f"app-{mode}.log")
    open(log_path, "w").close()

    for cmd in pick(plan.get("setup"), mode) or []:
        cmd = fill(cmd, ctx)
        res = subprocess.run(cmd, shell=True, cwd=run_dir, env=env, capture_output=True, text=True, timeout=300)
        with open(log_path, "a") as log:
            log.write(f"=== setup: {cmd} (exit {res.returncode})\n{res.stdout}{res.stderr}")
        if res.returncode != 0:
            print(f"[FALHA] setup '{cmd}' saiu com {res.returncode}\n{(res.stdout + res.stderr)[-1500:]}")
            return None, 2

    start_cmd = fill(pick(plan["start"], mode), ctx)
    app = App(start_cmd, run_dir, env, log_path, port, plan.get("boot_timeout", 30))
    results = []
    try:
        if not app.start():
            print(f"[FALHA] a aplicação não subiu em {plan.get('boot_timeout', 30)}s: {start_cmd}")
            print(app.log_tail())
            return None, 2
        print(f"[ok] aplicação no ar: {start_cmd} (porta {port})")
        for req in plan["requests"]:
            if not app.alive():
                print(f"  (processo caiu antes de '{req['id']}'; reiniciando para seguir)")
                app.stop()
                if not app.start():
                    print("[FALHA] não reiniciou depois da queda")
                    print(app.log_tail())
                    return None, 2
            status, ctype, raw = call(port, req)
            time.sleep(0.15)
            crashed = not app.alive()
            kind, sh = body_shape(ctype, raw)
            results.append({"id": req["id"], "method": req.get("method", "GET"), "path": req["path"],
                            "status": status, "body_kind": kind, "shape": sh, "crashed": crashed,
                            "probe": req.get("kind") == "probe",
                            "body_preview": raw[:160].decode("utf-8", "replace")})
            flag = " PROCESSO CAIU" if crashed else ""
            print(f"  {status or '---'}  {req.get('method', 'GET'):<6} {req['path']:<38} {req['id']}{flag}")
    finally:
        app.stop()
    return results, 0


def compare(plan, base, after):
    by_id = {r["id"]: r for r in base}
    violations = []
    for req, got in zip(plan["requests"], after):
        exp = by_id.get(req["id"])
        rule = req.get("after") or {}
        expected_status = rule.get("status", exp["status"] if exp else None)
        allowed = rule.get("status_in")
        problems = []
        if got["crashed"]:
            problems.append("o processo da aplicação caiu nesta requisição")
        if allowed:
            if got["status"] not in allowed:
                problems.append(f"status {got['status']}, esperado um de {allowed}")
        elif expected_status is not None and got["status"] != expected_status:
            problems.append(f"status {got['status']}, esperado {expected_status}"
                            + (" (baseline)" if "status" not in rule else " (mudança declarada no plano)"))
        if req.get("kind") != "probe" and exp and rule.get("shape") != "any" and got["status"] == exp["status"]:
            if exp["body_kind"] != got["body_kind"] and not rule.get("body_kind") == got["body_kind"]:
                problems.append(f"corpo virou {got['body_kind']}, era {exp['body_kind']}")
            elif exp["body_kind"] == "json":
                removed = set(rule.get("removed_keys", []))
                before_paths, after_paths = key_paths(exp["shape"]), key_paths(got["shape"])
                missing = sorted(p for p in before_paths - after_paths
                                 if p.split(".")[-1].replace("[]", "") not in removed and p not in removed
                                 and not any(p.startswith(r + ".") or p.startswith(r + "[]") for r in removed))
                if missing:
                    problems.append("campos do contrato sumiram: " + ", ".join(missing[:12]))
        if problems:
            violations.append({"id": req["id"], "request": f"{req.get('method', 'GET')} {req['path']}",
                               "problems": problems, "note": rule.get("note", ""),
                               "body_preview": got["body_preview"]})
    return violations


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["baseline", "compare"])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--project", default=".")
    ap.add_argument("--work", required=True)
    a = ap.parse_args()

    project, work = os.path.abspath(a.project), os.path.abspath(a.work)
    if work.startswith(project + os.sep):
        print("[ERRO] --work precisa ficar fora do projeto (a validação não escreve no projeto).")
        sys.exit(1)
    os.makedirs(work, exist_ok=True)
    with open(a.plan, encoding="utf-8") as fh:
        plan = json.load(fh)

    print(f"== smoke {a.mode}: {project}")
    results, code = run(a.mode, plan, project, work)
    if results is None:
        sys.exit(code)

    if a.mode == "baseline":
        out = os.path.join(work, "baseline.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        crashes = sum(r["crashed"] for r in results)
        errors = sum(1 for r in results if r["status"] >= 500 or r["status"] == 0)
        print(f"\nBaseline gravado: {out}")
        print(f"{len(results)} requisições | {errors} com 5xx/sem resposta | {crashes} derrubaram o processo")
        sys.exit(0)

    base_path = os.path.join(work, "baseline.json")
    if not os.path.exists(base_path):
        print("[ERRO] baseline.json não encontrado; rode o modo baseline antes da refatoração.")
        sys.exit(1)
    with open(base_path, encoding="utf-8") as fh:
        base = json.load(fh)
    violations = compare(plan, base, results)
    with open(os.path.join(work, "validation.json"), "w", encoding="utf-8") as fh:
        json.dump({"requests": results, "violations": violations}, fh, ensure_ascii=False, indent=2)

    print()
    if not violations:
        print(f"[VERDE] {len(results)} requisições conferidas contra o baseline: contrato preservado, "
              "mudanças declaradas confirmadas, nenhum processo caiu.")
        sys.exit(0)
    sys.stdout.flush()
    print(f"[VERMELHO] {len(violations)} violação(ões):", file=sys.stderr)
    for v in violations:
        print(f"\n- {v['request']}  ({v['id']})", file=sys.stderr)
        for p in v["problems"]:
            print(f"    problema: {p}", file=sys.stderr)
        if v["note"]:
            print(f"    declarado no plano: {v['note']}", file=sys.stderr)
        print(f"    resposta: {v['body_preview'][:160]}", file=sys.stderr)
        print("    como investigar: compare a rota/handler refatorado com o original; veja "
              f"{os.path.join(work, 'app-compare.log')}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()

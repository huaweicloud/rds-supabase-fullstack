#!/usr/bin/env python3
"""Mechanical verification gate for the rds-supabase-function-graph skill.

Independent verifier: security facts (401 on unauthenticated calls, CORS
origin exactness, version pinning) are checked by direct HTTP probes against
the deployed trigger URLs — never trusted from agent self-reporting.

Modes:
  check-contract                     validate .hwsupabase/functions.json
  check-stage --stage S [--verify]   stage order + trace enforcement (+ live
                                     HTTP probes when --verify is given)
  check-trace                        validate .hwsupabase/trace.jsonl format
  check-whitelist                    audit trace tool names per-stage
  check-version                      prod alias pinning + sha256 consistency

Credentials for --verify come from the process environment (FGS_TEST_JWT,
FGS_ALLOWED_ORIGIN) and are never logged. HTTPS is enforced except for
loopback hosts (local tests). stdlib-only; distributed with the skill.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

STAGES = [
    "fgs_env_ready",
    "functions_confirmed",
    "code_built",
    "deployed",
    "released",
    "integrated",
]
EXTRA_STAGES = ["rollback_switched", "rollback_verified", "decommissioned"]
ALL_STAGES = STAGES + EXTRA_STAGES
TRACE_REQUIRED = {"deployed", "released", "integrated"}

WHITELIST = {
    "fgs_env_ready": ["hcloud*"],
    "functions_confirmed": [],
    "code_built": ["node*", "npm*", "npx*"],
    "deployed": ["hcloud*", "zip*", "python3*", "node*"],
    "released": ["hcloud*", "fgs-gate*", "python3*"],
    "integrated": ["node*", "npm*", "npx*", "hcloud*", "fgs-gate*", "python3*"],
    "rollback_switched": ["hcloud*", "fgs-gate*", "python3*"],
    "rollback_verified": ["hcloud*", "fgs-gate*", "python3*"],
    "decommissioned": ["hcloud*", "fgs-gate*", "python3*"],
}

CRED_RE = re.compile(r"eyJ[A-Za-z0-9_-]{20,}|PRIVATE KEY|AKID")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
TIMEOUT = 10


def load_functions(base: Path):
    f = base / ".hwsupabase" / "functions.json"
    if not f.is_file():
        return None, None
    return json.loads(f.read_text(encoding="utf-8")), f


def https_or_loopback(url: str) -> bool:
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if p.scheme == "https":
        return True
    return p.scheme == "http" and (p.hostname or "") in LOOPBACK


def http_probe(url: str, method: str, headers: dict) -> tuple[int | None, dict]:
    """Return (status, response-headers). (None, {}) means unreachable."""
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=b"{}" if method in ("POST", "PUT") else None)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}
    except (urllib.error.URLError, OSError):
        return None, {}


def check_contract(base: Path) -> list[str]:
    missing: list[str] = []
    doc, path = load_functions(base)
    if doc is None:
        return [f"functions.json not found at {path}"]
    if doc.get("schema_version") != 1:
        missing.append("schema_version must be 1")
    if not isinstance(doc.get("webapp_ref"), (str, type(None))):
        missing.append("webapp_ref must be a string or null")
    fns = doc.get("functions")
    if not isinstance(fns, list):
        return missing + ["functions must be a list"]
    for i, fn in enumerate(fns):
        tag = f"functions[{i}]"
        if not isinstance(fn, dict):
            missing.append(f"{tag}: not an object")
            continue
        name = fn.get("name", "<unnamed>")
        if not isinstance(name, str) or not NAME_RE.match(name):
            missing.append(f"{tag}: invalid name {name!r}")
        for key in ("runtime", "handler", "obs_key"):
            if not isinstance(fn.get(key), str) or not fn.get(key):
                missing.append(f"{tag} {key}: non-empty string required")
        if not isinstance(fn.get("code_sha256"), str) or not SHA_RE.match(fn.get("code_sha256", "")):
            missing.append(f"{tag}: code_sha256 must be 64 lowercase hex")
        env_names = fn.get("env_names")
        if not isinstance(env_names, list) or not all(isinstance(e, str) and e for e in env_names):
            missing.append(f"{tag}: env_names must be a list of non-empty strings")
            env_names = []
        triggers = fn.get("triggers")
        has_apig = False
        if not isinstance(triggers, list):
            missing.append(f"{tag}: triggers must be a list")
        else:
            for j, tr in enumerate(triggers):
                if not isinstance(tr, dict) or tr.get("type") not in ("apig", "timer"):
                    missing.append(f"{tag} triggers[{j}]: type must be apig|timer")
                    continue
                if tr.get("type") == "apig":
                    has_apig = True
                    if tr.get("auth") != "none":
                        missing.append(f"{tag} triggers[{j}]: v1 requires auth=none (in-function JWT check)")
                    url = tr.get("url", "")
                    if not isinstance(url, str) or not https_or_loopback(url):
                        missing.append(f"{tag} triggers[{j}]: url must be https (loopback http exempt for tests)")
        if has_apig:
            for req_env in ("FGS_JWT_SECRET", "FGS_ALLOWED_ORIGINS"):
                if req_env not in env_names:
                    missing.append(f"{tag}: apig-triggered function must list env {req_env} (red line)")
        if fn.get("vpc") is not None:
            missing.append(f"{tag}: vpc must be null in v1")
        if fn.get("db_role") is not None:
            missing.append(f"{tag}: db_role must be null in v1")
        idem = fn.get("idempotency")
        if not isinstance(idem, dict) or not isinstance(idem.get("enabled"), bool) \
                or not isinstance(idem.get("key_field"), str):
            missing.append(f"{tag}: idempotency must be {{enabled: bool, key_field: str}}")
        versions = fn.get("versions")
        if not isinstance(versions, list):
            missing.append(f"{tag}: versions must be a list")
        else:
            prod = 0
            for j, v in enumerate(versions):
                if not isinstance(v, dict) or not isinstance(v.get("version"), str) or not v.get("version"):
                    missing.append(f"{tag} versions[{j}]: version must be a non-empty string")
                if not isinstance(v.get("sha256"), str) or not SHA_RE.match(v.get("sha256", "")):
                    missing.append(f"{tag} versions[{j}]: sha256 must be 64 lowercase hex")
                if v.get("alias") == "prod":
                    prod += 1
            if prod > 1:
                missing.append(f"{tag}: at most one version may carry alias 'prod'")
    stages = doc.get("stages")
    if not isinstance(stages, dict) or not isinstance(stages.get("history"), list):
        missing.append("stages.history must be a list")
    else:
        for j, h in enumerate(stages["history"]):
            if not isinstance(h, dict) or h.get("stage") not in ALL_STAGES \
                    or h.get("status") not in ("passed", "failed", "blocked") \
                    or not isinstance(h.get("at"), str):
                missing.append(f"stages.history[{j}]: bad entry (stage/status/at)")
    if CRED_RE.search(path.read_text(encoding="utf-8")):
        missing.append("credential-like string detected in functions.json")
    return missing


def check_stage(base: Path, stage: str, verify: bool) -> list[str]:
    missing: list[str] = []
    if stage not in STAGES:
        return [f"unknown stage {stage!r} (expected one of {STAGES})"]
    doc, _ = load_functions(base)
    if doc is None:
        return ["functions.json not found"]
    history = doc.get("stages", {}).get("history", [])
    passed = {h.get("stage") for h in history if isinstance(h, dict) and h.get("status") == "passed"}
    for required in STAGES[: STAGES.index(stage) + 1]:
        if required not in passed:
            missing.append(f"stage {required} has no passed record")
    if stage in TRACE_REQUIRED:
        missing += trace_has_ok(base, stage)
    if verify:
        missing += verify_live(base, doc)
    return missing


def trace_records(base: Path) -> list[dict]:
    f = base / ".hwsupabase" / "trace.jsonl"
    if not f.is_file():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"__malformed__": line})
    return out


def trace_has_ok(base: Path, stage: str) -> list[str]:
    recs = trace_records(base)
    if not any(isinstance(r, dict) and r.get("stage") == stage and r.get("status") == "ok" for r in recs):
        return [f"stage {stage} passed but no ok trace record for it (trace enforcement)"]
    return []


def verify_live(base: Path, doc: dict) -> list[str]:
    missing: list[str] = []
    jwt = _env("FGS_TEST_JWT")
    allowed_origin = _env("FGS_ALLOWED_ORIGIN")
    if jwt is None or allowed_origin is None:
        return ["--verify requires FGS_TEST_JWT and FGS_ALLOWED_ORIGIN in the process env"]
    bad_jwt = jwt.rsplit(".", 1)[0] + ".fgsgateinvalidsignature"
    for fn in doc.get("functions", []):
        if not isinstance(fn, dict):
            continue
        for tr in fn.get("triggers", []):
            if not (isinstance(tr, dict) and tr.get("type") == "apig"):
                continue
            url, name = tr.get("url", ""), fn.get("name", "<unnamed>")
            if not isinstance(url, str) or not https_or_loopback(url):
                missing.append(f"{name}: trigger url must be https (loopback exempt)")
                continue

            st, _ = http_probe(url, "POST", {"Content-Type": "application/json"})
            if st is None:
                missing.append(f"{name}: trigger url unreachable")
            elif st < 400:
                missing.append(f"{name}: unauthenticated request accepted with HTTP {st} (must be 401/403)")

            st, _ = http_probe(url, "POST", {"Content-Type": "application/json",
                                             "Authorization": f"Bearer {bad_jwt}"})
            if st is not None and st < 400:
                missing.append(f"{name}: invalid JWT accepted with HTTP {st} (must be 401/403)")

            st, _ = http_probe(url, "POST", {"Content-Type": "application/json",
                                             "Authorization": f"Bearer {jwt}",
                                             "Origin": allowed_origin})
            if st is None or st >= 400:
                missing.append(f"{name}: valid JWT call failed with HTTP {st}")

            st, hdrs = http_probe(url, "OPTIONS", {"Origin": allowed_origin,
                                                   "Access-Control-Request-Method": "POST"})
            if st is None or st >= 400:
                missing.append(f"{name}: CORS preflight failed with HTTP {st}")
            elif hdrs.get("access-control-allow-origin") != allowed_origin:
                missing.append(f"{name}: CORS Access-Control-Allow-Origin does not exactly match the allowed origin")

            st, _ = http_probe(url, "POST", {"Content-Type": "application/json",
                                             "Authorization": f"Bearer {jwt}",
                                             "Origin": "https://fgs-gate-invalid.origin.example"})
            if st is not None and st < 400:
                missing.append(f"{name}: disallowed origin accepted with HTTP {st}")
    return missing


def _env(name: str) -> str | None:
    import os
    return os.environ.get(name)


def check_trace(base: Path) -> list[str]:
    f = base / ".hwsupabase" / "trace.jsonl"
    if not f.is_file():
        return ["trace.jsonl not found"]
    missing: list[str] = []
    for i, rec in enumerate(trace_records(base)):
        if "__malformed__" in rec:
            missing.append(f"line {i + 1}: not valid JSON")
            continue
        if rec.get("stage") not in ALL_STAGES:
            missing.append(f"line {i + 1}: unknown stage {rec.get('stage')!r}")
        if rec.get("status") not in ("ok", "fail", "blocked"):
            missing.append(f"line {i + 1}: status must be ok|fail|blocked")
        if not isinstance(rec.get("tool"), str) or not rec.get("tool"):
            missing.append(f"line {i + 1}: tool must be a non-empty string")
        for key in ("at", "intent"):
            if not isinstance(rec.get(key), str):
                missing.append(f"line {i + 1}: {key} must be a string")
    return missing


def check_whitelist(base: Path) -> list[str]:
    f = base / ".hwsupabase" / "trace.jsonl"
    if not f.is_file():
        return ["trace.jsonl not found"]
    missing: list[str] = []
    for i, rec in enumerate(trace_records(base)):
        if "__malformed__" in rec or not isinstance(rec.get("tool"), str):
            continue
        stage, tool = rec.get("stage"), rec.get("tool")
        patterns = WHITELIST.get(stage)
        if patterns is None:
            missing.append(f"line {i + 1}: stage {stage!r} has no whitelist")
        elif not any(fnmatch.fnmatch(tool, p) for p in patterns):
            missing.append(f"line {i + 1}: tool {tool!r} not allowed at stage {stage!r}")
    return missing


def check_version(base: Path) -> list[str]:
    doc, _ = load_functions(base)
    if doc is None:
        return ["functions.json not found"]
    missing: list[str] = []
    for fn in doc.get("functions", []):
        if not isinstance(fn, dict):
            continue
        name = fn.get("name", "<unnamed>")
        versions = fn.get("versions", [])
        if not versions:
            missing.append(f"{name}: no released version recorded")
            continue
        prod = [v for v in versions if isinstance(v, dict) and v.get("alias") == "prod"]
        if not prod:
            missing.append(f"{name}: no version carries the 'prod' alias")
        elif prod[0].get("sha256") != fn.get("code_sha256"):
            missing.append(f"{name}: 'prod' alias sha256 != current code_sha256 (alias drift)")
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--path", default=".", help="project dir containing .hwsupabase/")
    sub = ap.add_subparsers(dest="mode", required=True)
    sub.add_parser("check-contract", parents=[common])
    cs = sub.add_parser("check-stage", parents=[common])
    cs.add_argument("--stage", required=True)
    cs.add_argument("--verify", action="store_true")
    for name in ("check-trace", "check-whitelist", "check-version"):
        sub.add_parser(name, parents=[common])
    args = ap.parse_args()
    base = Path(args.path).resolve()

    if args.mode == "check-contract":
        missing = check_contract(base)
    elif args.mode == "check-stage":
        missing = check_stage(base, args.stage, args.verify)
    elif args.mode == "check-trace":
        missing = check_trace(base)
    elif args.mode == "check-whitelist":
        missing = check_whitelist(base)
    else:
        missing = check_version(base)

    print(json.dumps({"verdict": "PASS" if not missing else "FAIL", "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())

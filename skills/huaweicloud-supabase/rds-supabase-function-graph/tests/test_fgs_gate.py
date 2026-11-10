"""fgs-gate test suite (18 cases) — mirrors the webapp-gate test discipline.

Runs the gate via subprocess against tmp fixtures; live --verify cases spin
up the local fake APIG (tests/fake_fgs.py).
"""
from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
GATE = SKILL_DIR / "scripts" / "fgs-gate.py"
FAKE = SKILL_DIR / "tests" / "fake_fgs.py"
PY = sys.executable

JWT = "header.payload.fgsfake"
ORIGIN = "https://www.example.com"
SHA = "a" * 64
SHA2 = "b" * 64


def fn_doc(**over):
    fn = {
        "name": "notify-transaction",
        "runtime": "Node.js18",
        "handler": "index.handler",
        "code_sha256": SHA,
        "obs_key": "artifacts/functions/notify-transaction/aaaaaaaa/pkg.zip",
        "env_names": ["FGS_JWT_SECRET", "FGS_ALLOWED_ORIGINS", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"],
        "vpc": None,
        "db_role": None,
        "triggers": [{"type": "apig", "auth": "none", "url": "https://gw.example.com/notify", "path": "/notify"}],
        "idempotency": {"enabled": True, "key_field": "request_id"},
        "versions": [{"version": "1", "sha256": SHA, "alias": "prod"}],
    }
    fn.update(over)
    return fn


def doc(**over):
    d = {
        "schema_version": 1,
        "webapp_ref": ".hwsupabase/webapp.json",
        "functions": [fn_doc()],
        "stages": {"history": [], "last_completed_stage": None},
    }
    d.update(over)
    return d


def stage_entry(stage, status="passed"):
    return {"stage": stage, "status": status, "at": "2026-11-11T08:00:00Z", "note": None}


def trace_line(tool="hcloud FGS CreateTrigger", stage="deployed", status="ok"):
    return json.dumps({"at": "2026-11-11T08:00:00Z", "stage": stage, "tool": tool,
                       "intent": "测试", "status": status, "note": None})


def setup(base: Path, d=None, trace=None):
    hs = base / ".hwsupabase"
    hs.mkdir(parents=True, exist_ok=True)
    (hs / "functions.json").write_text(json.dumps(d if d is not None else doc(), ensure_ascii=False), encoding="utf-8")
    if trace is not None:
        (hs / "trace.jsonl").write_text("\n".join(trace) + "\n", encoding="utf-8")


def run_gate(mode, base: Path, *extra, env_extra=None):
    env = {**os.environ, **(env_extra or {})}
    p = subprocess.run([PY, str(GATE), mode, "--path", str(base), *extra],
                       capture_output=True, text=True, env=env, timeout=60, check=False)
    return json.loads(p.stdout), p.returncode


# ---------- check-contract ----------

def test_contract_ok(tmp_path):
    setup(tmp_path)
    out, rc = run_gate("check-contract", tmp_path)
    assert (out["verdict"], rc) == ("PASS", 0)


def test_contract_bad_sha(tmp_path):
    setup(tmp_path, doc(functions=[fn_doc(code_sha256="XYZ")]))
    out, _rc = run_gate("check-contract", tmp_path)
    assert out["verdict"] == "FAIL" and any("code_sha256" in m for m in out["missing"])


def test_contract_secret_leak(tmp_path):
    d = doc()
    d["functions"][0]["env_names"].append("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.leak")
    setup(tmp_path, d)
    out, _ = run_gate("check-contract", tmp_path)
    assert out["verdict"] == "FAIL" and any("credential-like" in m for m in out["missing"])


def test_contract_apig_missing_jwt_env(tmp_path):
    setup(tmp_path, doc(functions=[fn_doc(env_names=["SUPABASE_URL"])]))
    out, _ = run_gate("check-contract", tmp_path)
    assert out["verdict"] == "FAIL" and any("FGS_JWT_SECRET" in m for m in out["missing"])


def test_contract_http_url_rejected(tmp_path):
    setup(tmp_path, doc(functions=[fn_doc(triggers=[{"type": "apig", "auth": "none",
                                                     "url": "http://gw.example.com/notify", "path": "/notify"}])]))
    out, _ = run_gate("check-contract", tmp_path)
    assert out["verdict"] == "FAIL" and any("https" in m for m in out["missing"])


def test_contract_vpc_must_be_null(tmp_path):
    setup(tmp_path, doc(functions=[fn_doc(vpc={"vpc_id": "x"})]))
    out, _ = run_gate("check-contract", tmp_path)
    assert out["verdict"] == "FAIL" and any("vpc" in m for m in out["missing"])


# ---------- check-stage ----------

def _staged_doc(upto: str):
    idx = ["fgs_env_ready", "functions_confirmed", "code_built", "deployed",
           "released", "integrated"].index(upto)
    return doc(stages={"history": [stage_entry(s) for s in
                                   ["fgs_env_ready", "functions_confirmed", "code_built", "deployed",
                                    "released", "integrated"][: idx + 1]], "last_completed_stage": upto})


def test_stage_order_fail(tmp_path):
    setup(tmp_path, _staged_doc("code_built"))
    out, _ = run_gate("check-stage", tmp_path, "--stage", "released")
    assert out["verdict"] == "FAIL" and any("deployed" in m for m in out["missing"])


def test_stage_ok_with_trace(tmp_path):
    setup(tmp_path, _staged_doc("deployed"), trace=[trace_line()])
    out, rc = run_gate("check-stage", tmp_path, "--stage", "deployed")
    assert (out["verdict"], rc) == ("PASS", 0)


def test_stage_deployed_without_trace_fail(tmp_path):
    setup(tmp_path, _staged_doc("deployed"))
    out, _ = run_gate("check-stage", tmp_path, "--stage", "deployed")
    assert out["verdict"] == "FAIL" and any("trace" in m for m in out["missing"])


def test_stage_exempt_no_trace(tmp_path):
    setup(tmp_path, _staged_doc("functions_confirmed"))
    out, rc = run_gate("check-stage", tmp_path, "--stage", "functions_confirmed")
    assert (out["verdict"], rc) == ("PASS", 0)


def test_stage_unknown_rejected(tmp_path):
    setup(tmp_path)
    out, _ = run_gate("check-stage", tmp_path, "--stage", "launched")
    assert out["verdict"] == "FAIL" and any("unknown stage" in m for m in out["missing"])


# ---------- check-trace / check-whitelist ----------

def test_trace_malformed_fail(tmp_path):
    setup(tmp_path, trace=["{not json"])
    out, _ = run_gate("check-trace", tmp_path)
    assert out["verdict"] == "FAIL" and any("not valid JSON" in m for m in out["missing"])


def test_whitelist_ok(tmp_path):
    setup(tmp_path, trace=[trace_line(tool="hcloud FGS CreateTrigger", stage="deployed")])
    out, rc = run_gate("check-whitelist", tmp_path)
    assert (out["verdict"], rc) == ("PASS", 0)


def test_whitelist_violation(tmp_path):
    setup(tmp_path, trace=[trace_line(tool="rm -rf /", stage="deployed")])
    out, _ = run_gate("check-whitelist", tmp_path)
    assert out["verdict"] == "FAIL" and any("not allowed" in m for m in out["missing"])


# ---------- check-version ----------

def test_version_ok(tmp_path):
    setup(tmp_path)
    out, rc = run_gate("check-version", tmp_path)
    assert (out["verdict"], rc) == ("PASS", 0)


def test_version_alias_drift(tmp_path):
    setup(tmp_path, doc(functions=[fn_doc(versions=[{"version": "1", "sha256": SHA2, "alias": "prod"}])]))
    out, _ = run_gate("check-version", tmp_path)
    assert out["verdict"] == "FAIL" and any("alias drift" in m for m in out["missing"])


def test_version_no_prod(tmp_path):
    setup(tmp_path, doc(functions=[fn_doc(versions=[{"version": "1", "sha256": SHA, "alias": "latest"}])]))
    out, _ = run_gate("check-version", tmp_path)
    assert out["verdict"] == "FAIL" and any("'prod'" in m for m in out["missing"])


# ---------- --verify (live, fake APIG) ----------

@contextlib.contextmanager
def fake_server_env(env_extra=None):
    env = {**os.environ, **(env_extra or {})}
    proc = subprocess.Popen([PY, str(FAKE), "--jwt", JWT, "--origin", ORIGIN, "--port", "0"],
                            stdout=subprocess.PIPE, text=True, env=env)
    port = int(proc.stdout.readline().strip())
    try:
        yield f"http://127.0.0.1:{port}/notify"
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)


@pytest.fixture()
def fake_server():
    with fake_server_env() as url:
        yield url


def _verify_doc(url):
    return _staged_doc("deployed") | {"functions": [fn_doc(
        triggers=[{"type": "apig", "auth": "none", "url": url, "path": "/notify"}])]}


def test_verify_all_good(tmp_path, fake_server):
    setup(tmp_path, _verify_doc(fake_server), trace=[trace_line()])
    out, rc = run_gate("check-stage", tmp_path, "--stage", "deployed", "--verify",
                       env_extra={"FGS_TEST_JWT": JWT, "FGS_ALLOWED_ORIGIN": ORIGIN})
    assert (out["verdict"], rc, out["missing"]) == ("PASS", 0, [])


def test_verify_broken_open_fail(tmp_path, fake_server):
    url = fake_server.replace("/notify", "/broken-open")
    setup(tmp_path, _verify_doc(url), trace=[trace_line()])
    out, _ = run_gate("check-stage", tmp_path, "--stage", "deployed", "--verify",
                      env_extra={"FGS_TEST_JWT": JWT, "FGS_ALLOWED_ORIGIN": ORIGIN})
    assert out["verdict"] == "FAIL" and any("unauthenticated" in m for m in out["missing"])


def test_verify_bad_cors_fail(tmp_path):
    with fake_server_env({"FGS_FAKE_BAD_CORS": "1"}) as url:
        setup(tmp_path, _verify_doc(url), trace=[trace_line()])
        out, _ = run_gate("check-stage", tmp_path, "--stage", "deployed", "--verify",
                          env_extra={"FGS_TEST_JWT": JWT, "FGS_ALLOWED_ORIGIN": ORIGIN})
    assert out["verdict"] == "FAIL" and any("CORS" in m for m in out["missing"])


def test_verify_missing_env(tmp_path, fake_server):
    setup(tmp_path, _verify_doc(fake_server), trace=[trace_line()])
    out, _ = run_gate("check-stage", tmp_path, "--stage", "deployed", "--verify")
    assert out["verdict"] == "FAIL" and any("FGS_TEST_JWT" in m for m in out["missing"])

#!/usr/bin/env python3
"""Mechanical gate checks for the rds-supabase-web-build workflow.

Stage completion is verified, not self-asserted: this tool validates the
.hwsupabase/webapp.json contract, stage progression, mandatory-gate
artifacts, trace hygiene and — with --verify — live cloud facts.

Usage:
  python webapp-gate.py <project_dir> check-contract
  python webapp-gate.py <project_dir> check-stage --stage instance_ready
  python webapp-gate.py <project_dir> check-stage --stage backend_deployed \
      --verify [--mcp-command "uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase"]
  python webapp-gate.py <project_dir> check-gate --number 3
  python webapp-gate.py <project_dir> check-trace

--verify performs machine verification against the live instance:
REST layer (always, via gateway REST API using SUPABASE_URL / ANON /
SERVICE_ROLE keys from the process environment) checks deployed-table
visibility and reachability; the optional MCP layer (--mcp-command) spawns
the data-plane MCP read-only to check table inventory, RLS status and
security advisors. Credentials are never logged.

Exit codes: 0 = PASS, 1 = FAIL (missing[] printed as JSON).
"""
import argparse
import http.client
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

STAGES = ["environment_ready", "requirements_confirmed", "instance_ready", "mcp_connected", "backend_deployed",
          "frontend_built", "local_verified", "hosting_published", "launched", "decommissioned"]
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA = re.compile(r"^[0-9a-f]{64}$")
CRED = re.compile(r"eyJ[A-Za-z0-9_-]{10,}|BEGIN (RSA|EC|OPENSSH) PRIVATE|AKID[A-Za-z0-9]{10,}")
BUCKET = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
GATE_FILES = {3: "3-rules-checklist.md", 4: "4-sdk-contract-checklist.md", 5: "5-local-test-report.md"}
CRED_ENV_NAMES = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]
# Stages whose completion requires at least one ok trace record (tool activity
# is mandatory there); conversation-only steps are exempt.
TRACE_REQUIRED = {"instance_ready", "mcp_connected", "backend_deployed", "frontend_built",
                  "hosting_published", "launched"}
# Per-stage tool allow-lists (shell wildcards matched against the trace tool
# string). Violations surface in check-whitelist; patterns are deliberately
# generous — prefixes group control-plane, data-plane, CLI and bookkeeping.
WHITELIST = {
    "environment_ready": ["diagnostics*", "uv*", "webapp*"],
    "requirements_confirmed": [],
    "instance_ready": ["list_*", "show_*", "plan_*", "create_*", "wait_*", "cancel_*",
                       "inspect_*", "reconcile_*", "deliver_*", "change_*", "update_*",
                       "hcloud*", "obsutil*", "diagnostics*", "uv*", "webapp*", "gate*"],
    "mcp_connected": ["get_project_url", "list_tables", "uv*", "webapp*", "gate*"],
    "backend_deployed": ["list_*", "get_*", "execute_sql", "webapp*", "gate*"],
    "frontend_built": ["list_*", "get_*", "npm*", "npx*", "node*", "webapp*", "gate*"],
    "local_verified": ["list_*", "get_*", "npm*", "npx*", "node*", "webapp*", "gate*"],
    "hosting_published": ["list_*", "show_*", "get_*", "update_*", "hcloud*", "obsutil*",
                          "npm*", "npx*", "uv*", "webapp*", "gate*"],
    "launched": ["get_*", "list_*", "*user*", "*admin*", "webapp*", "gate*"],
    "decommissioned": ["list_*", "show_*", "delete_*", "execute_sql", "hcloud*", "obsutil*",
                       "webapp*", "gate*"],
}


def scan_credential_like(value, path, missing):
    if isinstance(value, str) and CRED.search(value):
        missing.append(f"credential-like value at {path} (values are forbidden in webapp.json)")
    elif isinstance(value, dict):
        for key, item in value.items():
            scan_credential_like(item, f"{path}.{key}", missing)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            scan_credential_like(item, f"{path}[{index}]", missing)


def load_manifest(project_dir):
    path = Path(project_dir) / ".hwsupabase" / "webapp.json"
    if not path.is_file():
        return None, [f"missing {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"unreadable {path}: {exc}"]
    if not isinstance(data, dict):
        return None, ["webapp.json must be a JSON object"]
    return data, []


def check_contract(data, missing):
    if data.get("schema_version") != 1:
        missing.append("schema_version must be 1")
    for key in ("project", "stages"):
        if not isinstance(data.get(key), dict):
            missing.append(f"{key} must be an object")
    if isinstance(data.get("project"), dict) and not data["project"].get("name"):
        missing.append("project.name must be a non-empty string")
    caps = (data.get("project") or {}).get("baas_capabilities")
    if caps is not None:
        valid = {"database", "auth", "rpc", "storage", "realtime", "vector"}
        if not (isinstance(caps, list) and caps and all(isinstance(c, str) and c in valid for c in caps)):
            missing.append("project.baas_capabilities must be a non-empty list drawn from "
                           "database/auth/rpc/storage/realtime/vector")
    instance = data.get("instance")
    if instance is not None:
        if not isinstance(instance, dict):
            missing.append("instance must be an object or null")
        else:
            if not isinstance(instance.get("supabase_application_id"), str):
                missing.append("instance.supabase_application_id must be a string")
            if instance.get("source") not in ("created", "selected"):
                missing.append("instance.source must be 'created' or 'selected'")
            if not isinstance(instance.get("gateway_url"), str):
                missing.append("instance.gateway_url must be a string")
            if instance.get("credential_env_names") != CRED_ENV_NAMES:
                missing.append("instance.credential_env_names must be the fixed three-name list")
            if instance.get("credential_source") not in ("devkit", "protected_file"):
                missing.append("instance.credential_source must be 'devkit' or 'protected_file'")
            region = instance.get("region")
            if region is not None and not isinstance(region, str):
                missing.append("instance.region must be a string or null")
    obs = data.get("obs")
    if obs is not None:
        if not isinstance(obs, dict):
            missing.append("obs must be an object or null")
        else:
            if not (isinstance(obs.get("bucket_name"), str) and BUCKET.match(obs["bucket_name"])):
                missing.append("obs.bucket_name must be a valid bucket name "
                               "(3-63 chars, lowercase letters/digits/hyphens, letter-or-digit ends)")
            if obs.get("source") not in ("created", "selected"):
                missing.append("obs.source must be 'created' or 'selected'")
            if obs.get("source") == "created" and obs.get("naming_basis") not in ("app_name_slug", "app_name_slug_uuid"):
                missing.append("obs.naming_basis must be 'app_name_slug' or 'app_name_slug_uuid' when source is 'created'")
            if obs.get("source") == "selected" and obs.get("naming_basis") is not None:
                missing.append("obs.naming_basis must be null when source is 'selected'")
    mcp = data.get("mcp")
    if mcp is not None:
        if not isinstance(mcp, dict):
            missing.append("mcp must be an object or null")
        else:
            if mcp.get("registration_scope") != "project":
                missing.append("mcp.registration_scope must be 'project' "
                               "(project-level MCP registration only; user/system scope is forbidden)")
            paths = mcp.get("config_paths")
            if not isinstance(paths, dict):
                missing.append("mcp.config_paths must be an object")
            else:
                for plane in ("mgr", "data"):
                    value = paths.get(plane)
                    if value is None:
                        continue
                    if not (isinstance(value, str) and value.startswith(".") and not value.startswith("..")
                            and "~" not in value and not os.path.isabs(value)):
                        missing.append(f"mcp.config_paths.{plane} must be a project-relative path starting "
                                       "with '.' (absolute paths, '~' and '..' are forbidden)")
    storage = data.get("storage")
    if storage is not None:
        if not isinstance(storage, dict):
            missing.append("storage must be an object or null")
        else:
            if not (isinstance(storage.get("bucket_name"), str) and BUCKET.match(storage["bucket_name"])):
                missing.append("storage.bucket_name must be a valid bucket name "
                               "(3-63 chars, lowercase letters/digits/hyphens, letter-or-digit ends)")
            if storage.get("source") not in ("created", "selected"):
                missing.append("storage.source must be 'created' or 'selected'")
            if not isinstance(storage.get("connected"), bool):
                missing.append("storage.connected must be a boolean")
            obs_bucket = (data.get("obs") or {}).get("bucket_name")
            if isinstance(storage.get("bucket_name"), str) and storage["bucket_name"] == obs_bucket:
                missing.append("storage.bucket_name must differ from obs.bucket_name "
                               "(the frontend hosting bucket is public-read; reuse is a privilege escalation)")
    backend = data.get("backend")
    if backend is not None:
        if not isinstance(backend, dict) or not isinstance(backend.get("deployments"), list):
            missing.append("backend.deployments must be a list")
        else:
            if not isinstance(backend.get("teardown_ref"), str):
                missing.append("backend.teardown_ref must be a string (one-click cleanup script path)")
            for index, dep in enumerate(backend["deployments"]):
                if not isinstance(dep, dict):
                    missing.append(f"backend.deployments[{index}] must be an object")
                    continue
                if not isinstance(dep.get("batch_id"), str):
                    missing.append(f"backend.deployments[{index}].batch_id must be a string")
                if not (isinstance(dep.get("applied_at"), str) and TS.match(dep["applied_at"])):
                    missing.append(f"backend.deployments[{index}].applied_at must be RFC 3339 UTC")
                if not (isinstance(dep.get("objects"), list) and
                        all(isinstance(item, str) for item in dep["objects"])):
                    missing.append(f"backend.deployments[{index}].objects must be a string list")
                exposed = dep.get("exposed")
                if exposed is not None and not (isinstance(exposed, list) and
                                                all(isinstance(item, str) for item in exposed)):
                    missing.append(f"backend.deployments[{index}].exposed must be a string list or null")
                if exposed is not None and isinstance(exposed, list) and isinstance(dep.get("objects"), list):
                    unknown = [t for t in exposed if t not in dep["objects"]]
                    if unknown:
                        missing.append(f"backend.deployments[{index}].exposed must be a subset of objects: {unknown}")
                if not (isinstance(dep.get("source_sha256"), str) and SHA.match(dep["source_sha256"])):
                    missing.append(f"backend.deployments[{index}].source_sha256 must be lowercase sha256")
                if dep.get("status") not in ("applied", "failed", "rolled_back"):
                    missing.append(f"backend.deployments[{index}].status must be applied/failed/rolled_back")
    frontend = data.get("frontend")
    if frontend is not None:
        if not isinstance(frontend, dict):
            missing.append("frontend must be an object or null")
        else:
            for key in ("record_ref", "project_dir", "framework"):
                if not isinstance(frontend.get(key), str):
                    missing.append(f"frontend.{key} must be a string")
    stages = data.get("stages")
    if isinstance(stages, dict):
        if stages.get("last_completed_stage") not in STAGES:
            missing.append("stages.last_completed_stage must be a stage enum value")
        if not (isinstance(stages.get("updated_at"), str) and TS.match(stages["updated_at"])):
            missing.append("stages.updated_at must be RFC 3339 UTC")
        history = stages.get("history")
        if not isinstance(history, list):
            missing.append("stages.history must be a list")
        else:
            for index, event in enumerate(history):
                if not isinstance(event, dict) or event.get("stage") not in STAGES \
                        or event.get("status") not in ("passed", "failed", "blocked") \
                        or not (isinstance(event.get("at"), str) and TS.match(event["at"])):
                    missing.append(f"stages.history[{index}] must be {{stage,status,at,note}}")
    scan_credential_like(data, "webapp", missing)


def check_stage(data, stage, missing, project_dir=None):
    stages = data.get("stages") or {}
    reached = stages.get("last_completed_stage")
    if reached not in STAGES or stage not in STAGES:
        missing.append("invalid stage enum")
        return
    if STAGES.index(reached) < STAGES.index(stage):
        missing.append(f"last_completed_stage is '{reached}'; stage '{stage}' not reached yet")
    history = stages.get("history") or []
    if not any(isinstance(e, dict) and e.get("stage") == stage and e.get("status") == "passed"
               for e in history):
        missing.append(f"no passed history event for '{stage}'")
    if stage in ("instance_ready", "mcp_connected", "backend_deployed", "frontend_built",
                 "local_verified", "hosting_published", "launched") and not isinstance(data.get("instance"), dict):
        missing.append("instance section missing from instance_ready onward")
    if stage in ("instance_ready", "mcp_connected", "backend_deployed", "frontend_built",
                 "local_verified", "hosting_published", "launched") and not isinstance(data.get("obs"), dict):
        missing.append("obs section missing from instance_ready onward")
    if stage in ("instance_ready", "mcp_connected", "backend_deployed", "frontend_built",
                 "local_verified", "hosting_published", "launched"):
        caps = (data.get("project") or {}).get("baas_capabilities") or []
        if "storage" in caps:
            storage = data.get("storage")
            if not isinstance(storage, dict):
                missing.append("storage capability required by step 2 but storage section is missing")
            elif storage.get("connected") is not True:
                missing.append("storage.connected must be true from instance_ready onward "
                               "when the storage capability is required")
    if stage in ("instance_ready", "mcp_connected", "backend_deployed", "frontend_built",
                 "local_verified", "hosting_published", "launched"):
        mcp = data.get("mcp")
        if not isinstance(mcp, dict) or not isinstance((mcp.get("config_paths") or {}).get("mgr"), str):
            missing.append("mcp.config_paths.mgr must be a project-level config path from instance_ready onward")
    if stage in ("mcp_connected", "backend_deployed", "frontend_built", "local_verified",
                    "hosting_published", "launched"):
        mcp = data.get("mcp")
        if not isinstance(mcp, dict) or not isinstance((mcp.get("config_paths") or {}).get("data"), str):
            missing.append("mcp.config_paths.data must be a project-level config path from mcp_connected onward")
    if stage in ("hosting_published", "launched") and project_dir is not None:
        record_ref = (data.get("frontend") or {}).get("record_ref")
        if isinstance(record_ref, str):
            path = Path(project_dir) / record_ref
            if not path.is_file():
                missing.append(f"frontend.record_ref file not found: {record_ref}")
            else:
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    record = None
                if not isinstance(record, dict):
                    missing.append(f"frontend.record_ref is not a JSON object: {record_ref}")
                else:
                    stable = record.get("stable_url")
                    if not (isinstance(stable, str) and stable):
                        missing.append("stable_url missing in frontend record (required from hosting_published)")
                    else:
                        ssl = (data.get("instance") or {}).get("ssl_enabled")
                        if ssl is False and stable.startswith("https://"):
                            missing.append("stable_url is HTTPS while instance SSL is disabled — mixed content "
                                           "(HTTPS page calling the HTTP gateway) is blocked by browsers")
                        elif ssl is True and stable.startswith("http://"):
                            missing.append("stable_url is HTTP while instance SSL is enabled (HTTPS entry required)")
    if stage in ("frontend_built", "local_verified", "hosting_published", "launched") and not isinstance(data.get("frontend"), dict):
        missing.append("frontend section missing from frontend_built onward")
    if stage in ("backend_deployed", "frontend_built", "local_verified", "hosting_published", "launched"):
        deployments = (data.get("backend") or {}).get("deployments") or []
        if not deployments:
            missing.append("backend.deployments empty from backend_deployed onward")
        elif deployments[-1].get("status") != "applied":
            missing.append("latest backend deployment is not 'applied'")
        teardown = (data.get("backend") or {}).get("teardown_ref")
        if not isinstance(teardown, str):
            missing.append("backend.teardown_ref must be a string from backend_deployed onward")
        elif project_dir is not None:
            path = Path(project_dir) / teardown
            if not path.is_file():
                missing.append(f"backend.teardown_ref file not found: {teardown}")
            else:
                text = path.read_text(encoding="utf-8")
                for obj in deployments[-1].get("objects") or []:
                    bare = obj.split(".")[-1].strip('"')
                    if obj not in text and bare not in text:
                        missing.append(f"teardown does not cover deployed object '{obj}'")


def rule_stems():
    """Known best-practices rule file stems (sibling skill); None when unavailable."""
    override = os.getenv("WEBAPP_GATE_RULES_DIR")
    root = Path(override) if override else \
        Path(__file__).resolve().parent.parent / "rds-supabase-postgres-best-practices" / "references"
    if not root.is_dir():
        return None
    return sorted({p.stem for p in root.glob("*.md") if not p.name.startswith("_")})


def check_gate(data, number, project_dir, missing, summary):
    name = GATE_FILES.get(number)
    if not name:
        missing.append("gate number must be 3, 4 or 5")
        return
    path = Path(project_dir) / ".hwsupabase" / "gates" / name
    if not path.is_file():
        missing.append(f"missing mandatory-gate artifact {path} (see workflow-stages.md mandatory gates)")
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines()
             if line.strip().startswith(("-", "*")) and ("→" in line or "->" in line)]
    if number == 3:
        stems = rule_stems()
        if stems is None:
            if len(lines) < 5:
                missing.append(f"{name} needs at least 5 rule→location mapping bullets, found {len(lines)}")
            summary["rule_validation"] = "skipped: best-practices skill not found next to this skill"
            return
        valid, invalid = [], []
        for line in lines:
            reference = line.split("→")[0].split("->")[0]
            if any(re.search(rf"(^|[^0-9a-z]){re.escape(stem)}([^0-9a-z]|$)", reference, re.IGNORECASE) for stem in stems):
                valid.append(line)
            else:
                invalid.append(line.strip()[:60])
        if invalid:
            missing.append(f"{name} has mapping lines without a known rule file stem: {invalid[:3]}")
        if len(valid) < 5:
            missing.append(f"{name} needs at least 5 valid rule→location mappings (known stems), found {len(valid)}")
    elif number == 5:
        passed_lines = [line for line in lines
                        if re.match(r"^\s*-\s*T\d+", line) and ("→ passed" in line or "-> passed" in line)]
        failed_lines = [line.strip()[:60] for line in lines if "→ failed" in line or "-> failed" in line]
        if failed_lines:
            missing.append(f"{name} still has failed cases (fix and loop until all pass): {failed_lines[:3]}")
        if len(passed_lines) < 5:
            missing.append(f"{name} needs at least 5 passed L0 cases (T-numbered lines), found {len(passed_lines)}")
    elif len(lines) < 5:
        missing.append(f"{name} needs at least 5 mapping bullets, found {len(lines)}")


def load_trace(project_dir, missing):
    path = Path(project_dir) / ".hwsupabase" / "trace.jsonl"
    if not path.exists():
        return []
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as exc:
        missing.append(f"unreadable {path}: {exc}")
        return []
    records = []
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            missing.append(f"trace.jsonl line {index + 1} is not valid JSON")
            continue
        if not isinstance(record, dict) or record.get("stage") not in STAGES \
                or not isinstance(record.get("tool"), str) \
                or record.get("status") not in ("ok", "fail", "blocked") \
                or not (isinstance(record.get("at"), str) and TS.match(record["at"])):
            missing.append(f"trace.jsonl line {index + 1} must be {{at,stage,tool,intent,status,note}}")
            continue
        records.append(record)
    return records


def check_trace(project_dir, missing):
    load_trace(project_dir, missing)


def check_whitelist(project_dir, missing, summary):
    import fnmatch
    records = load_trace(project_dir, missing)
    violations, per_stage = [], {}
    for record in records:
        stage, tool = record["stage"], record["tool"]
        per_stage.setdefault(stage, set()).add(tool)
        allowed = WHITELIST.get(stage)
        if allowed is None:
            violations.append(f"unknown stage '{stage}' in trace (tool: {tool})")
        elif not any(fnmatch.fnmatch(tool, pattern) for pattern in allowed):
            violations.append(f"stage {stage}: tool '{tool}' is outside the stage allow-list")
    for violation in sorted(set(violations)):
        missing.append(violation)
    summary["whitelist"] = {stage: sorted(tools) for stage, tools in sorted(per_stage.items())}


def latest_deployment(data):
    deployments = (data.get("backend") or {}).get("deployments") or []
    return deployments[-1] if deployments else None


def table_name(entry):
    return entry.split(".")[-1].strip().strip('"')


def http_get(url, headers, timeout=15, allow_http=False):
    u = urlsplit(url)
    local = u.hostname in ("127.0.0.1", "localhost")
    if u.scheme == "https":
        conn = http.client.HTTPSConnection(u.hostname, u.port, timeout=timeout)
    elif u.scheme == "http" and (local or allow_http):
        # HTTP is the intended access mode when the instance has SSL disabled
        # (webapp.json instance.ssl_enabled is false); loopback stays exempt
        # for tests. Everything else must be HTTPS.
        conn = http.client.HTTPConnection(u.hostname, u.port, timeout=timeout)
    else:
        raise ValueError("gateway URL must be HTTPS (HTTP allowed only when instance SSL is disabled, or for loopback tests)")
    route = u.path + (f"?{u.query}" if u.query else "")
    conn.request("GET", route, headers=headers)
    response = conn.getresponse()
    raw = response.read(1048576)
    status = response.status
    conn.close()
    return status, raw


def verify_rest(data, missing, summary):
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    anon = os.getenv("SUPABASE_ANON_KEY", "")
    service = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    for name, value in (("SUPABASE_URL", base), ("SUPABASE_ANON_KEY", anon),
                        ("SUPABASE_SERVICE_ROLE_KEY", service)):
        if not value:
            missing.append(f"--verify requires environment variable {name}")
    if missing:
        return
    allow_http = ((data.get("instance") or {}).get("ssl_enabled") is False)
    deployment = latest_deployment(data)
    if not deployment:
        summary["rest"] = {"note": "no deployments to verify"}
        return
    try:
        status, raw = http_get(f"{base}/rest/v1/", {"apikey": service, "Authorization": f"Bearer {service}"},
                             allow_http=allow_http)
        if status != 200:
            missing.append(f"REST root unreachable with service key (status {status})")
            return
        paths = (json.loads(raw).get("paths") or {})
        rest_tables = {p.strip("/").strip('"') for p in paths if not p.strip("/").startswith("rpc/")}
    except Exception as exc:
        missing.append(f"REST verification failed: {exc}")
        return
    deployed = [table_name(o) for o in deployment.get("objects") or []]
    absent = [t for t in deployed if t not in rest_tables]
    for table in absent:
        missing.append(f"deployed table '{table}' is not visible via REST (service key)")
    checked, reachable = [], []
    for table in deployed:
        try:
            status, _ = http_get(f"{base}/rest/v1/{table}?select=*&limit=1",
                                  {"apikey": service, "Authorization": f"Bearer {service}"}, allow_http=allow_http)
            if status != 200:
                missing.append(f"table '{table}' not reachable via REST with service key (status {status})")
            else:
                reachable.append(table)
            checked.append(table)
        except Exception as exc:
            missing.append(f"REST check failed for '{table}': {exc}")
    exposed = [table_name(t) for t in (deployment.get("exposed") or [])]
    anon_ok, anon_denied = [], []
    for table in exposed:
        try:
            status, _ = http_get(f"{base}/rest/v1/{table}?select=*&limit=1",
                                  {"apikey": anon, "Authorization": f"Bearer {anon}"}, allow_http=allow_http)
            (anon_ok if status == 200 else anon_denied).append((table, status))
            if status != 200:
                missing.append(f"exposed table '{table}' not anonymously reachable (status {status})")
        except Exception as exc:
            missing.append(f"anon REST check failed for '{table}': {exc}")
    summary["rest"] = {"rest_tables": len(rest_tables), "deployed": len(deployed),
                       "reachable": reachable, "anon_ok": anon_ok, "anon_denied": anon_denied}


def mcp_spawn(command):
    argv = shlex.split(command)
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=dict(os.environ))
    return proc


def mcp_send(proc, message):
    proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
    proc.stdin.flush()


def mcp_recv(proc, request_id, deadline_seconds=25.0):
    import time
    deadline = time.monotonic() + deadline_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("MCP response timeout")
        line = proc.stdout.readline()
        if not line:
            raise TimeoutError("MCP process closed stdout")
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(message, dict) and message.get("id") == request_id:
            return message


def mcp_tool(proc, counter, name, arguments):
    request_id = next(counter)
    mcp_send(proc, {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
    message = mcp_recv(proc, request_id)
    if "error" in message:
        raise RuntimeError(f"MCP tool error: {message['error']}")
    content = (message.get("result") or {}).get("content") or []
    text = next((block.get("text") for block in content if isinstance(block, dict) and "text" in block), None)
    structured = (message.get("result") or {}).get("structuredContent")
    if structured is not None:
        return structured
    if text is None:
        raise RuntimeError("MCP tool returned no content")
    return json.loads(text)


def row_field(row, *names):
    for name in names:
        if name in row:
            return row[name]
    return None


def verify_mcp(command, data, missing, summary):
    deployment = latest_deployment(data)
    if not deployment:
        summary["mcp"] = {"note": "no deployments to verify"}
        return
    proc = None
    watchdog = None
    try:
        proc = mcp_spawn(command)
        import threading
        watchdog = threading.Timer(120.0, proc.kill)
        watchdog.start()
        counter = iter(range(1, 10_000))
        mcp_send(proc, {"jsonrpc": "2.0", "id": next(counter), "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "webapp-gate", "version": "0.5"}}})
        mcp_recv(proc, 1)
        mcp_send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        rows = mcp_tool(proc, counter, "list_tables", {})
        if not isinstance(rows, list):
            rows = rows.get("tables") if isinstance(rows, dict) else []
        public = {table_name(str(row_field(r, "name", "tablename", "table") or ""))
                  for r in rows if str(row_field(r, "schema", "schemaname") or "public") == "public"}
        deployed = [table_name(o) for o in deployment.get("objects") or []]
        for table in deployed:
            if table not in public:
                missing.append(f"deployed table '{table}' not found by data-plane MCP list_tables")
        exposed = [table_name(t) for t in (deployment.get("exposed") or [])]
        rls_enabled = []
        for table in exposed:
            status_rows = mcp_tool(proc, counter, "get_rls_status", {"schema": "public", "table": table})
            if not isinstance(status_rows, list):
                status_rows = [status_rows]
            row = next((r for r in status_rows
                        if table_name(str(row_field(r, "table", "tablename", "name") or "")) == table), None)
            enabled = bool(row_field(row or {}, "row_security", "rowsecurity", "rls_enabled",
                                      "enabled", "relrowsecurity")) if row else False
            policies = row_field(row or {}, "policies", "policy_count", "policies_count") if row else None
            if not enabled:
                missing.append(f"exposed table '{table}' has RLS disabled (machine-verified)")
            elif not policies or int(policies) < 1:
                missing.append(f"exposed table '{table}' has RLS enabled but zero policies")
            else:
                rls_enabled.append(table)
        advisors = mcp_tool(proc, counter, "get_advisors", {"type": "security"})
        issues = advisors.get("issues") if isinstance(advisors, dict) else advisors
        issues = issues if isinstance(issues, list) else []
        hits = []
        for issue in issues:
            affected = str(row_field(issue if isinstance(issue, dict) else {}, "name", "object", "table") or "")
            if any(table in affected for table in deployed):
                hits.append(affected or str(issue)[:40])
        for hit in hits:
            missing.append(f"security advisor reports an issue on a deployed table: {hit}")
        summary["mcp"] = {"public_tables": len(public), "rls_enabled": rls_enabled,
                          "advisor_issues_total": len(issues), "advisor_hits": hits}
    except Exception as exc:
        missing.append(f"MCP verification failed: {exc}")
    finally:
        if watchdog:
            watchdog.cancel()
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


def report(verdict, payload=None):
    print(json.dumps({"verdict": verdict, **(payload or {})}, ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("mode", choices=("check-contract", "check-stage", "check-gate",
                                         "check-trace", "check-whitelist"))
    parser.add_argument("--stage")
    parser.add_argument("--number", type=int)
    parser.add_argument("--verify", action="store_true",
                        help="machine-verify live facts (REST layer; add --mcp-command for RLS/advisors)")
    parser.add_argument("--mcp-command",
                        help="data-plane MCP launch command, e.g. "
                             "'uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase'")
    args = parser.parse_args()
    summary = {}
    if args.mode in ("check-trace", "check-whitelist"):
        missing, summary = [], {}
        if args.mode == "check-whitelist":
            check_whitelist(args.project_dir, missing, summary)
        else:
            check_trace(args.project_dir, missing)
        return report("PASS" if not missing else "FAIL", {"missing": missing, **summary})
    data, load_errors = load_manifest(args.project_dir)
    if load_errors:
        return report("FAIL", {"missing": load_errors})
    missing = []
    if args.mode == "check-contract":
        check_contract(data, missing)
    elif args.mode == "check-stage":
        if not args.stage:
            return report("FAIL", {"missing": ["--stage is required for check-stage"]})
        check_stage(data, args.stage, missing, project_dir=args.project_dir)
        check_contract(data, missing)
        if args.stage in TRACE_REQUIRED:
            records = load_trace(args.project_dir, missing)
            if not any(r["stage"] == args.stage and r["status"] == "ok" for r in records):
                missing.append(f"trace enforcement: no ok trace records for stage '{args.stage}'")
        if args.verify:
            verify_rest(data, missing, summary)
            if args.mcp_command:
                verify_mcp(args.mcp_command, data, missing, summary)
            else:
                summary.setdefault("mcp", {"note": "not machine-verified (no --mcp-command); "
                                                   "RLS/advisors remain agent-verified"})
    elif args.mode == "check-gate":
        check_gate(data, args.number, args.project_dir, missing, summary)
    return report("PASS" if not missing else "FAIL", {"missing": missing, **summary})


if __name__ == "__main__":
    sys.exit(main())

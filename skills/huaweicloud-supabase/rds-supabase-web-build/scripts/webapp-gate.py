#!/usr/bin/env python3
"""Mechanical gate checks for the rds-supabase-web-build workflow.

Stage completion is verified, not self-asserted: this tool validates the
.hwsupabase/webapp.json contract, stage progression, mandatory-gate
artifacts and trace hygiene. Read-only; Python stdlib only; travels with
the skill directory.

Usage:
  python webapp-gate.py <project_dir> check-contract
  python webapp-gate.py <project_dir> check-stage --stage instance_ready
  python webapp-gate.py <project_dir> check-gate --number 3
  python webapp-gate.py <project_dir> check-trace

Exit codes: 0 = PASS, 1 = FAIL (missing[] printed as JSON).
"""
import argparse
import json
import re
import sys
from pathlib import Path

STAGES = ["requirements_confirmed", "instance_ready", "mcp_connected", "backend_deployed",
          "frontend_built", "hosting_published", "launched", "decommissioned"]
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA = re.compile(r"^[0-9a-f]{64}$")
CRED = re.compile(r"eyJ[A-Za-z0-9_-]{10,}|BEGIN (RSA|EC|OPENSSH) PRIVATE|AKID[A-Za-z0-9]{10,}")
GATE_FILES = {3: "3-rules-checklist.md", 4: "4-sdk-contract-checklist.md"}
CRED_ENV_NAMES = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]


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
    if isinstance(data.get("project"), dict):
        if not isinstance(data["project"].get("name"), str) or not data["project"].get("name"):
            missing.append("project.name must be a non-empty string")
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
    backend = data.get("backend")
    if backend is not None:
        if not isinstance(backend, dict) or not isinstance(backend.get("deployments"), list):
            missing.append("backend.deployments must be a list")
        else:
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


def check_stage(data, stage, missing):
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
                 "hosting_published", "launched"):
        if not isinstance(data.get("instance"), dict):
            missing.append("instance section missing for a post-① stage")
    if stage in ("frontend_built", "hosting_published", "launched"):
        if not isinstance(data.get("frontend"), dict):
            missing.append("frontend section missing for a post-④ stage")
    if stage in ("backend_deployed", "frontend_built", "hosting_published", "launched"):
        deployments = (data.get("backend") or {}).get("deployments") or []
        if not deployments:
            missing.append("backend.deployments empty for a post-③ stage")
        elif deployments[-1].get("status") != "applied":
            missing.append("latest backend deployment is not 'applied'")


def check_gate(data, number, project_dir, missing):
    name = GATE_FILES.get(number)
    if not name:
        missing.append("gate number must be 3 or 4")
        return
    path = Path(project_dir) / ".hwsupabase" / "gates" / name
    if not path.is_file():
        missing.append(f"missing mandatory-gate artifact {path} (see workflow-stages ③/④)")
        return
    mappings = [line for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith(("-", "*")) and ("→" in line or "->" in line)]
    if len(mappings) < 5:
        missing.append(f"{name} needs at least 5 rule→location mapping bullets, found {len(mappings)}")


def check_trace(project_dir, missing):
    path = Path(project_dir) / ".hwsupabase" / "trace.jsonl"
    if not path.exists():
        return
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as exc:
        missing.append(f"unreadable {path}: {exc}")
        return
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


def report(verdict, payload=None):
    print(json.dumps({"verdict": verdict, **(payload or {})}, ensure_ascii=False, indent=2))
    return 0 if verdict == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("mode", choices=("check-contract", "check-stage", "check-gate", "check-trace"))
    parser.add_argument("--stage")
    parser.add_argument("--number", type=int)
    args = parser.parse_args()
    if args.mode == "check-trace":
        missing = []
        check_trace(args.project_dir, missing)
        return report("PASS" if not missing else "FAIL", {"missing": missing})
    data, load_errors = load_manifest(args.project_dir)
    if load_errors:
        return report("FAIL", {"missing": load_errors})
    missing = []
    if args.mode == "check-contract":
        check_contract(data, missing)
    elif args.mode == "check-stage":
        if not args.stage:
            return report("FAIL", {"missing": ["--stage is required for check-stage"]})
        check_stage(data, args.stage, missing)
        check_contract(data, missing)
    elif args.mode == "check-gate":
        check_gate(data, args.number, args.project_dir, missing)
    return report("PASS" if not missing else "FAIL", {"missing": missing})


if __name__ == "__main__":
    sys.exit(main())

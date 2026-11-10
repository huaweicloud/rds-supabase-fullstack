"""Minimal fake data-plane MCP server for webapp-gate --verify tests.

Speaks newline-delimited JSON-RPC 2.0 over stdio. Behavior knobs:
  FAKE_RLS_ENABLED (default "1"), FAKE_ADVISOR_HIT (default "0"),
  FAKE_TABLES (default "posts,users,comments")
"""
import json
import os
import sys

TABLES = [t.strip() for t in os.getenv("FAKE_TABLES", "posts,users,comments").split(",") if t.strip()]
RLS_ON = os.getenv("FAKE_RLS_ENABLED", "1") == "1"
ADVISOR_HIT = os.getenv("FAKE_ADVISOR_HIT", "0") == "1"
EXPOSED = {t.strip() for t in os.getenv("FAKE_EXPOSED", "posts").split(",") if t.strip()}


def tool_result(payload):
    return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        if message.get("method") == "initialize":
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message.get("id"), "result": {
                "protocolVersion": "2025-03-26", "capabilities": {},
                "serverInfo": {"name": "fake-rds-supabase", "version": "0.1"}}}) + "\n")
        elif message.get("method") == "notifications/initialized":
            pass
        elif message.get("method") == "tools/call":
            name = (message.get("params") or {}).get("name")
            if name == "list_tables":
                payload = [{"schema": "public", "name": t} for t in TABLES] + \
                          [{"schema": "information_schema", "name": "tables"}]
            elif name == "get_rls_status":
                payload = [{"schema": "public", "table": t,
                            "row_security": RLS_ON and t in EXPOSED,
                            "policies": 2 if RLS_ON and t in EXPOSED else 0} for t in TABLES]
            elif name == "get_advisors":
                payload = {"issues": ([{"name": f"000_security_rls_on_public.{TABLES[0]}", "level": "ERROR"}]
                                      if ADVISOR_HIT else []), "total_count": 1 if ADVISOR_HIT else 0}
            else:
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message.get("id"),
                                             "error": {"code": -32601, "message": f"unknown tool {name}"}}) + "\n")
                continue
            response = tool_result(payload)
            response["id"] = message.get("id")
            sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

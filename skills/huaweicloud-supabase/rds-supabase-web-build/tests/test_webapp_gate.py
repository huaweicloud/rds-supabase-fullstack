"""webapp-gate.py behavior tests: contract, stages, gates, trace and --verify.

Runs the gate script as a subprocess against temp fixtures; the REST layer is
exercised through a local fake gateway and the MCP layer through tests/fake_mcp.py.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE.parent / "scripts" / "webapp-gate.py"
FAKE_MCP = HERE / "fake_mcp.py"
RULES = {"security-rls-basics", "schema-primary-keys", "query-missing-indexes",
         "security-privileges", "data-upsert", "schema-constraints"}

SHA = "a" * 64


class FakeGateway(BaseHTTPRequestHandler):
    apikey_ok = {"service": "test-service", "anon": "test-anon"}
    openapi_tables = ["posts", "users", "comments"]
    anon_allowed = {"posts"}

    def log_message(self, *args):
        pass

    def do_GET(self):
        key = self.headers.get("apikey", "")
        if self.path.rstrip("/") == "/rest/v1":
            payload = {"paths": {f"/{t}": {} for t in self.apikey_tables if key == self.apikey_ok["service"]}}
            self._respond(200, payload)
            return
        if self.path.startswith("/rest/v1/"):
            table = self.path[len("/rest/v1/"):].split("?")[0]
            if key == self.apikey_ok["service"]:
                self._respond(200, [])
            elif key == self.apikey_ok["anon"] and table in self.anon_allowed:
                self._respond(200, [])
            else:
                self._respond(401, {"error": {"code": "4251"}})
            return
        self._respond(404, {})

    def _respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def apikey_tables(self):
        return self.openapi_tables


def make_project(tables=("public.posts", "public.users"), exposed=("public.posts",), advanced=None):
    root = Path(tempfile.mkdtemp(prefix="gate-test-"))
    (root / ".hwsupabase" / "gates").mkdir(parents=True)
    deployment = {"batch_id": "b1", "applied_at": "2026-11-10T08:00:00Z",
                  "objects": list(tables), "source_sha256": SHA, "status": "applied"}
    if exposed is not None:
        deployment["exposed"] = list(exposed)
    if advanced is not None:
        deployment.update(advanced)
    manifest = {
        "schema_version": 1,
        "project": {"name": "demo", "description": None, "requirements_summary": "blog",
                    "baas_capabilities": ["database", "auth", "rpc"]},
        "instance": {"supabase_application_id": "app-1", "source": "selected",
                     "gateway_url": "http://127.0.0.1:9", "credential_env_names":
                     ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"],
                     "credential_source": "protected_file", "region": "cn-north-4"},
        "obs": {"bucket_name": "demo", "source": "created", "naming_basis": "app_name_slug"},
        "mcp": {"registration_scope": "project",
                "config_paths": {"mgr": ".opencode/mcp.json", "data": ".opencode/mcp.json"}},
        "backend": {"current_batch": "b1", "deployments": [deployment],
                    "teardown_ref": ".hwsupabase/teardown.sql"},
        "frontend": {"record_ref": ".hwsupabase/frontend/prod/environment.json",
                     "project_dir": "web", "framework": "react-vite-ts"},
        "stages": {"last_completed_stage": "frontend_built", "updated_at": "2026-11-10T09:00:00Z",
                   "history": [{"stage": s, "status": "passed", "at": "2026-11-10T07:00:00Z", "note": None}
                               for s in ("requirements_confirmed", "instance_ready", "mcp_connected",
                                         "backend_deployed", "frontend_built")]},
    }
    (root / ".hwsupabase" / "webapp.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / ".hwsupabase" / "teardown.sql").write_text(
        "-- one-click teardown\nBEGIN;\n"
        + "".join(f"DROP TABLE IF EXISTS {t};\n" for t in tables)
        + "COMMIT;\n", encoding="utf-8")
    trace_lines = [json.dumps({"at": "2026-11-10T07:30:00Z", "stage": stage, "tool": tool,
                               "intent": "fixture", "status": "ok", "note": None})
                   for stage, tool in (("instance_ready", "list_supabase_applications"),
                                       ("mcp_connected", "get_project_url"),
                                       ("backend_deployed", "execute_sql"),
                                       ("frontend_built", "npm run build"))]
    (root / ".hwsupabase" / "trace.jsonl").write_text("\n".join(trace_lines) + "\n", encoding="utf-8")
    return root


def run_gate(project, *args, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SUPABASE_", "HUAWEICLOUD_", "WEBAPP_GATE_"))}
    env.setdefault("WEBAPP_GATE_RULES_DIR", str(make_rules_dir()))
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(GATE), str(project), *args],
                          capture_output=True, text=True, timeout=60, env=env)


def make_rules_dir():
    root = Path(tempfile.mkdtemp(prefix="gate-rules-"))
    for stem in RULES:
        (root / f"{stem}.md").write_text(f"# {stem}\n", encoding="utf-8")
    return root


def write_gate_file(project, number, lines):
    name = "3-rules-checklist.md" if number == 3 else "4-sdk-contract-checklist.md"
    (project / ".hwsupabase" / "gates" / name).write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


VALID_MAPPINGS = [
    "- security-rls-basics：对外表启用 RLS → init.sql L12",
    "- schema-primary-keys：主键选型 → init.sql L4",
    "- query-missing-indexes：外键索引 → init.sql L30",
    "- security-privileges：最小授权 GRANT → init.sql L20",
    "- data-upsert：可重复种子 → init.sql L40",
]


class ContractTests(unittest.TestCase):
    def test_pass(self):
        result = run_gate(make_project(), "check-contract")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["verdict"], "PASS")

    def test_fail_on_credential_like_value(self):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        data["instance"]["gateway_url"] = "eyJhbGciOiJIUzI1NiJ payload sig"
        path.write_text(json.dumps(data))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("credential-like", result.stdout)

    def test_fail_on_exposed_not_subset(self):
        project = make_project(exposed=("public.posts", "public.secrets"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("subset", result.stdout)

    def test_fail_on_bad_deployment_status(self):
        project = make_project(advanced={"status": "applied!"})
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("status", result.stdout)


class ObsContractTests(unittest.TestCase):
    def _edit_obs(self, mutate):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        mutate(data["obs"])
        path.write_text(json.dumps(data))
        return project

    def test_fail_obs_missing_from_instance_ready(self):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        del data["obs"]
        path.write_text(json.dumps(data))
        result = run_gate(project, "check-stage", "--stage", "instance_ready")
        self.assertEqual(result.returncode, 1)
        self.assertIn("obs section missing", result.stdout)

    def test_fail_obs_invalid_bucket_name(self):
        project = self._edit_obs(lambda obs: obs.update(bucket_name="My_Bucket"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("bucket name", result.stdout)

    def test_fail_obs_invalid_source(self):
        project = self._edit_obs(lambda obs: obs.update(source="auto"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("obs.source", result.stdout)

    def test_fail_obs_naming_required_when_created(self):
        project = self._edit_obs(lambda obs: obs.update(naming_basis=None))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("app_name_slug", result.stdout)

    def test_fail_obs_naming_forbidden_when_selected(self):
        project = self._edit_obs(lambda obs: obs.update(source="selected", naming_basis="app_name_slug"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("null when source is 'selected'", result.stdout)

    def test_pass_obs_selected_without_naming(self):
        project = self._edit_obs(lambda obs: obs.update(source="selected", naming_basis=None))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 0, result.stdout)


class McpRegistrationTests(unittest.TestCase):
    def _edit_mcp(self, mutate):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        mutate(data["mcp"])
        path.write_text(json.dumps(data))
        return project

    def test_fail_mcp_user_scope(self):
        project = self._edit_mcp(lambda m: m.update(registration_scope="user"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("registration_scope", result.stdout)

    def test_fail_mcp_absolute_path(self):
        project = self._edit_mcp(lambda m: m["config_paths"].update(mgr="/Users/fitz/.claude.json"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("config_paths.mgr", result.stdout)

    def test_fail_mcp_home_tilde_path(self):
        project = self._edit_mcp(lambda m: m["config_paths"].update(data="~/.config/opencode/opencode.json"))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("config_paths.data", result.stdout)

    def test_fail_mcp_missing_from_instance_ready(self):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        del data["mcp"]
        path.write_text(json.dumps(data))
        result = run_gate(project, "check-stage", "--stage", "instance_ready")
        self.assertEqual(result.returncode, 1)
        self.assertIn("config_paths.mgr", result.stdout)

    def test_fail_mcp_data_missing_from_mcp_connected(self):
        project = self._edit_mcp(lambda m: m["config_paths"].pop("data"))
        result = run_gate(project, "check-stage", "--stage", "mcp_connected")
        self.assertEqual(result.returncode, 1)
        self.assertIn("config_paths.data", result.stdout)


class StorageCapabilityTests(unittest.TestCase):
    def _with_storage(self, mutate_storage=None, caps=("database", "auth", "rpc", "storage")):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        data["project"]["baas_capabilities"] = list(caps)
        if mutate_storage is not None:
            data["storage"] = mutate_storage
        path.write_text(json.dumps(data))
        return project

    def test_fail_storage_required_but_missing(self):
        project = self._with_storage()
        result = run_gate(project, "check-stage", "--stage", "instance_ready")
        self.assertEqual(result.returncode, 1)
        self.assertIn("storage section is missing", result.stdout)

    def test_fail_storage_reuses_hosting_bucket(self):
        project = self._with_storage({"bucket_name": "demo", "source": "created", "connected": True})
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must differ from obs.bucket_name", result.stdout)

    def test_fail_storage_not_connected(self):
        project = self._with_storage({"bucket_name": "demo-storage", "source": "created", "connected": False})
        result = run_gate(project, "check-stage", "--stage", "instance_ready")
        self.assertEqual(result.returncode, 1)
        self.assertIn("storage.connected", result.stdout)

    def test_fail_storage_invalid_source(self):
        project = self._with_storage({"bucket_name": "demo-storage", "source": "auto", "connected": True})
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("storage.source", result.stdout)

    def test_pass_storage_fully_connected(self):
        project = self._with_storage({"bucket_name": "demo-storage", "source": "selected", "connected": True})
        result = run_gate(project, "check-stage", "--stage", "instance_ready")
        self.assertEqual(result.returncode, 0, result.stdout)


class StableUrlProtocolTests(unittest.TestCase):
    def make_published(self, ssl_enabled, stable_url):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        data["instance"]["ssl_enabled"] = ssl_enabled
        data["stages"]["last_completed_stage"] = "hosting_published"
        data["stages"]["history"].append({"stage": "hosting_published", "status": "passed",
                                          "at": "2026-11-10T10:00:00Z", "note": None})
        path.write_text(json.dumps(data))
        with (project / ".hwsupabase" / "trace.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": "2026-11-10T10:00:00Z", "stage": "hosting_published",
                                     "tool": "hcloud obs cp", "intent": "publish v1",
                                     "status": "ok", "note": None}) + "\n")
        env_dir = project / ".hwsupabase" / "frontend" / "prod"
        env_dir.mkdir(parents=True)
        (env_dir / "environment.json").write_text(json.dumps({"stable_url": stable_url}), encoding="utf-8")
        return project

    def test_pass_http_entry_when_ssl_disabled(self):
        project = self.make_published(False, "http://cdn.example.com")
        result = run_gate(project, "check-stage", "--stage", "hosting_published")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_fail_https_entry_when_ssl_disabled(self):
        project = self.make_published(False, "https://cdn.example.com")
        result = run_gate(project, "check-stage", "--stage", "hosting_published")
        self.assertEqual(result.returncode, 1)
        self.assertIn("mixed content", result.stdout)

    def test_fail_http_entry_when_ssl_enabled(self):
        project = self.make_published(True, "http://cdn.example.com")
        result = run_gate(project, "check-stage", "--stage", "hosting_published")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTPS entry required", result.stdout)

    def test_fail_frontend_record_missing(self):
        project = self.make_published(False, "http://cdn.example.com")
        (project / ".hwsupabase" / "frontend" / "prod" / "environment.json").unlink()
        result = run_gate(project, "check-stage", "--stage", "hosting_published")
        self.assertEqual(result.returncode, 1)
        self.assertIn("record_ref file not found", result.stdout)


class TeardownTests(unittest.TestCase):
    def test_fail_teardown_ref_missing(self):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        del data["backend"]["teardown_ref"]
        path.write_text(json.dumps(data))
        result = run_gate(project, "check-contract")
        self.assertEqual(result.returncode, 1)
        self.assertIn("teardown_ref", result.stdout)

    def test_fail_teardown_file_missing(self):
        project = make_project()
        (project / ".hwsupabase" / "teardown.sql").unlink()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stdout)

    def test_fail_teardown_object_not_covered(self):
        project = make_project()
        (project / ".hwsupabase" / "teardown.sql").write_text(
            "BEGIN;\nDROP TABLE IF EXISTS public.posts;\nCOMMIT;\n", encoding="utf-8")
        result = run_gate(project, "check-stage", "--stage", "backend_deployed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not cover", result.stdout)

    def test_pass_teardown_bare_name_coverage(self):
        project = make_project()
        (project / ".hwsupabase" / "teardown.sql").write_text(
            "BEGIN;\nDROP TABLE IF EXISTS posts;\nDROP TABLE IF EXISTS users;\nCOMMIT;\n",
            encoding="utf-8")
        result = run_gate(project, "check-stage", "--stage", "backend_deployed")
        self.assertEqual(result.returncode, 0, result.stdout)


class StageTests(unittest.TestCase):
    def test_pass_reached(self):
        result = run_gate(make_project(), "check-stage", "--stage", "backend_deployed")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_fail_not_reached(self):
        result = run_gate(make_project(), "check-stage", "--stage", "hosting_published")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not reached", result.stdout)

    def test_fail_no_history(self):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        data["stages"]["history"] = []
        path.write_text(json.dumps(data))
        result = run_gate(project, "check-stage", "--stage", "backend_deployed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no passed history", result.stdout)


class GateArtifactTests(unittest.TestCase):
    def test_gate3_pass_with_valid_stems(self):
        project = make_project()
        write_gate_file(project, 3, VALID_MAPPINGS)
        result = run_gate(project, "check-gate", "--number", "3")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_gate3_fail_unknown_rule_stem(self):
        project = make_project()
        write_gate_file(project, 3, [
            "- security-rls-basics：RLS → L12",
            "- totally-made-up-rule：不存在 → L1",
            "- schema-primary-keys：主键 → L4",
            "- query-missing-indexes：索引 → L30",
            "- security-privileges：授权 → L20",
        ])
        result = run_gate(project, "check-gate", "--number", "3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("without a known rule file stem", result.stdout)

    def test_gate3_fail_too_few_mappings(self):
        project = make_project()
        write_gate_file(project, 3, VALID_MAPPINGS[:3])
        result = run_gate(project, "check-gate", "--number", "3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("at least 5 valid", result.stdout)

    def test_gate4_structural_pass(self):
        project = make_project()
        write_gate_file(project, 4, [
            "- 会话管理 → src/lib/auth.ts",
            "- RLS 语义 → src/api.ts",
            "- 错误契约 → src/errors.ts",
            "- env 注入 → .env.example",
            "- Realtime 清理 → src/realtime.ts",
        ])
        result = run_gate(project, "check-gate", "--number", "4")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_gate3_reports_skip_when_rules_dir_missing(self):
        project = make_project()
        write_gate_file(project, 3, VALID_MAPPINGS)
        result = run_gate(project, "check-gate", "--number", "3", env_extra={"WEBAPP_GATE_RULES_DIR": "/nonexistent"})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("skipped: best-practices skill not found", result.stdout)


class TraceTests(unittest.TestCase):
    def test_trace_valid(self):
        project = make_project()
        (project / ".hwsupabase" / "trace.jsonl").write_text(
            '{"at":"2026-11-10T07:30:00Z","stage":"backend_deployed","tool":"execute_sql",'
            '"intent":"deploy b1","status":"ok","note":null}\n', encoding="utf-8")
        result = run_gate(project, "check-trace")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_trace_invalid_line(self):
        project = make_project()
        (project / ".hwsupabase" / "trace.jsonl").write_text("not-json\n", encoding="utf-8")
        result = run_gate(project, "check-trace")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not valid JSON", result.stdout)


class VerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGateway)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def env(self):
        return {"SUPABASE_URL": f"http://127.0.0.1:{self.port}",
                "SUPABASE_ANON_KEY": "test-anon",
                "SUPABASE_SERVICE_ROLE_KEY": "test-service"}

    def test_verify_pass_rest_and_mcp(self):
        project = make_project()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed",
                          "--verify", "--mcp-command", f"{sys.executable} {FAKE_MCP}",
                          env_extra=self.env())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("rls_enabled", payload.get("mcp", {}))

    def test_verify_fail_missing_env(self):
        project = make_project()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed", "--verify",
                          env_extra={"SUPABASE_URL": "", "SUPABASE_ANON_KEY": "", "SUPABASE_SERVICE_ROLE_KEY": ""})
        self.assertEqual(result.returncode, 1)
        self.assertIn("SUPABASE_URL", result.stdout)

    def test_verify_fail_table_absent_from_rest(self):
        project = make_project(tables=("public.posts", "public.secrets"))
        result = run_gate(project, "check-stage", "--stage", "backend_deployed", "--verify",
                          env_extra=self.env())
        self.assertEqual(result.returncode, 1)
        self.assertIn("not visible via REST", result.stdout)

    def test_verify_fail_exposed_not_anon_reachable(self):
        project = make_project(exposed=("public.users",))
        result = run_gate(project, "check-stage", "--stage", "backend_deployed", "--verify",
                          env_extra=self.env())
        self.assertEqual(result.returncode, 1)
        self.assertIn("not anonymously reachable", result.stdout)

    def test_verify_fail_rls_disabled(self):
        project = make_project()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed",
                          "--verify", "--mcp-command", f"{sys.executable} {FAKE_MCP}",
                          env_extra={**self.env(), "FAKE_RLS_ENABLED": "0"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("RLS disabled", result.stdout)

    def test_verify_fail_advisor_hit(self):
        project = make_project()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed",
                          "--verify", "--mcp-command", f"{sys.executable} {FAKE_MCP}",
                          env_extra={**self.env(), "FAKE_ADVISOR_HIT": "1"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("security advisor", result.stdout)

    def _set_ssl(self, project, value):
        manifest = json.loads((project / ".hwsupabase" / "webapp.json").read_text(encoding="utf-8"))
        manifest["instance"]["ssl_enabled"] = value
        (project / ".hwsupabase" / "webapp.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_verify_http_allowed_when_ssl_disabled(self):
        project = make_project()
        self._set_ssl(project, False)
        result = run_gate(project, "check-stage", "--stage", "backend_deployed", "--verify",
                          env_extra={"SUPABASE_URL": "http://example.invalid:8443",
                                     "SUPABASE_ANON_KEY": "test-anon",
                                     "SUPABASE_SERVICE_ROLE_KEY": "test-service"})
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("must be HTTPS", result.stdout)  # http is the intended mode here
        self.assertIn("REST verification failed", result.stdout)  # fails on reachability, not scheme

    def test_verify_http_rejected_when_ssl_unknown(self):
        project = make_project()  # ssl_enabled absent -> HTTPS enforced (safe default)
        result = run_gate(project, "check-stage", "--stage", "backend_deployed", "--verify",
                          env_extra={"SUPABASE_URL": "http://example.invalid:8443",
                                     "SUPABASE_ANON_KEY": "test-anon",
                                     "SUPABASE_SERVICE_ROLE_KEY": "test-service"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be HTTPS", result.stdout)

    def test_verify_without_mcp_notes_gap(self):
        project = make_project()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed", "--verify",
                          env_extra=self.env())
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("no --mcp-command", result.stdout)


class TraceEnforcementTests(unittest.TestCase):
    def test_fail_when_trace_missing_for_required_stage(self):
        project = make_project()
        (project / ".hwsupabase" / "trace.jsonl").unlink()
        result = run_gate(project, "check-stage", "--stage", "backend_deployed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("trace enforcement", result.stdout)

    def test_exempt_stage_passes_without_trace(self):
        project = make_project()
        path = project / ".hwsupabase" / "webapp.json"
        data = json.loads(path.read_text())
        data["stages"]["history"].append({"stage": "requirements_confirmed", "status": "passed",
                                          "at": "2026-11-10T06:00:00Z", "note": None})
        path.write_text(json.dumps(data))
        (project / ".hwsupabase" / "trace.jsonl").unlink()
        result = run_gate(project, "check-stage", "--stage", "requirements_confirmed")
        self.assertEqual(result.returncode, 0, result.stdout)


class WhitelistTests(unittest.TestCase):
    def test_pass_all_tools_allowed(self):
        result = run_gate(make_project(), "check-whitelist")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_fail_on_out_of_stage_tool(self):
        project = make_project()
        with (project / ".hwsupabase" / "trace.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": "2026-11-10T08:30:00Z", "stage": "backend_deployed",
                                     "tool": "delete_supabase_application", "intent": "oops",
                                     "status": "ok", "note": None}) + "\n")
        result = run_gate(project, "check-whitelist")
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the stage allow-list", result.stdout)


class SkillLintTests(unittest.TestCase):
    SKILL_DIR = HERE.parent

    def test_pass_on_real_skill(self):
        result = subprocess.run([sys.executable, str(HERE.parent / "scripts" / "skill-lint.py"),
                                 str(self.SKILL_DIR)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fail_on_broken_copy(self):
        import shutil
        broken = Path(tempfile.mkdtemp(prefix="skill-lint-")) / "rds-supabase-web-build"
        shutil.copytree(self.SKILL_DIR, broken,
                        ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        skill = broken / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace(
            "### 步骤五 · 后端生成部署 → 断点 `backend_deployed`",
            "### 步骤五 · 后端生成部署 → 断点 `backend_deployed_x`"), encoding="utf-8")
        result = subprocess.run([sys.executable, str(broken / "scripts" / "skill-lint.py"),
                                 str(broken)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn("mismatch", result.stdout)
        shutil.rmtree(broken, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

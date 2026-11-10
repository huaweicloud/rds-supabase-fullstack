"""Discovery must resolve projects and endpoints without echoing credentials."""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

TOKEN_PAYLOAD = {'token': {'project': {'id': 'p-1', 'name': 'cn-north-4', 'domain': {'id': 'd-1'}}}}
PROJECTS_PAYLOAD = {'projects': [
    {'id': 'p-1', 'name': 'cn-north-4'},
    {'id': 'p-2', 'name': 'custom-pool'},
]}


class Handler(BaseHTTPRequestHandler):
    token_payload = TOKEN_PAYLOAD
    apps_code = 200
    observed = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).observed.append((self.path, dict(self.headers)))
        if self.path.startswith('/v3/auth/tokens'):
            payload, code = self.token_payload, 200
        elif self.path.startswith('/v3/projects'):
            payload, code = PROJECTS_PAYLOAD, 200
        else:
            payload, code = {'applications': []}, self.apps_code
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        from mcp_server_supabase.service import discovery
        self.discovery = discovery
        Handler.observed = []
        Handler.token_payload = TOKEN_PAYLOAD
        Handler.apps_code = 200
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    async def test_rest_token_scope_single_candidate(self):
        env = {'SUPABASE_TRANSPORT': 'rest', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin):
            result = await self.discovery.discover()
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['candidates']), 1)
        candidate = result['candidates'][0]
        self.assertEqual(candidate['project_id'], 'p-1')
        self.assertEqual(candidate['project_name'], 'cn-north-4')
        self.assertEqual(candidate['region'], 'cn-north-4')
        self.assertEqual(candidate['endpoint'], 'https://rds.cn-north-4.myhuaweicloud.com')
        self.assertEqual(candidate['endpoint_source'], 'derived')
        self.assertEqual(candidate['suggested_env'], {'HUAWEICLOUD_PROJECT_ID': 'p-1',
                                                       'SUPABASE_RDS_ENDPOINT': 'https://rds.cn-north-4.myhuaweicloud.com'})
        headers = Handler.observed[0][1]
        self.assertEqual(headers.get('X-Auth-Token'), 'secret-token')
        self.assertEqual(headers.get('X-Subject-Token'), 'secret-token')
        self.assertNotIn('secret-token', json.dumps(result))

    async def test_sdk_core_lists_projects_and_flags_non_region(self):
        env = {'SUPABASE_TRANSPORT': 'sdk_core', 'HUAWEICLOUD_ACCESS_KEY': 'test-ak',
               'HUAWEICLOUD_SECRET_KEY': 'test-sk'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin):
            result = await self.discovery.discover()
        self.assertTrue(result['passed'])
        by_id = {c['project_id']: c for c in result['candidates']}
        self.assertEqual(by_id['p-1']['endpoint'], 'https://rds.cn-north-4.myhuaweicloud.com')
        self.assertEqual(by_id['p-1']['endpoint_source'], 'derived')
        self.assertIsNone(by_id['p-2']['endpoint'])
        self.assertEqual(by_id['p-2']['endpoint_source'], 'manual')
        self.assertIsNone(by_id['p-2']['suggested_env'])
        self.assertNotIn('test-ak', json.dumps(result))
        self.assertNotIn('test-sk', json.dumps(result))

    async def test_explicit_endpoint_wins_over_derivation(self):
        env = {'SUPABASE_TRANSPORT': 'rest', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token',
               'SUPABASE_RDS_ENDPOINT': 'https://rds.explicit.example.invalid'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin):
            result = await self.discovery.discover()
        candidate = result['candidates'][0]
        self.assertEqual(candidate['endpoint'], 'https://rds.explicit.example.invalid')
        self.assertEqual(candidate['endpoint_source'], 'explicit')
        self.assertTrue(result['explicit_endpoint_configured'])

    async def test_probe_confirms_derived_endpoint_without_echo(self):
        env = {'SUPABASE_TRANSPORT': 'rest', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin), \
             patch.object(self.discovery, 'derive_endpoint', lambda region: self.origin):
            result = await self.discovery.discover(probe=True)
        candidate = result['candidates'][0]
        self.assertTrue(candidate['probe']['reachable'])
        self.assertFalse(candidate['probe']['verified'])
        probe_calls = [path for path, _ in Handler.observed if 'ai-application' in path]
        self.assertEqual(len(probe_calls), 1)
        self.assertTrue(probe_calls[0].startswith('/v3/p-1/ai-application/applications'))
        self.assertIn('type=supabase', probe_calls[0])
        self.assertNotIn('secret-token', json.dumps(result))

    async def test_probe_failure_reports_unreachable(self):
        Handler.apps_code = 404
        env = {'SUPABASE_TRANSPORT': 'rest', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin), \
             patch.object(self.discovery, 'derive_endpoint', lambda region: self.origin):
            result = await self.discovery.discover(probe=True)
        self.assertFalse(result['candidates'][0]['probe']['reachable'])

    async def test_domain_scoped_token_reports_clear_error(self):
        Handler.token_payload = {'token': {'user': {'id': 'u-1'}}}
        env = {'SUPABASE_TRANSPORT': 'rest', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin):
            result = await self.discovery.discover()
        self.assertFalse(result['passed'])
        self.assertIn('project-scoped', result['error'])
        self.assertTrue(result['network_attempted'])

    async def test_missing_credentials_reports_error_without_network(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin):
            result = await self.discovery.discover()
        self.assertFalse(result['passed'])
        self.assertFalse(result['network_attempted'])
        self.assertEqual(Handler.observed, [])

    async def test_unsupported_transport_rejected_before_network(self):
        env = {'SUPABASE_TRANSPORT': 'unknown', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', self.origin):
            result = await self.discovery.discover()
        self.assertFalse(result['passed'])
        self.assertIn('SUPABASE_TRANSPORT', result['error'])
        self.assertEqual(Handler.observed, [])

    async def test_iam_unreachable_reports_error(self):
        env = {'SUPABASE_TRANSPORT': 'rest', 'HUAWEICLOUD_AUTH_TOKEN': 'secret-token'}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.discovery, 'IAM_ORIGIN', 'http://127.0.0.1:1'):
            result = await self.discovery.discover()
        self.assertFalse(result['passed'])
        self.assertIn('IAM query failed', result['error'])

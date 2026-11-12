"""Application inventory query: fixed type scope, filters, sort and the mandatory projection."""
import unittest
from unittest.mock import AsyncMock
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.service.operations import Operations

RECORD = {'id': 'app-1', 'name': 'demo', 'public_ip': '192.0.2.10', 'port': 8443,
          'flavor_ref': 'rds.supabase.c6.large.2', 'mode': 'Single',
          'created_time': '2026-11-01T08:00:00Z', 'remark': 'fixture',
          'status': 'normal', 'updated_time': '2026-11-02T08:00:00Z',
          'api_key': 'fixture-secret'}


class ApplicationListTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.ops = Operations(self.client)

    def _respond(self, payload):
        self.client.request.return_value = (200, payload)

    async def test_query_carries_fixed_type_filters_and_sort(self):
        self._respond({'applications': [], 'total_count': 0})
        await self.ops.read('applications', name='demo', application_id='app-1',
                            sort_key='name', sort_dir='asc')
        self.assertEqual(self.client.request.call_args.args,
                         ('GET', '/v3/{project}/ai-application/applications'))
        query = self.client.request.call_args.kwargs['query']
        self.assertEqual(query['type'], 'supabase')
        self.assertEqual(query['name'], 'demo')
        self.assertEqual(query['id'], 'app-1')
        self.assertEqual(query['sort_key'], 'name')
        self.assertEqual(query['sort_dir'], 'asc')

    async def test_defaults_are_bounded_and_echoed(self):
        self._respond({'applications': [], 'total_count': 0})
        result = await self.ops.read('applications')
        query = self.client.request.call_args.kwargs['query']
        self.assertEqual((query['limit'], query['offset'], query['sort_key'], query['sort_dir']),
                         (10, 0, 'created_time', 'desc'))
        self.assertEqual(result['limit'], 10)
        self.assertEqual(result['offset'], 0)

    async def test_total_count_and_mandatory_projection(self):
        self._respond({'applications': [dict(RECORD)], 'total_count': 5})
        result = await self.ops.read('applications')
        self.assertEqual(result['data']['total_count'], 5)
        row = result['data']['data'][0]
        for field in ('id', 'name', 'public_ip', 'port', 'flavor_ref', 'mode',
                      'created_time', 'remark'):
            self.assertIn(field, row)
        self.assertEqual(row['status'], 'normal')
        self.assertNotIn('api_key', row)

    async def test_alias_promotion_to_canonical_names(self):
        record = dict(RECORD)
        record['flavor'] = record.pop('flavor_ref')
        record['description'] = record.pop('remark')
        record['gateway_port'] = record.pop('port')
        self._respond({'applications': [record], 'total_count': 1})
        row = (await self.ops.read('applications'))['data']['data'][0]
        self.assertEqual(row['flavor_ref'], 'rds.supabase.c6.large.2')
        self.assertEqual(row['remark'], 'fixture')
        self.assertEqual(row['port'], 8443)
        self.assertNotIn('flavor', row)
        self.assertNotIn('description', row)
        self.assertNotIn('gateway_port', row)

    async def test_malformed_envelope_fails_closed(self):
        for payload in ({'applications': {}}, {'applications': []},
                        {'total_count': True, 'applications': []},
                        {'total_count': -1, 'applications': []}):
            with self.subTest(payload=payload):
                self._respond(payload)
                with self.assertRaises(McpToolError):
                    await self.ops.read('applications')

    async def test_missing_mandatory_field_fails_closed(self):
        record = dict(RECORD)
        del record['public_ip']
        self._respond({'applications': [record], 'total_count': 1})
        with self.assertRaises(McpToolError) as error:
            await self.ops.read('applications')
        self.assertEqual(error.exception.code, 'MCP_SDK_ERROR')

    async def test_invalid_filters_never_call_backend(self):
        for kwargs in ({'sort_key': 'bogus'}, {'sort_dir': 'up'},
                       {'application_id': '../bad'}, {'name': ''}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(McpToolError) as error:
                    await self.ops.read('applications', **kwargs)
                self.assertEqual(error.exception.code, 'MCP_INVALID_ARGS')
                self.assertFalse(self.client.request.called)

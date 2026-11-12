"""Application inventory query: fixed type scope, filters, sort and the mandatory projection.

Fixtures mirror the real backend response contract (envelope {total_count, data},
direct_eip as the public IP, epoch-millisecond timestamps, nested objects).
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.service.operations import Operations

REAL_RECORD = {
    'id': 'ad9079c304464c33a4f2fd516d4a3b16in32',
    'name': 'rds-supabase-liujian-web',
    'type': 'supabase',
    'version': '1.0.0',
    'mode': 'Single',
    'status': 'abnormal',
    'enable_ssl': False,
    'current_actions': [],
    'group_type': 'general',
    'flavor_id': 'bdb98bc6-7279-4bce-b436-2acd47819ac1',
    'flavor_ref': 'rds.supabase.n1.large.2',
    'vcpus': 2,
    'ram': 4,
    'private_ip': '192.168.0.112',
    'traffic_vip': '192.168.0.252',
    'direct_eip': '123.60.101.251',
    'port': 8443,
    'availability_zone': 'cn-east-3a',
    'az_details': [{'code': 'cn-east-3a', 'description': '可用区1'}],
    'managed_instance': {'id': 'ee36e15f94ed4432adb3ada163620d82in03',
                         'name': 'rds-supabase-pg-01309873', 'status': 'shutdown'},
    'created_time': 1794025857392,
    'updated_time': 1794403200116,
}

REAL_PAYLOAD = {'total_count': 1, 'data': [dict(REAL_RECORD)]}


def rfc3339(epoch_ms):
    seconds, millis = divmod(epoch_ms, 1000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc)
    return stamp.strftime('%Y-%m-%dT%H:%M:%S') + '.%03dZ' % millis


class ApplicationListTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.ops = Operations(self.client)

    def _respond(self, payload):
        self.client.request.return_value = (200, payload)

    async def test_query_carries_fixed_type_filters_and_sort(self):
        self._respond({'data': [], 'total_count': 0})
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
        self._respond({'data': [], 'total_count': 0})
        result = await self.ops.read('applications')
        query = self.client.request.call_args.kwargs['query']
        self.assertEqual((query['limit'], query['offset'], query['sort_key'], query['sort_dir']),
                         (10, 0, 'created_time', 'desc'))
        self.assertEqual(result['limit'], 10)
        self.assertEqual(result['offset'], 0)

    async def test_real_payload_projection(self):
        self._respond(dict(REAL_PAYLOAD))
        result = await self.ops.read('applications')
        self.assertEqual(result['data']['total_count'], 1)
        row = result['data']['data'][0]
        self.assertEqual(row['id'], 'ad9079c304464c33a4f2fd516d4a3b16in32')
        self.assertEqual(row['name'], 'rds-supabase-liujian-web')
        self.assertEqual(row['mode'], 'Single')
        self.assertEqual(row['port'], 8443)
        self.assertEqual(row['flavor_ref'], 'rds.supabase.n1.large.2')
        self.assertEqual(row['public_ip'], '123.60.101.251')
        self.assertNotIn('direct_eip', row)
        self.assertEqual(row['created_time'], rfc3339(1794025857392))
        self.assertEqual(row['updated_time'], rfc3339(1794403200116))
        self.assertIsNone(row['remark'])
        self.assertEqual(row['managed_instance']['status'], 'shutdown')
        self.assertEqual(row['az_details'][0]['code'], 'cn-east-3a')
        self.assertEqual(row['current_actions'], [])
        self.assertEqual(row['vcpus'], 2)
        self.assertEqual(row['private_ip'], '192.168.0.112')
        self.assertEqual(row['type'], 'supabase')
        self.assertEqual(row['status'], 'abnormal')

    async def test_nested_secrets_are_dropped(self):
        record = dict(REAL_RECORD)
        record['managed_instance'] = dict(record['managed_instance'],
                                          password='fixture-secret', api_key='fixture-key')
        self._respond({'total_count': 1, 'data': [record]})
        row = (await self.ops.read('applications'))['data']['data'][0]
        self.assertNotIn('password', row['managed_instance'])
        self.assertNotIn('api_key', row['managed_instance'])
        self.assertNotIn('fixture-secret', str(row))

    async def test_alias_promotion_to_canonical_names(self):
        record = dict(REAL_RECORD)
        record['flavor'] = record.pop('flavor_ref')
        record['description'] = 'fixture remark'
        record['gateway_port'] = record.pop('port')
        self._respond({'total_count': 1, 'data': [record]})
        row = (await self.ops.read('applications'))['data']['data'][0]
        self.assertEqual(row['flavor_ref'], 'rds.supabase.n1.large.2')
        self.assertEqual(row['remark'], 'fixture remark')
        self.assertEqual(row['port'], 8443)
        self.assertNotIn('flavor', row)
        self.assertNotIn('description', row)
        self.assertNotIn('gateway_port', row)

    async def test_malformed_envelope_fails_closed(self):
        for payload in ({'data': {}}, {'data': []}, {'applications': []},
                        {'total_count': True, 'data': []},
                        {'total_count': -1, 'data': []}):
            with self.subTest(payload=payload):
                self._respond(payload)
                with self.assertRaises(McpToolError):
                    await self.ops.read('applications')

    async def test_missing_mandatory_field_fails_closed(self):
        record = dict(REAL_RECORD)
        del record['direct_eip']
        self._respond({'total_count': 1, 'data': [record]})
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


REAL_DETAIL = {
    'id': 'ad9079c304464c33a4f2fd516d4a3b16in32',
    'name': 'rds-supabase-liujian-web',
    'type': 'supabase',
    'version': '1.0.0',
    'mode': 'Single',
    'spec_flavor': {'id': 'bdb98bc6-7279-4bce-b436-2acd47819ac1', 'vcpus': 2, 'ram': 4,
                    'code': 'rds.supabase.n1.large.2', 'group_type': 'general'},
    'data_volume': {'type': 'SSD', 'size': 10000000000},
    'nodes': [{'node_id': '6c84be680c38417ca1f89842de504520no32',
               'node_name': 'rds-supabase-liujian-web_node0', 'status': 'abnormal',
               'role': 'master', 'manage_ip': '172.16.1.75', 'private_ip': '192.168.0.112',
               'az_code': 'cn-east-3a', 'az_name': '可用区1',
               'created_time': 1794025857392, 'updated_time': 1794403500913}],
    'status': 'abnormal',
    'current_actions': [],
    'manage_ip': '172.16.1.75',
    'private_ip': '192.168.0.112',
    'traffic_vip': '192.168.0.252',
    'direct_eip': '123.60.101.251',
    'dnat': {'enabled': False},
    'vpc_id': 'fff3b97c-8821-44e5-b16e-788a745292f0',
    'subnet_id': '52ba0d87-b803-4273-8e8e-332dde4fa19d',
    'port': 8443,
    'security_group_id': '7d4fd664-b212-4a54-a5f5-735eacc6cd54',
    'enable_ssl': False,
    'storage_component': {'enabled': False},
    'availability_zone': 'cn-east-3a',
    'az_details': [{'code': 'cn-east-3a', 'description': '可用区1'}],
    'time_zone': 'UTC+08:00',
    'created_time': 1794025857392,
    'updated_time': 1794403200116,
    'managed_instance': {'id': 'ee36e15f94ed4432adb3ada163620d82in03',
                         'name': 'rds-supabase-pg-01309873',
                         'datastore': {'type': 'postgresql', 'version': '18.6.260901'},
                         'mode': 'Single', 'status': 'shutdown'},
}


class ApplicationDetailTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.ops = Operations(self.client)

    async def test_real_detail_projection(self):
        self.client.request.return_value = (200, dict(REAL_DETAIL))
        result = await self.ops.read('application', 'ad9079c304464c33a4f2fd516d4a3b16in32')
        row = result['data']
        self.assertEqual(row['id'], 'ad9079c304464c33a4f2fd516d4a3b16in32')
        self.assertEqual(row['name'], 'rds-supabase-liujian-web')
        self.assertEqual(row['mode'], 'Single')
        self.assertEqual(row['status'], 'abnormal')
        self.assertFalse(row['enable_ssl'])
        self.assertEqual(row['port'], 8443)
        self.assertEqual(row['private_ip'], '192.168.0.112')
        self.assertEqual(row['traffic_vip'], '192.168.0.252')
        self.assertEqual(row['manage_ip'], '172.16.1.75')
        self.assertEqual(row['public_ip'], '123.60.101.251')
        self.assertNotIn('direct_eip', row)
        self.assertIsNone(row['remark'])
        self.assertEqual(row['created_time'], rfc3339(1794025857392))
        self.assertEqual(row['updated_time'], rfc3339(1794403200116))
        self.assertEqual(row['spec_flavor']['code'], 'rds.supabase.n1.large.2')
        self.assertEqual(row['data_volume']['size'], 10000000000)
        self.assertEqual(row['nodes'][0]['role'], 'master')
        self.assertEqual(row['nodes'][0]['created_time'], rfc3339(1794025857392))
        self.assertEqual(row['nodes'][0]['updated_time'], rfc3339(1794403500913))
        self.assertEqual(row['managed_instance']['datastore']['version'], '18.6.260901')
        self.assertEqual(row['managed_instance']['status'], 'shutdown')
        self.assertEqual(row['dnat'], {'enabled': False})
        self.assertEqual(row['time_zone'], 'UTC+08:00')
        self.assertEqual(row['storage_component'], {'enabled': False})
        self.assertNotIn('limit', result)
        self.assertNotIn('offset', result)
        self.assertIn('Access address', result['note'])

    async def test_detail_missing_mandatory_fails_closed(self):
        for field in ('private_ip', 'enable_ssl', 'port', 'status', 'created_time'):
            record = dict(REAL_DETAIL)
            del record[field]
            self.client.request.return_value = (200, record)
            with self.subTest(field=field):
                with self.assertRaises(McpToolError) as error:
                    await self.ops.read('application', 'app-1')
                self.assertEqual(error.exception.code, 'MCP_SDK_ERROR')

    async def test_detail_without_eip_yields_null_public_ip(self):
        record = dict(REAL_DETAIL)
        del record['direct_eip']
        self.client.request.return_value = (200, record)
        row = (await self.ops.read('application', 'app-1'))['data']
        self.assertIsNone(row['public_ip'])

    async def test_detail_nested_secrets_dropped(self):
        record = dict(REAL_DETAIL)
        record['nodes'] = [dict(record['nodes'][0], password='fixture-secret')]
        self.client.request.return_value = (200, record)
        row = (await self.ops.read('application', 'app-1'))['data']
        self.assertNotIn('password', row['nodes'][0])
        self.assertNotIn('fixture-secret', str(row))

    async def test_detail_malformed_fails_closed(self):
        for payload in ([], 'x', None):
            self.client.request.return_value = (200, payload)
            with self.subTest(payload=payload):
                with self.assertRaises(McpToolError):
                    await self.ops.read('application', 'app-1')

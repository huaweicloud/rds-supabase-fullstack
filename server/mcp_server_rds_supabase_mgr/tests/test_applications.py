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
        del record['flavor_ref']
        self._respond({'total_count': 1, 'data': [record]})
        with self.assertRaises(McpToolError) as error:
            await self.ops.read('applications')
        self.assertEqual(error.exception.code, 'MCP_SDK_ERROR')

    async def test_missing_ip_fields_do_not_fail(self):
        # public_ip is absent until an EIP is bound; a freshly created row may
        # carry neither address. Both must project as None, not MCP_SDK_ERROR.
        record = dict(REAL_RECORD)
        for key in ('direct_eip', 'public_ip', 'public_ip_address', 'eip_address'):
            record.pop(key, None)
        self._respond({'total_count': 1, 'data': [record]})
        result = await self.ops.read('applications')
        row = result['data']['data'][0]
        self.assertIsNone(row['public_ip'])

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
        for field in ('enable_ssl', 'port', 'status', 'created_time'):
            record = dict(REAL_DETAIL)
            del record[field]
            self.client.request.return_value = (200, record)
            with self.subTest(field=field):
                with self.assertRaises(McpToolError) as error:
                    await self.ops.read('application', 'app-1')
                self.assertEqual(error.exception.code, 'MCP_SDK_ERROR')

    async def test_detail_missing_private_ip_while_creating_does_not_fail(self):
        # While the application is still creating the backend omits private_ip;
        # the detail query must project None instead of MCP_SDK_ERROR.
        record = dict(REAL_DETAIL)
        del record['private_ip']
        record['status'] = 'creating'
        self.client.request.return_value = (200, record)
        row = (await self.ops.read('application', 'app-1'))['data']
        self.assertIsNone(row['private_ip'])
        self.assertEqual(row['status'], 'creating')

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


REAL_AUTH_CONFIG = {
    'enable_account_sign_up': True,
    'enable_anonymous_users': False,
    'api_external_url': 'http://localhost:8443',
    'site_url': 'http://localhost:3000',
    'allow_redirect_urls': '',
    'github_oauth_provider': {'enable_github': False, 'oauth_client_id': '', 'redirect_uri': ''},
    'email_oauth_provider': {
        'enable_email_sign_up': False,
        'enable_email_auto_confirm': True,
        'smtp_config': {'smtp_host': '', 'smtp_port': 587, 'smtp_user': '',
                        'smtp_admin_email': '', 'smtp_sender_name': '', 'smtp_max_frequency': 60}},
    'email_template_config': {
        'mailer_confirmation': {'subject': '', 'url': ''},
        'mailer_invite': {'subject': '', 'url': ''},
        'mailer_recovery': {'subject': '', 'url': ''},
        'mailer_email_change': {'subject': '', 'url': ''},
        'mailer_magic_link': {'subject': '', 'url': ''},
        'mailer_reauthentication': {'subject': '', 'url': ''}},
}


class AuthConfigTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.ops = Operations(self.client)

    async def test_real_auth_config_projection(self):
        self.client.request.return_value = (200, dict(REAL_AUTH_CONFIG))
        result = await self.ops.read('auth', 'app-1')
        row = result['data']
        self.assertTrue(row['enable_account_sign_up'])
        self.assertFalse(row['enable_anonymous_users'])
        self.assertEqual(row['site_url'], 'http://localhost:3000')
        self.assertEqual(row['api_external_url'], 'http://localhost:8443')
        self.assertEqual(row['allow_redirect_urls'], '')
        self.assertFalse(row['github_oauth_provider']['enable_github'])
        self.assertEqual(row['email_oauth_provider']['smtp_config']['smtp_port'], 587)
        self.assertEqual(row['email_oauth_provider']['smtp_config']['smtp_max_frequency'], 60)
        for template in ('mailer_confirmation', 'mailer_invite', 'mailer_recovery',
                         'mailer_email_change', 'mailer_magic_link', 'mailer_reauthentication'):
            self.assertIn(template, row['email_template_config'])
        self.assertNotIn('limit', result)
        self.assertNotIn('offset', result)
        self.assertIn('reconciliation', result['note'])

    async def test_auth_missing_mandatory_fails_closed(self):
        for field in ('enable_account_sign_up', 'site_url', 'github_oauth_provider',
                      'email_oauth_provider', 'email_template_config'):
            record = dict(REAL_AUTH_CONFIG)
            del record[field]
            self.client.request.return_value = (200, record)
            with self.subTest(field=field):
                with self.assertRaises(McpToolError) as error:
                    await self.ops.read('auth', 'app-1')
                self.assertEqual(error.exception.code, 'MCP_SDK_ERROR')

    async def test_auth_flag_and_section_types_enforced(self):
        for field, value in (('enable_account_sign_up', 1), ('enable_anonymous_users', 'false'),
                             ('site_url', None), ('github_oauth_provider', []),
                             ('email_template_config', 'x')):
            record = dict(REAL_AUTH_CONFIG)
            record[field] = value
            self.client.request.return_value = (200, record)
            with self.subTest(field=field):
                with self.assertRaises(McpToolError) as error:
                    await self.ops.read('auth', 'app-1')
                self.assertEqual(error.exception.code, 'MCP_SDK_ERROR')

    async def test_auth_smtp_secret_dropped_identifiers_remain(self):
        record = dict(REAL_AUTH_CONFIG)
        provider = dict(record['email_oauth_provider'])
        provider['smtp_config'] = dict(provider['smtp_config'], smtp_pwd='fixture-secret',
                                       smtp_password='fixture-secret')
        record['email_oauth_provider'] = provider
        github = dict(record['github_oauth_provider'], client_secret='fixture-secret',
                      oauth_client_id='client-id-1')
        record['github_oauth_provider'] = github
        self.client.request.return_value = (200, record)
        row = (await self.ops.read('auth', 'app-1'))['data']
        self.assertNotIn('smtp_pwd', row['email_oauth_provider']['smtp_config'])
        self.assertNotIn('smtp_password', row['email_oauth_provider']['smtp_config'])
        self.assertNotIn('client_secret', row['github_oauth_provider'])
        self.assertEqual(row['github_oauth_provider']['oauth_client_id'], 'client-id-1')
        self.assertNotIn('fixture-secret', str(row))

    async def test_auth_malformed_fails_closed(self):
        for payload in ([], 'x', None):
            self.client.request.return_value = (200, payload)
            with self.subTest(payload=payload):
                with self.assertRaises(McpToolError):
                    await self.ops.read('auth', 'app-1')


APP_ID = 'ad9079c304464c33a4f2fd516d4a3b16in32'
INSTANCE_ID = 'ee36e15f94ed4432adb3ada163620d82in03'


class ManagedInstanceDeleteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from mcp_server_supabase.service.plans import PlanStore
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'SUPABASE_ENABLE_WRITES': 'true',
                                           'HUAWEICLOUD_MCP_READ_ONLY': 'false'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.client = AsyncMock()
        self.client.endpoint = 'https://example.invalid'; self.client.project = 'project'; self.client.token = 'fixture'
        self.ops = Operations(self.client, PlanStore(Path(self.tmp.name) / 'state.db'))

    def detail(self, **overrides):
        detail = dict(REAL_DETAIL)
        detail['managed_instance'] = dict(REAL_DETAIL['managed_instance'])
        detail.update(overrides)
        detail.setdefault('status', 'normal')
        detail.setdefault('current_actions', [])
        if detail['status'] == 'abnormal' and 'status' not in overrides:
            detail['status'] = 'normal'
        return detail

    def sweep(self, rows):
        return {'total_count': len(rows), 'data': rows}

    async def test_preview_is_local_only(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.assertEqual(preview['status'], 'confirmation_required')
        self.assertEqual(preview['instance_id'], INSTANCE_ID)
        self.assertTrue(any('irreversibly' in w for w in preview['warnings']))
        self.client.request.assert_not_awaited()

    async def test_confirm_deletes_verified_instance(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 1, 'instances': [{'id': INSTANCE_ID, 'name': 'rds-supabase-pg-01309873', 'status': 'ACTIVE'}]}),
            (200, {'job_id': 'job-77'}),
        ]
        result = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['job_id'], 'job-77')
        self.assertEqual(result['instance_name'], 'rds-supabase-pg-01309873')
        self.assertEqual(self.client.request.call_args_list[-1].args, ('DELETE', '/v3/{project}/instances/' + INSTANCE_ID))
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'accepted')
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['job_id'], 'job-77')

    async def test_binding_mismatch_blocks_before_delete(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.return_value = (200, self.detail(managed_instance={'id': 'other-instance'}))
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')
        self.assertEqual(self.client.request.await_count, 1)
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'prepared')

    async def test_missing_managed_instance_blocks(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        detail = self.detail(); detail.pop('managed_instance')
        self.client.request.return_value = (200, detail)
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')

    async def test_unknown_application_fails_closed(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.return_value = (200, {'id': 'someone-else'})
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_NOT_FOUND')
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'prepared')

    async def test_other_application_reference_blocks(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}},
                              {'id': 'other-app', 'managed_instance': {'id': INSTANCE_ID}}])),
        ]
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')
        self.assertEqual(self.client.request.await_count, 2)
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'prepared')

    async def test_instance_absent_from_inventory_blocks(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 0, 'instances': []}),
        ]
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_NOT_FOUND')

    async def test_definite_rejection_marks_failed(self):
        from mcp_server_supabase.failures import RecoveryError
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 1, 'instances': [{'id': INSTANCE_ID}]}),
            RecoveryError('MCP_INVALID_ARGS', 'bad', 'invalid_request', 'fix it'),
        ]
        with self.assertRaises(McpToolError):
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'failed')

    async def test_transport_failure_marks_unknown(self):
        from mcp_server_supabase.failures import RecoveryError
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 1, 'instances': [{'id': INSTANCE_ID}]}),
            RecoveryError('MCP_SDK_ERROR', 'boom', 'service_unavailable', 'retry later'),
        ]
        with self.assertRaises(McpToolError):
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'unknown')

    async def test_response_without_job_marks_unknown(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 1, 'instances': [{'id': INSTANCE_ID}]}),
            (200, {}),
        ]
        with self.assertRaises(McpToolError):
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'], 'unknown')

    async def test_replay_is_rejected(self):
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 1, 'instances': [{'id': INSTANCE_ID}]}),
            (200, {'job_id': 'job-77'}),
        ]
        await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.sweep([{'id': APP_ID, 'managed_instance': {'id': INSTANCE_ID}}])),
            (200, {'total_count': 1, 'instances': [{'id': INSTANCE_ID}]}),
        ]
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')

    async def test_readonly_gate_blocks_before_any_call(self):
        import os
        from unittest.mock import patch
        preview = await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID)
        with patch.dict(os.environ, {'HUAWEICLOUD_MCP_READ_ONLY': 'true'}):
            with self.assertRaises(McpToolError) as ctx:
                await self.ops.delete_managed_instance(APP_ID, INSTANCE_ID, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_READ_ONLY')
        self.client.request.assert_not_awaited()


class DeleteApplicationWithInstanceTests(unittest.IsolatedAsyncioTestCase):
    APP = 'ad9079c304464c33a4f2fd516d4a3b16in32'
    INSTANCE = 'ee36e15f94ed4432adb3ada163620d82in03'

    def setUp(self):
        import os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from mcp_server_supabase.service.plans import PlanStore
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'SUPABASE_ENABLE_WRITES': 'true',
                                           'HUAWEICLOUD_MCP_READ_ONLY': 'false'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.client = AsyncMock()
        self.client.endpoint = 'https://example.invalid'; self.client.project = 'project'; self.client.token = 'fixture'
        self.ops = Operations(self.client, PlanStore(Path(self.tmp.name) / 'state.db'))

    def detail(self, **overrides):
        detail = dict(REAL_DETAIL)
        detail['managed_instance'] = dict(REAL_DETAIL['managed_instance'])
        detail.update(overrides)
        detail.setdefault('status', 'normal')
        detail.setdefault('current_actions', [])
        if detail['status'] == 'abnormal' and 'status' not in overrides:
            detail['status'] = 'normal'
        return detail

    def apps_page(self, rows):
        return {'total_count': len(rows), 'data': rows}

    async def test_choice_is_mandatory(self):
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_application(self.APP, None)
        self.assertEqual(ctx.exception.code, 'MCP_INVALID_ARGS')
        self.assertIn('delete_managed_instance', ctx.exception.message)

    async def test_preview_no_shows_both_paths(self):
        preview = await self.ops.delete_application(self.APP, False)
        self.assertEqual(preview['status'], 'confirmation_required')
        self.assertEqual(preview['delete_managed_instance'], False)
        self.assertTrue(any('retained' in w for w in preview['warnings']))
        self.assertTrue(any('charges' in w for w in preview['warnings']))
        self.assertEqual(self.client.request.await_count, 0)

    async def test_preview_yes_warns_irreversible(self):
        preview = await self.ops.delete_application(self.APP, True)
        self.assertEqual(preview['delete_managed_instance'], True)
        self.assertTrue(any('irreversibly' in w for w in preview['warnings']))
        self.assertTrue(any('simultaneously' in w for w in preview['warnings']))
        self.assertEqual(self.client.request.await_count, 0)

    async def test_no_path_deletes_application_only(self):
        preview = await self.ops.delete_application(self.APP, False)
        self.client.request.side_effect = [
            (200, self.detail()),                          # readiness read
            (202, {'job_id': 'job-app'}),                  # application delete
        ]
        result = await self.ops.delete_application(self.APP, False, True, preview['plan_id'])
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['job_id'], 'job-app')
        self.assertIsNone(result.get('instance_deletion'))
        calls = [c.args for c in self.client.request.call_args_list]
        self.assertEqual(len(calls), 2)                    # no instance reads at all

    async def test_yes_path_deletes_application_and_instance_together(self):
        preview = await self.ops.delete_application(self.APP, True)
        self.client.request.side_effect = [
            (200, self.detail()),                                                   # application readiness
            # instance preflight (before submission, while the app is readable)
            (200, self.apps_page([{'id': self.APP, 'managed_instance': {'id': self.INSTANCE}}])),
            (200, {'total_count': 1, 'instances': [{'id': self.INSTANCE, 'name': 'pg-1'}]}),
            (202, {'job_id': 'job-app'}),                                           # application delete
            (200, {'job_id': 'job-inst'}),                                          # instance delete
        ]
        result = await self.ops.delete_application(self.APP, True, True, preview['plan_id'])
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['job_id'], 'job-app')
        self.assertEqual(result['instance_job_id'], 'job-inst')
        self.assertEqual(result['instance_id'], self.INSTANCE)
        self.assertTrue(any('separate cloud tasks' in w for w in result['warnings']))

    async def test_yes_path_missing_managed_instance_fails_closed_before_submission(self):
        preview = await self.ops.delete_application(self.APP, True)
        detail = self.detail(); detail.pop('managed_instance')
        self.client.request.side_effect = [
            (200, detail),
        ]
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_application(self.APP, True, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')
        # no deletion submitted: only the readiness read happened
        methods = [c.args[0] for c in self.client.request.call_args_list]
        self.assertEqual(methods, ['GET'])

    async def test_yes_path_unshared_check_blocks_before_submission(self):
        preview = await self.ops.delete_application(self.APP, True)
        self.client.request.side_effect = [
            (200, self.detail()),
            (200, self.apps_page([{'id': self.APP, 'managed_instance': {'id': self.INSTANCE}},
                                  {'id': 'other', 'managed_instance': {'id': self.INSTANCE}}])),
        ]
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_application(self.APP, True, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')
        methods = [c.args[0] for c in self.client.request.call_args_list]
        self.assertEqual(methods, ['GET', 'GET'])

    async def test_readonly_gate_blocks_before_any_write(self):
        import os
        from unittest.mock import patch
        preview = await self.ops.delete_application(self.APP, False)
        with patch.dict(os.environ, {'HUAWEICLOUD_MCP_READ_ONLY': 'true'}):
            with self.assertRaises(McpToolError) as ctx:
                await self.ops.delete_application(self.APP, False, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_READ_ONLY')
        self.assertEqual(self.client.request.await_count, 0)

    async def test_replay_rejected(self):
        preview = await self.ops.delete_application(self.APP, False)
        self.client.request.side_effect = [
            (200, self.detail()),
            (202, {'job_id': 'job-app'}),
        ]
        await self.ops.delete_application(self.APP, False, True, preview['plan_id'])
        self.client.request.side_effect = [
            (200, self.detail()),
        ]
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_application(self.APP, False, True, preview['plan_id'])
        self.assertEqual(ctx.exception.code, 'MCP_GUARDRAIL_BLOCKED')

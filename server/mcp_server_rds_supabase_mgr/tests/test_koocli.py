import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.client.koocli import KoocliClient, flatten_params, parse_payload, region_from_env


class FakeProcess:
    def __init__(self, returncode=0, stdout=b'', stderr=b''):
        self.returncode = None
        self._returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    async def communicate(self):
        self.returncode = self._returncode
        return self._stdout, self._stderr

    async def wait(self):
        self.returncode = self._returncode

    def kill(self):
        self.killed = True


def client(**kwargs):
    defaults = dict(binary='/usr/local/bin/hcloud', region='cn-north-4',
                    ak='AK', sk='SK', security_token='', timeout=5)
    defaults.update(kwargs)
    return KoocliClient(**defaults)


class FlattenTests(unittest.TestCase):
    def test_flat_nested_and_list_params(self):
        self.assertEqual(flatten_params({'limit': 10}), ['--limit=10'])
        self.assertEqual(flatten_params({'security_group': {'name': 'g', 'description': 'd'}}),
                         ['--security_group.name=g', '--security_group.description=d'])
        self.assertEqual(flatten_params({'security_group_id': ['a', 'b']}), ['--security_group_id.1=a', '--security_group_id.2=b'])
        self.assertEqual(flatten_params(None), [])

    def test_region_resolution(self):
        with patch.dict(os.environ, {'HUAWEICLOUD_REGION': 'cn-east-3', 'SUPABASE_RDS_ENDPOINT': 'https://rds.cn-north-4.myhuaweicloud.com'}):
            self.assertEqual(region_from_env(), 'cn-east-3')
        with patch.dict(os.environ, {'HUAWEICLOUD_REGION': ''}):
            os.environ.pop('HUAWEICLOUD_REGION', None)
            with patch.dict(os.environ, {'SUPABASE_RDS_ENDPOINT': 'https://rds.cn-north-4.myhuaweicloud.com'}, clear=False):
                self.assertEqual(region_from_env(), 'cn-north-4')
            with patch.dict(os.environ, {'SUPABASE_RDS_ENDPOINT': 'http://10.0.0.1:8443'}, clear=False):
                self.assertEqual(region_from_env(), '')

    def test_region_defaults_from_env_at_construction(self):
        with patch.dict(os.environ, {'HUAWEICLOUD_REGION': 'la-south-2'}):
            cli = KoocliClient(binary='/usr/local/bin/hcloud')
            argv = cli.argv('VPC', 'ListSecurityGroups', {'limit': 1})
            self.assertIn('--cli-region=la-south-2', argv)
        with patch.dict(os.environ, {'HUAWEICLOUD_REGION': ''}, clear=False):
            os.environ.pop('HUAWEICLOUD_REGION', None)
            cli = KoocliClient(binary='/usr/local/bin/hcloud')
            self.assertEqual(cli.region, '')

    def test_argv_injects_region_and_credentials(self):
        argv = client().argv('VPC', 'CreateSecurityGroup', {'security_group': {'name': 'app'}})
        self.assertEqual(argv, ['/usr/local/bin/hcloud', 'VPC', 'CreateSecurityGroup',
                                '--security_group.name=app', '--cli-region=cn-north-4',
                                '--cli-access-key=AK', '--cli-secret-key=SK'])
        argv = client(security_token='TOK').argv('VPC', 'ShowSecurityGroup', {'security_group_id': 'g'})
        self.assertIn('--cli-security-token=TOK', argv)
        argv = client(ak='', sk='').argv('VPC', 'ListSecurityGroups')
        self.assertEqual(argv, ['/usr/local/bin/hcloud', 'VPC', 'ListSecurityGroups', '--cli-region=cn-north-4'])
        argv = client(region='').argv('VPC', 'ListSecurityGroups')
        self.assertEqual(argv, ['/usr/local/bin/hcloud', 'VPC', 'ListSecurityGroups',
                                '--cli-access-key=AK', '--cli-secret-key=SK'])

    def test_missing_binary_is_rejected_before_spawn(self):
        with self.assertRaises(McpToolError) as ctx:
            client(binary='').argv('VPC', 'ListSecurityGroups')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_MISSING')

    def test_token_fingerprint_binds_credentials_and_region(self):
        self.assertNotEqual(client().token, client(region='cn-east-3').token)
        self.assertNotEqual(client().token, client(sk='OTHER').token)
        self.assertEqual(client().token, client().token)


class CallTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_parses_json_after_preamble(self):
        proc = FakeProcess(stdout=b'hcloud 7.3.12\n{"security_groups": []}')
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            data = await client().call('VPC', 'ListSecurityGroups', {'limit': 10})
        self.assertEqual(data, {'security_groups': []})

    async def test_empty_output_is_empty_dict(self):
        proc = FakeProcess(stdout=b'')
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            self.assertEqual(await client().call('VPC', 'DeleteSecurityGroupRule', {'security_group_rule_id': 'r'}), {})

    async def test_api_error_is_passed_through(self):
        payload = b'{"error_code": "VPC.0403", "error_msg": "denied", "request_id": "req-1"}'
        proc = FakeProcess(returncode=1, stdout=payload)
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            with self.assertRaises(McpToolError) as ctx:
                await client().call('VPC', 'CreateSecurityGroup')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_ERROR')
        self.assertIn('VPC.0403', ctx.exception.message)
        self.assertIn('req-1', ctx.exception.message)

    async def test_privacy_agreement_signature_is_actionable(self):
        proc = FakeProcess(returncode=1, stdout='[USE_ERROR]您输入的是无效字符'.encode())
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            with self.assertRaises(McpToolError) as ctx:
                await client().call('VPC', 'ListSecurityGroups')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_BLOCKED')
        self.assertIn('hcloud version', ctx.exception.hint)

    async def test_unparseable_failure_includes_bounded_snippet(self):
        proc = FakeProcess(returncode=1, stdout=b'connection refused by peer')
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            with self.assertRaises(McpToolError) as ctx:
                await client().call('VPC', 'ListSecurityGroups')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_ERROR')
        self.assertIn('connection refused', ctx.exception.message)

    async def test_timeout_kills_process(self):
        class SlowProcess(FakeProcess):
            async def communicate(self):
                await asyncio.sleep(30)
        proc = SlowProcess()
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            with self.assertRaises(McpToolError) as ctx:
                await client(timeout=0.05).call('VPC', 'ListSecurityGroups')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_TIMEOUT')
        self.assertTrue(proc.killed)

    async def test_spawn_failure_maps_to_missing(self):
        with patch('asyncio.create_subprocess_exec', AsyncMock(side_effect=FileNotFoundError())):
            with self.assertRaises(McpToolError) as ctx:
                await client().call('VPC', 'ListSecurityGroups')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_MISSING')


class ParseTests(unittest.TestCase):
    def test_parse_payload_shapes(self):
        self.assertEqual(parse_payload(''), {})
        self.assertEqual(parse_payload('  \n'), {})
        self.assertEqual(parse_payload('x\n{"a": 1}'), {'a': 1})
        with self.assertRaises(McpToolError):
            parse_payload('no json here')


if __name__ == '__main__':
    unittest.main()


class UseErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_exit_zero_use_error_surfaces_real_text(self):
        # KooCLI reports unsupported operations as exit code 0 with a [USE_ERROR]
        # line on stdout; the real text must surface instead of "no JSON payload".
        proc = FakeProcess(stdout=b'[USE_ERROR]Operation ListSubnets/v3 is not supported.\n\nYou may want to select one of the following operations:')
        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=proc)):
            with self.assertRaises(McpToolError) as ctx:
                await client().call('VPC', 'ListSubnets/v3')
        self.assertEqual(ctx.exception.code, 'MCP_CLI_ERROR')
        self.assertIn('ListSubnets/v3 is not supported', ctx.exception.message)

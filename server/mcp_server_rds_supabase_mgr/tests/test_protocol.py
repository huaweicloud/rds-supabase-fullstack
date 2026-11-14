"""Exercise the real stdio boundary without cloud credentials or network calls."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_arguments_are_rejected_without_echo_or_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'plans.db'
            env = {**os.environ, 'SUPABASE_STATE_FILE':str(state),
                   'HUAWEICLOUD_MCP_READ_ONLY':'false', 'SUPABASE_ENABLE_WRITES':'false'}
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'mcp_server_supabase.main'], env=env)
            with tempfile.TemporaryFile(mode='w+') as errors:
                async with stdio_client(params, errlog=errors) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        for name, args in (
                            ('plan_supabase_creation', {'manage_type':'newly_instance'}),
                            ('change_supabase_ssl', {'application_id':'fixture-app','enable_ssl':False}),
                        ):
                            result = await session.call_tool(name, {**args, 'unsupported_marker':'private-marker-value'})
                            payload = result.structured_content or json.loads(result.content[0].text)
                            self.assertEqual(payload.get('error', {}).get('code'), 'MCP_INVALID_ARGS')
                            self.assertNotIn('private-marker-value', str(result))
                        tools = await session.list_tools()
                        self.assertTrue(all(t.input_schema.get('additionalProperties') is False for t in tools.tools))
                errors.seek(0)
                self.assertNotIn('private-marker-value', errors.read())
            self.assertFalse(state.exists(), 'Rejected requests must not issue plans')

    async def test_write_preview_over_stdio(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, 'SUPABASE_STATE_FILE':str(Path(directory)/'plans.db'),
                   'HUAWEICLOUD_MCP_READ_ONLY':'false', 'SUPABASE_ENABLE_WRITES':'false'}
            params = StdioServerParameters(command=sys.executable,
                args=['-m','mcp_server_supabase.main'], env=env)
            with tempfile.TemporaryFile(mode='w+') as errors:
                async with stdio_client(params, errlog=errors) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool('change_supabase_ssl', {'application_id':'fixture-app','enable_ssl':False})
                        preview = result.structured_content or json.loads(result.content[0].text)
                        self.assertEqual(preview['status'], 'confirmation_required')
                        self.assertTrue(preview['plan_id'])
                        result = await session.call_tool('get_supabase_capabilities', {})
                        capabilities = result.structured_content or json.loads(result.content[0].text)
                        self.assertEqual(len(capabilities['scenarios']), 6)
                        self.assertTrue(capabilities['implemented_operations'])

    async def test_read_only_blocks_write_tools_over_stdio(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, 'SUPABASE_STATE_FILE':str(Path(directory)/'plans.db'),
                   'HUAWEICLOUD_MCP_READ_ONLY':'true', 'SUPABASE_ENABLE_WRITES':'false'}
            params = StdioServerParameters(command=sys.executable,
                args=['-m','mcp_server_supabase.main'], env=env)
            with tempfile.TemporaryFile(mode='w+') as errors:
                async with stdio_client(params, errlog=errors) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool('change_supabase_ssl', {'application_id':'fixture-app','enable_ssl':False})
                        payload = result.structured_content or json.loads(result.content[0].text)
                        self.assertEqual(payload['error']['code'], 'MCP_READ_ONLY')

    async def test_job_tools_discoverable_and_locally_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'plans.db'
            env={k:v for k,v in os.environ.items() if not k.startswith(('HUAWEICLOUD_','SUPABASE_'))}
            env.update({'SUPABASE_STATE_FILE':str(state),'HUAWEICLOUD_MCP_READ_ONLY':'true','SUPABASE_ENABLE_WRITES':'false'})
            params=StdioServerParameters(command=sys.executable,args=['-m','mcp_server_supabase.main'],env=env)
            with tempfile.TemporaryFile(mode='w+') as errors:
                async with stdio_client(params,errlog=errors) as (read,write):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        tools=await session.list_tools()
                        names={t.name for t in tools.tools}
                        self.assertIn('show_operation_job_status',names)
                        self.assertIn('wait_operation_job_complete',names)
                        for name in ('inspect_supabase_plan','cancel_supabase_plan','reconcile_supabase_auth_plan'):
                            self.assertNotIn(name,names)
                        result=await session.call_tool('wait_operation_job_complete',{'job_id':'fixture-job','max_attempts':99})
                        payload=result.structured_content or json.loads(result.content[0].text)
                        self.assertEqual(payload['error']['code'],'MCP_INVALID_ARGS')
                        result=await session.call_tool('show_operation_job_status',{'job_id':'../bad'})
                        payload=result.structured_content or json.loads(result.content[0].text)
                        self.assertEqual(payload['error']['code'],'MCP_INVALID_ARGS')
            self.assertFalse(state.exists())

    async def test_new_secret_previews_cross_real_stdio_without_leaks(self):
        with tempfile.TemporaryDirectory() as directory:
            registry=Path(directory)/'requests.json'
            registry.write_text(json.dumps({'password':{'application_password':'fixture-sensitive-value'},'storage':{'enabled':True,'bucket_name':'fixture-bucket','ak':'fixture-ak','sk':'fixture-sensitive-value'},'auth':{'email_oauth_provider':{'smtp_config':{'smtp_pwd':'fixture-sensitive-value'}}}}));registry.chmod(0o600)
            env={k:v for k,v in os.environ.items() if not k.startswith(('HUAWEICLOUD_','SUPABASE_'))}
            env.update({'SUPABASE_REQUESTS_FILE':str(registry),'SUPABASE_STATE_FILE':str(Path(directory)/'plans.db'),'HUAWEICLOUD_MCP_READ_ONLY':'false','SUPABASE_ENABLE_WRITES':'false'})
            params=StdioServerParameters(command=sys.executable,args=['-m','mcp_server_supabase.main'],env=env)
            with tempfile.TemporaryFile(mode='w+') as errors:
                async with stdio_client(params,errlog=errors) as (read,write):
                    async with ClientSession(read,write) as session:
                        await session.initialize();tools=await session.list_tools()
                        self.assertEqual(len(tools.tools),32)
                        for name,ref in [('change_supabase_application_password','password'),('update_supabase_storage','storage'),('update_supabase_auth_config','auth')]:
                            result=await session.call_tool(name,{'application_id':'fixture-app','request_ref':ref})
                            payload=result.structured_content or json.loads(result.content[0].text)
                            self.assertEqual(payload['status'],'confirmation_required')
                            self.assertNotIn('fixture-sensitive-value',str(result))
                errors.seek(0);self.assertNotIn('fixture-sensitive-value',errors.read())

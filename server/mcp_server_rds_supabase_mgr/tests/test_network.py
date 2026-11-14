import os
import tempfile
import unittest
from pathlib import Path
from huaweicloud_mcp_core.errors import McpToolError

GROUP='11111111-1111-4111-8111-111111111111'
RULE='22222222-2222-4222-8222-222222222222'
TAGS=[{'key':'AUTO_CREATE','value':'true'},{'key':'USE_FOR','value':'Supabase'}]

def tagged_group(group_id=GROUP,tags=TAGS):
    return {'security_group':{'id':group_id,'tags':list(tags or []),'security_group_rules':[]}}

class FakeKoocli:
    def __init__(self):
        self.region='cn-north-4'
        self.token='fixture'
        self.calls=[]
        self.results=[]

    def push(self,result):
        self.results.append(result)

    async def call(self,service,operation,params=None):
        self.calls.append((service,operation,params))
        result=self.results.pop(0)
        if isinstance(result,Exception):raise result
        return result

    def last(self):
        return self.calls[-1]


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from mcp_server_supabase.service.network import Network
        from mcp_server_supabase.service.plans import PlanStore
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.koocli=FakeKoocli()
        self.ops=Network(self.koocli,PlanStore(Path(self.tmp.name)/'state.db'))
        self.env=os.environ.copy()
        os.environ['SUPABASE_ENABLE_WRITES']='true';os.environ['HUAWEICLOUD_MCP_READ_ONLY']='false'
        self.addCleanup(lambda:os.environ.clear() or os.environ.update(self.env))

    async def test_list_and_show_use_v3_operations(self):
        self.koocli.push({'security_groups':[]})
        await self.ops.list_groups(10)
        self.assertEqual(self.koocli.last(),('VPC','ListSecurityGroups/v3',{'limit':10}))
        self.koocli.push({'security_group':{'id':GROUP}})
        await self.ops.show_group(GROUP)
        self.assertEqual(self.koocli.last(),('VPC','ShowSecurityGroup/v3',{'security_group_id':GROUP}))

    async def test_show_unifies_separate_rules_shape(self):
        self.koocli.push({'security_group':{'id':GROUP},'security_group_rules':[{'id':RULE,'security_group_id':GROUP}]})
        result=await self.ops.show_group(GROUP)
        self.assertEqual(result['data']['security_group_rules'][0]['id'],RULE)

    async def test_group_create_is_not_rule_creation(self):
        preview=await self.ops.create_group('app-group')
        self.assertEqual(self.koocli.calls,[])
        self.koocli.push({'security_group':{'id':GROUP}})
        result=await self.ops.create_group('app-group',confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(result['resource_id'],GROUP)
        service,operation,params=self.koocli.last()
        self.assertEqual(operation,'CreateSecurityGroup/v3')
        self.assertEqual(params['security_group']['name'],'app-group')
        self.assertEqual(params['security_group']['tags'],TAGS)

    async def test_group_create_carries_purpose_description(self):
        description='Supabase应用（自动创建）'
        preview=await self.ops.create_group('supabase-app-group',description)
        self.assertEqual(preview['changes']['security_group']['description'],description)
        self.koocli.push({'security_group':{'id':GROUP}})
        await self.ops.create_group('supabase-app-group',description,True,preview['plan_id'])
        service,operation,params=self.koocli.last()
        self.assertEqual(params['security_group']['name'],'supabase-app-group')
        self.assertEqual(params['security_group']['description'],description)
        self.assertEqual(params['security_group']['tags'],TAGS)
        self.assertEqual(preview['changes']['security_group']['tags'],TAGS)
        for bad in ('x'*256,'<script>'):
            with self.assertRaises(McpToolError):
                await self.ops.create_group('g',bad)

    async def test_native_single_rule_body_and_no_replay(self):
        preview=await self.ops.add_rule(GROUP,'192.0.2.0/24',8443)
        self.assertEqual(preview['changes']['security_group_rule']['direction'],'ingress')
        self.assertEqual(preview['changes']['security_group_rule']['priority'],1)
        self.koocli.push({'security_group':{'id':GROUP,'security_group_rules':[]}})
        self.koocli.push({'security_group_rule':{'id':RULE,'security_group_id':GROUP}})
        result=await self.ops.add_rule(GROUP,'192.0.2.0/24',8443,confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(result['resource_id'],RULE)
        service,operation,params=self.koocli.last()
        self.assertEqual(operation,'CreateSecurityGroupRule/v3')
        self.assertEqual(params['security_group_rule']['security_group_id'],GROUP)
        self.assertEqual(params['security_group_rule']['multiport'],'8443')
        self.koocli.push({'security_group':{'id':GROUP,'security_group_rules':[]}})
        with self.assertRaises(McpToolError):await self.ops.add_rule(GROUP,'192.0.2.0/24',8443,confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'accepted')

    async def test_egress_rule_direction_and_protocol(self):
        preview=await self.ops.add_rule(GROUP,'192.0.2.0/24',5432,'egress','tcp')
        self.assertEqual(preview['changes']['security_group_rule']['direction'],'egress')
        self.koocli.push({'security_group':{'id':GROUP,'security_group_rules':[]}})
        self.koocli.push({'security_group_rule':{'id':RULE,'security_group_id':GROUP}})
        await self.ops.add_rule(GROUP,'192.0.2.0/24',5432,'egress','tcp',True,preview['plan_id'])
        _,operation,params=self.koocli.last()
        self.assertEqual(params['security_group_rule']['direction'],'egress')
        self.assertEqual(params['security_group_rule']['protocol'],'tcp')
        self.assertEqual(params['security_group_rule']['multiport'],'5432')

    async def test_delete_checks_ownership_then_applies(self):
        preview=await self.ops.delete_rule(GROUP,RULE)
        self.koocli.push({'security_group':{'id':GROUP,'security_group_rules':[{'id':'other','security_group_id':GROUP}]}})
        with self.assertRaises(McpToolError):await self.ops.delete_rule(GROUP,RULE,True,preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'prepared')
        self.koocli.push({'security_group':{'id':GROUP,'security_group_rules':[{'id':RULE,'security_group_id':GROUP}]}})
        self.koocli.push({})
        result=await self.ops.delete_rule(GROUP,RULE,True,preview['plan_id'])
        self.assertEqual(result['status'],'applied');self.assertFalse(result['completion_verified'])
        self.assertEqual(self.koocli.last(),('VPC','DeleteSecurityGroupRule/v3',{'security_group_rule_id':RULE}))
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'accepted')

    async def test_invalid_or_world_source_and_readonly(self):
        for source in ('0.0.0.0/0','::/0','invalid'):
            with self.assertRaises(McpToolError):await self.ops.add_rule(GROUP,source,8443)
        for direction,protocol in (('in','tcp'),('egress','icmp')):
            with self.assertRaises(McpToolError):await self.ops.add_rule(GROUP,'192.0.2.0/24',8443,direction,protocol)
        with patch_readonly():
            with self.assertRaises(McpToolError):await self.ops.create_group('app-group',True,'fixture')
        self.assertEqual(self.koocli.calls,[])

    async def test_duplicate_rule_prevents_write(self):
        preview=await self.ops.add_rule(GROUP,'192.0.2.0/24',8443)
        self.koocli.push({'security_group':{'id':GROUP,'security_group_rules':[preview['changes']['security_group_rule']]}})
        with self.assertRaises(McpToolError):await self.ops.add_rule(GROUP,'192.0.2.0/24',8443,confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'prepared')

    async def test_malformed_mutation_response_keeps_unknown(self):
        preview=await self.ops.create_group('app-group')
        self.koocli.push({})
        with self.assertRaises(McpToolError):await self.ops.create_group('app-group',confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'unknown')

    async def test_write_failure_keeps_unknown(self):
        preview=await self.ops.create_group('app-group')
        self.koocli.push(McpToolError('MCP_CLI_ERROR','boom'))
        with self.assertRaises(McpToolError):await self.ops.create_group('app-group',confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'unknown')

    async def test_delete_group_flow(self):
        preview=await self.ops.delete_group(GROUP)
        self.assertEqual(preview['status'],'confirmation_required')
        self.assertTrue(any('removes every rule' in w for w in preview['warnings']))
        self.assertEqual(self.koocli.calls,[])
        # identity mismatch blocks the write
        self.koocli.push({'security_group':{'id':'other'}})
        with self.assertRaises(McpToolError):await self.ops.delete_group(GROUP,True,preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'prepared')
        # untagged group is blocked: not created by this flow
        self.koocli.push(tagged_group(tags=[]))
        with self.assertRaises(McpToolError) as ctx:
            await self.ops.delete_group(GROUP,True,preview['plan_id'])
        self.assertEqual(ctx.exception.code,'MCP_GUARDRAIL_BLOCKED')
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'prepared')
        # wrong tag value is blocked too
        self.koocli.push(tagged_group(tags=[{'key':'AUTO_CREATE','value':'true'},{'key':'USE_FOR','value':'Other'}]))
        with self.assertRaises(McpToolError):
            await self.ops.delete_group(GROUP,True,preview['plan_id'])
        # dict-shaped tags are accepted
        self.koocli.push({'security_group':{'id':GROUP,'tags':{'AUTO_CREATE':'true','USE_FOR':'Supabase'},'security_group_rules':[]}})
        self.koocli.push({})
        result=await self.ops.delete_group(GROUP,True,preview['plan_id'])
        self.assertEqual(result['status'],'applied');self.assertEqual(result['resource_id'],GROUP)
        self.assertEqual(self.koocli.last(),('VPC','DeleteSecurityGroup/v3',{'security_group_id':GROUP}))
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'accepted')
        # replay is refused
        self.koocli.push(tagged_group())
        with self.assertRaises(McpToolError):await self.ops.delete_group(GROUP,True,preview['plan_id'])

    async def test_delete_group_write_failure_keeps_unknown(self):
        preview=await self.ops.delete_group(GROUP)
        self.koocli.push(tagged_group())
        self.koocli.push(McpToolError('MCP_CLI_ERROR','in use'))
        with self.assertRaises(McpToolError):await self.ops.delete_group(GROUP,True,preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'unknown')

    async def test_group_identity_failure_blocks_rule_write(self):
        preview=await self.ops.add_rule(GROUP,'192.0.2.0/24',8443)
        self.koocli.push({'security_group':{'id':'other'}})
        with self.assertRaises(McpToolError):await self.ops.add_rule(GROUP,'192.0.2.0/24',8443,confirm=True,plan_id=preview['plan_id'])
        self.assertEqual(len(self.koocli.calls),1)
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'prepared')


class patch_readonly:
    def __enter__(self):
        self.previous=os.environ.get('HUAWEICLOUD_MCP_READ_ONLY')
        os.environ['HUAWEICLOUD_MCP_READ_ONLY']='true'
        return self

    def __exit__(self,*args):
        if self.previous is None:os.environ.pop('HUAWEICLOUD_MCP_READ_ONLY',None)
        else:os.environ['HUAWEICLOUD_MCP_READ_ONLY']=self.previous


if __name__=='__main__':
    unittest.main()

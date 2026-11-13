import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.failures import RecoveryError,http_failure
from mcp_server_supabase.service.operations import Operations
from mcp_server_supabase.service.plans import PlanStore

# Shape of a real, backend-accepted route-A creation payload (passwords replaced
# with a rule-compliant fixture value; every other field verbatim from the
# captured request: ha object, ESSD volume, explicit port 5432, application
# version 1.0.0, parameter-template id, both security groups).
REAL_NEW_PG={'name':'rds-supabase-5a55','basic_config':{'region':'cn-east-3','vpc_id':'fff3b97c-8821-44e5-b16e-788a745292f0','subnet_id':'bba70694-b1aa-47a6-b6d1-cfc9563e0ec2','time_zone':'UTC+08:00'},'storage_component':{'enabled':False},'version':'1.0.0','mode':'Single','flavor_ref':'rds.supabase.n1.large.2','availability_zone':'cn-east-3a','password':'Fixture-Secret1','manage_type':'newly_instance','managed_instance':{'datastore':{'type':'PostgreSQL','version':'17.11.260901'},'ha':{'mode':'Single','replication_mode':'async'},'charge_info':{'charge_mode':'postPaid'},'flavor_ref':'rds.pg.n1.medium.2','volume':{'type':'ESSD','size':40},'availability_zone':'cn-east-3a','security_group_id':'b558b952-7bba-456c-9137-9d8d161ae58b','password':'Fixture-Secret1','port':5432,'enterprise_project_id':'0','configuration_id':'95611c6a-8ede-47e8-88d6-3f0f1adc5b59'},'security_group_id':'7d4fd664-b212-4a54-a5f5-735eacc6cd54'}


def message(error):
    return error.to_dict()['error']['message']


class CreationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.file=Path(self.tmp.name)/'requests.json';self.file.touch(mode=0o600)
        self.env=patch.dict(os.environ,{'SUPABASE_REQUESTS_FILE':str(self.file),'SUPABASE_ENABLE_WRITES':'true','HUAWEICLOUD_MCP_READ_ONLY':'false'});self.env.start();self.addCleanup(self.env.stop)
        self.client=AsyncMock();self.client.endpoint='https://example.invalid';self.client.project='project';self.client.token='fixture'
        self.ops=Operations(self.client,PlanStore(Path(self.tmp.name)/'ledger.db'))
        self.body={'name':'test-app','basic_config':{'region':'region-1','vpc_id':'vpc-id','subnet_id':'subnet-id'},'version':'1.0.0','mode':'Single','flavor_ref':'rds.supabase.a.b.c','availability_zone':'region-1a','password':'Fixture-Secret1','storage_component':{'enabled':False},'manage_type':'existed_instance','existing_instance':{'instance_id':'pg-id','database_name':'supabase','database_pwd':'fixture-secret'}}
    def save(self):self.file.write_text(json.dumps({'create':self.body}))
    async def test_create_existing_is_secret_free_and_returns_all_ids(self):
        self.save();preview=await self.ops.create_reference('create')
        self.assertNotIn('Fixture-Secret1',str(preview));self.assertNotIn('fixture-secret',str(preview));self.client.request.assert_not_awaited()
        self.client.request.return_value=(202,{'job_id':'job','application_id':'app','instance_id':'pg','instance_job_id':'pgjob'})
        result=await self.ops.create_reference('create',True,preview['plan_id'])
        self.assertEqual(result['application_id'],'app');self.assertFalse(result['completion_verified'])
        self.assertEqual(self.client.request.call_args.args,('POST','/v3/{project}/ai-application/supabases'))
        with self.assertRaises(McpToolError):await self.ops.create_reference('create',True,preview['plan_id'])
        self.assertEqual(self.client.request.await_count,1)
    async def test_real_world_new_pg_payload_passes(self):
        self.file.write_text(json.dumps({'create':REAL_NEW_PG}))
        preview=await self.ops.create_reference('create')
        self.assertNotIn('Fixture-Secret1',str(preview))
        self.assertIn("'ha'",str(preview))  # ha is a normal field, not a secret
        self.client.request.return_value=(202,{'job_id':'job','application_id':'app','instance_id':'pg','instance_job_id':'pgjob'})
        result=await self.ops.create_reference('create',True,preview['plan_id'])
        self.assertEqual(result['job_id'],'job');self.assertEqual(result['instance_id'],'pg')
        sent=self.client.request.call_args.kwargs['body']
        self.assertEqual(sent['managed_instance']['ha'],{'mode':'Single','replication_mode':'async'})
        self.assertEqual(sent['managed_instance']['volume'],{'type':'ESSD','size':40})
        self.assertEqual(sent['managed_instance']['port'],5432)
    async def test_field_errors_name_the_offending_field(self):
        cases=[('ha','mode','Ha','ha.mode'),
               ('ha','replication_mode','quic','ha.replication_mode'),
               ('port',None,2000,'port'),
               ('charge_info','charge_mode','prePaid','postPaid')]
        for section,key,value,needle in cases:
            body=copy.deepcopy(REAL_NEW_PG)
            if key is None:body['managed_instance'][section]=value
            else:body['managed_instance'][section][key]=value
            self.file.write_text(json.dumps({'create':body}))
            with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create')
            self.assertIn(needle,message(ctx.exception))
        body=copy.deepcopy(REAL_NEW_PG);body['managed_instance']['hax']='x'
        self.file.write_text(json.dumps({'create':body}))
        with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create')
        self.assertIn('unexpected field',message(ctx.exception));self.assertIn('hax',message(ctx.exception))
        self.client.request.assert_not_awaited()
    async def test_password_composition_rule(self):
        for bad,needle in (('abcdefgh','password'),('Ab1','password'),('A'*33,'password'),('Abcdefgh','at least three')):
            body=copy.deepcopy(REAL_NEW_PG);body['password']=bad
            self.file.write_text(json.dumps({'create':body}))
            with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create')
            self.assertIn(needle,message(ctx.exception))
        body=copy.deepcopy(REAL_NEW_PG);body['managed_instance']['password']='short'
        self.file.write_text(json.dumps({'create':body}))
        with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create')
        self.assertIn('managed_instance.password',message(ctx.exception))
        body=copy.deepcopy(REAL_NEW_PG);body['password']='Abc12345'  # three classes, minimal length
        self.file.write_text(json.dumps({'create':body}))
        await self.ops.create_reference('create')
    async def test_no_ha_deployment_or_implicit_branch_or_unknown_fields(self):
        for key,value in [('mode','Ha'),('manage_type','guess'),('extra','secret')]:
            body=copy.deepcopy(self.body);body[key]=value;self.file.write_text(json.dumps({'create':body}))
            with self.assertRaises(McpToolError):await self.ops.create_reference('create')
        self.client.request.assert_not_awaited()
    async def test_new_pg_validates_branch_and_postpaid_only(self):
        del self.body['existing_instance'];self.body['manage_type']='newly_instance'
        self.body['managed_instance']={'datastore':{'type':'PostgreSQL','version':'16'},'charge_info':{'charge_mode':'postPaid'},'flavor_ref':'pg-flavor','volume':{'type':'CLOUDSSD','size':100},'availability_zone':'region-1a','security_group_id':'11111111-1111-4111-8111-111111111111','password':'Fixture-Secret1','enterprise_project_id':'0'}
        self.save();preview=await self.ops.create_reference('create');self.assertNotIn('Fixture-Secret1',str(preview))
        self.body['managed_instance']['charge_info']['charge_mode']='prePaid';self.save()
        with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create')
        self.assertIn('postPaid',message(ctx.exception))
    async def test_volume_type_follows_environment_selection(self):
        del self.body['existing_instance'];self.body['manage_type']='newly_instance'
        base={'datastore':{'type':'PostgreSQL','version':'16'},'charge_info':{'charge_mode':'postPaid'},'flavor_ref':'pg-flavor','volume':{'type':'CLOUDSSD','size':100},'availability_zone':'region-1a','security_group_id':'11111111-1111-4111-8111-111111111111','password':'Fixture-Secret1','enterprise_project_id':'0'}
        for vol in ({'type':'ESSD','size':80},{'type':'GPSSD','size':40}):
            body=copy.deepcopy(self.body);body['managed_instance']=copy.deepcopy(base);body['managed_instance']['volume']=vol;self.file.write_text(json.dumps({'create':body}))
            await self.ops.create_reference('create')
        for vol in ({'type':'','size':80},{'type':'CLOUDSSD','size':0},{'type':'CLOUDSSD','size':'big'}):
            body=copy.deepcopy(self.body);body['managed_instance']=copy.deepcopy(base);body['managed_instance']['volume']=vol;self.file.write_text(json.dumps({'create':body}))
            with self.assertRaises(McpToolError):await self.ops.create_reference('create')
        self.client.request.assert_not_awaited()
    async def test_backend_rejection_marks_failed_and_allows_repreview(self):
        self.file.write_text(json.dumps({'create':REAL_NEW_PG}))
        preview=await self.ops.create_reference('create')
        self.client.request.side_effect=McpToolError('MCP_INVALID_ARGS','API returned HTTP 400 (backend: error_code=DBS.280002, error_msg=flavor not available)')
        with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create',True,preview['plan_id'])
        self.assertIn('DBS.280002',message(ctx.exception));self.assertIn('flavor not available',message(ctx.exception))
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'failed')
        self.client.request.side_effect=None
        self.client.request.return_value=(202,{'job_id':'job','application_id':'app'})
        retry=await self.ops.create_reference('create')
        result=await self.ops.create_reference('create',True,retry['plan_id'])
        self.assertEqual(result['job_id'],'job');self.assertEqual(self.ops.plans.inspect(retry['plan_id'])['state'],'accepted')
    async def test_ambiguous_failure_marks_unknown_and_blocks_replay(self):
        self.file.write_text(json.dumps({'create':REAL_NEW_PG}))
        preview=await self.ops.create_reference('create')
        self.client.request.side_effect=RecoveryError('MCP_SDK_ERROR','Request result unavailable','transport_or_response','Verify connectivity.')
        with self.assertRaises(RecoveryError) as ctx:await self.ops.create_reference('create',True,preview['plan_id'])
        self.assertEqual(message(ctx.exception),'Creation result unknown')
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'unknown')
        retry=await self.ops.create_reference('create')
        with self.assertRaises(McpToolError) as ctx:await self.ops.create_reference('create',True,retry['plan_id'])
        self.assertIn('unresolved execution',message(ctx.exception))
    async def test_unexpected_order_and_transport_result_are_not_success(self):
        self.save();preview=await self.ops.create_reference('create')
        self.client.request.return_value=(202,{'order_id':'order'})
        with self.assertRaises(McpToolError):await self.ops.create_reference('create',True,preview['plan_id'])
        self.assertEqual(self.ops.plans.inspect(preview['plan_id'])['state'],'unknown')
    def test_http_failure_carries_backend_detail(self):
        error=http_failure(400,{'error_code':'DBS.280002','error_msg':'flavor not available'})
        text=message(error)
        self.assertIn('HTTP 400',text);self.assertIn('error_code=DBS.280002',text);self.assertIn('error_msg=flavor not available',text)
        self.assertEqual(message(http_failure(503,None)),'API returned HTTP 503')

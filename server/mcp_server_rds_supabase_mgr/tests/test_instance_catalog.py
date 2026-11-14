import unittest
from huaweicloud_mcp_core.errors import McpToolError


class FakeKoocli:
    def __init__(self):
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


class InstanceCatalogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from mcp_server_supabase.service.instance_catalog import InstanceCatalog
        self.koocli=FakeKoocli()
        self.catalog=InstanceCatalog(self.koocli)

    async def test_engine_versions_happy_path(self):
        rows=[{'id':'ds-15','name':'15'},{'id':'ds-17','name':'17'}]
        self.koocli.push({'dataStores':rows})
        result=await self.catalog.list_engine_versions()
        self.assertEqual(self.koocli.last(),('RDS','ListDatastores',{'database_name':'PostgreSQL'}))
        self.assertEqual(result['data'],rows)
        self.assertIn('create-with-new-instance',result['note'])
        self.assertIn('az_status',result['note'])

    async def test_flavors_happy_path_with_major_version(self):
        rows=[{'spec_code':'rds.pg.xlarge.arm','vcpus':4,'ram':16,
               'az_status':{'cn-east-3a':'normal'},'instance_mode':'single','version_name':'17'}]
        self.koocli.push({'flavors':rows})
        result=await self.catalog.list_flavors('17')
        self.assertEqual(self.koocli.last(),('RDS','ListFlavors',
                                             {'database_name':'PostgreSQL','version_name':'17'}))
        self.assertEqual(result['data'],rows)

    async def test_flavors_without_version_omits_the_key(self):
        self.koocli.push({'flavors':[]})
        result=await self.catalog.list_flavors()
        service,operation,params=self.koocli.last()
        self.assertEqual((service,operation),('RDS','ListFlavors'))
        self.assertEqual(params,{'database_name':'PostgreSQL'})
        self.assertNotIn('version_name',params)
        self.assertEqual(result['data'],[])

    async def test_flavors_rejects_non_major_versions_before_any_call(self):
        for bad in ('17.11.260901','','x','123'):
            with self.assertRaises(McpToolError) as ctx:
                await self.catalog.list_flavors(bad)
            self.assertEqual(ctx.exception.code,'MCP_INVALID_ARGS')
        self.assertEqual(self.koocli.calls,[])

    async def test_storage_types_normalize_ha_mode_case(self):
        rows=[{'name':'ESSD','az_status':{'cn-east-3a':'normal'},'support_compute_group_type':['x86']}]
        self.koocli.push({'storage_type':rows})
        result=await self.catalog.list_storage_types('17','Single')
        self.assertEqual(self.koocli.last(),('RDS','ListStorageTypes',
                                             {'database_name':'PostgreSQL','version_name':'17','ha_mode':'single'}))
        self.assertEqual(result['data'],rows)
        self.koocli.push({'storage_type':rows})
        await self.catalog.list_storage_types('16','Ha')
        self.assertEqual(self.koocli.last()[2]['ha_mode'],'ha')
        self.assertEqual(self.koocli.last()[2]['version_name'],'16')

    async def test_storage_types_reject_bad_mode_and_missing_version(self):
        for ha_mode in ('replication','x','cluster'):
            with self.assertRaises(McpToolError) as ctx:
                await self.catalog.list_storage_types('17',ha_mode)
            self.assertEqual(ctx.exception.code,'MCP_INVALID_ARGS')
        with self.assertRaises(McpToolError) as ctx:
            await self.catalog.list_storage_types(None,'single')
        self.assertEqual(ctx.exception.code,'MCP_INVALID_ARGS')
        for bad in ('17.11.260901','x'):
            with self.assertRaises(McpToolError) as ctx:
                await self.catalog.list_storage_types(bad,'ha')
            self.assertEqual(ctx.exception.code,'MCP_INVALID_ARGS')
        self.assertEqual(self.koocli.calls,[])

    async def test_missing_or_malformed_response_lists_fail_closed(self):
        self.koocli.push({'dataStores':None})
        with self.assertRaises(McpToolError) as ctx:
            await self.catalog.list_engine_versions()
        self.assertEqual(ctx.exception.code,'MCP_SDK_ERROR')
        self.koocli.push({})
        with self.assertRaises(McpToolError) as ctx:
            await self.catalog.list_flavors()
        self.assertEqual(ctx.exception.code,'MCP_SDK_ERROR')
        self.koocli.push({'storage_type':'broken'})
        with self.assertRaises(McpToolError) as ctx:
            await self.catalog.list_storage_types('17','ha')
        self.assertEqual(ctx.exception.code,'MCP_SDK_ERROR')

    async def test_koocli_errors_pass_through_unchanged(self):
        for method,args in ((self.catalog.list_engine_versions,()),
                            (self.catalog.list_flavors,('17',)),
                            (self.catalog.list_storage_types,('17','ha'))):
            self.koocli.push(McpToolError('MCP_CLI_ERROR','boom'))
            with self.assertRaises(McpToolError) as ctx:
                await method(*args)
            self.assertEqual(ctx.exception.code,'MCP_CLI_ERROR')

    async def test_data_passes_through_safe_sanitization(self):
        rows=[{'spec_code':'rds.pg.s1.xlarge','secret_key':'leak','nested':{'password':'leak','size':100}}]
        self.koocli.push({'flavors':rows})
        result=await self.catalog.list_flavors()
        self.assertEqual(result['data'],[{'spec_code':'rds.pg.s1.xlarge','nested':{'size':100}}])

    def _push_sources(self,versions=('15','17'),flavors=None,storage=None,vpcs=None,subnets=None,groups=None):
        """Push the six probe results in the implementation's call order:
        Datastores, Flavors, StorageTypes, Vpcs, Subnets, SecurityGroups."""
        if flavors is None:
            flavors=[{'spec_code':'rds.pg.n1.medium.2','az_status':{'cn-east-3a':'normal','cn-east-3b':'sellout'}},
                     {'spec_code':'rds.pg.n1.large.2','az_status':{'cn-east-3b':'normal'}},
                     {'spec_code':'rds.pg.n1.xlarge.2','az_status':{'cn-east-3a':'sellout','cn-east-3b':'sellout'}}]
        if storage is None:
            storage=[{'name':'SSD','az_status':{'cn-east-3a':'normal'}},{'name':'ESSD','az_status':{'cn-east-3a':'normal'}}]
        if vpcs is None:vpcs=[{'id':'vpc-1','name':'net-a'}]
        if subnets is None:subnets=[{'id':'subnet-1','name':'sub-a','vpc_id':'vpc-1'}]
        if groups is None:
            groups=[{'id':'sg-1','name':'db-dedicated','tags':[{'key':'AUTO_CREATE','value':'true'},{'key':'USE_FOR','value':'Supabase'}]},
                    {'id':'sg-2','name':'shared'}]
        self.koocli.push({'dataStores':[{'id':'ds-'+v,'name':v} for v in versions]})
        self.koocli.push({'flavors':flavors})
        self.koocli.push({'storage_type':storage})
        self.koocli.push(vpcs if isinstance(vpcs,Exception) else {'vpcs':vpcs})
        self.koocli.push(subnets if isinstance(subnets,Exception) else {'subnets':subnets})
        self.koocli.push(groups if isinstance(groups,Exception) else {'security_groups':groups})

    async def test_discover_link_options_single_happy_path(self):
        self._push_sources()
        result=await self.catalog.discover_link_create_options('Single')
        self.assertEqual([c[1] for c in self.koocli.calls],
                         ['ListDatastores','ListFlavors','ListStorageTypes','ListVpcs/v3','ListSubnets','ListSecurityGroups/v3'])
        self.assertEqual(self.koocli.calls[2],('RDS','ListStorageTypes',
                                               {'database_name':'PostgreSQL','version_name':'17','ha_mode':'single'}))
        self.assertEqual(self.koocli.calls[3],('VPC','ListVpcs/v3',{'limit':100}))
        self.assertEqual(self.koocli.calls[4],('VPC','ListSubnets',{'limit':100}))
        self.assertEqual(self.koocli.calls[5],('VPC','ListSecurityGroups/v3',{'limit':100}))
        self.assertEqual(result['mode'],'Single')
        options=result['managed_instance_field_options']
        self.assertEqual(options['datastore.type'],{'fixed':'PostgreSQL'})
        self.assertEqual(options['datastore.version']['values'],['15','17'])
        self.assertEqual(options['datastore.version']['recommended'],'17')
        self.assertEqual(options['flavor_ref']['values'],['rds.pg.n1.medium.2','rds.pg.n1.large.2'])
        self.assertEqual(options['flavor_ref']['recommended'],'rds.pg.n1.medium.2')
        self.assertEqual(options['volume.type']['values'],['SSD','ESSD'])
        self.assertEqual(options['volume.type']['recommended'],'ESSD')
        self.assertEqual(options['volume.size'],{'minimum':40,'maximum':40000,'recommended':40,'note':'GB'})
        self.assertEqual(options['charge_info']['values'],
                         [{'charge_mode':'postPaid'},
                          {'charge_mode':'prePaid','period_type':'month','period_num':1},
                          {'charge_mode':'prePaid','period_type':'year','period_num':1}])
        self.assertEqual(options['charge_info']['recommended'],{'charge_mode':'postPaid'})
        self.assertEqual(options['ha.mode'],{'fixed':'Single'})
        self.assertEqual(options['ha.replication_mode'],{'values':['async','sync'],'recommended':'async'})
        self.assertEqual(options['availability_zone']['values'],['cn-east-3a','cn-east-3b'])
        self.assertEqual(options['port'],{'recommended':5432,'note':'默认端口，可省略'})
        self.assertEqual(options['enterprise_project_id'],{'recommended':'0','note':'默认项目；多企业项目时让用户确认'})
        self.assertEqual(options['password'],{'note':'8-32 位三类字符，用户经本地请求文件提供，工具不生成'})
        self.assertEqual(options['configuration_id'],{'note':'参数模板，可选，默认不传'})
        self.assertEqual(options['security_group_id']['values'],
                         [{'id':'sg-1','name':'db-dedicated','flow_created':True},{'id':'sg-2','name':'shared','flow_created':False}])
        self.assertIsNone(options['security_group_id']['recommended'])
        self.assertEqual(result['network']['vpcs'],[{'id':'vpc-1','name':'net-a'}])
        self.assertEqual(result['network']['subnets'],[{'id':'subnet-1','name':'sub-a','vpc_id':'vpc-1'}])
        self.assertEqual(set(result['discovery_status']),{'engine_versions','flavors','storage_types','vpcs','subnets','security_groups'})
        self.assertTrue(all(value=='ok' for value in result['discovery_status'].values()))
        self.assertEqual(result['top_level_reminder'],
                         ['availability_zone 必须与顶层一致（服务端强制校验）',
                          '数据库密码与应用密码同规则，可同值',
                          '本工具只服务新建实例场景；托管已有实例用 list_supabase_manageable_instances'])

    async def test_discover_link_options_ha_mode_shapes_storage_query(self):
        self._push_sources()
        result=await self.catalog.discover_link_create_options('Ha')
        self.assertEqual(self.koocli.calls[2][2],{'database_name':'PostgreSQL','version_name':'17','ha_mode':'ha'})
        self.assertEqual(result['mode'],'Ha')
        options=result['managed_instance_field_options']
        self.assertEqual(options['ha.mode'],{'fixed':'Ha'})
        self.assertIn('两个不同 AZ',options['availability_zone']['note'])
        self.assertTrue(all(value=='ok' for value in result['discovery_status'].values()))

    async def test_discover_link_options_survives_total_sellout(self):
        self._push_sources(flavors=[{'spec_code':'rds.pg.n1.medium.2','az_status':{'cn-east-3a':'sellout'}}])
        result=await self.catalog.discover_link_create_options('Single')
        options=result['managed_instance_field_options']
        self.assertEqual(options['flavor_ref']['values'],[])
        self.assertIsNone(options['flavor_ref']['recommended'])
        self.assertEqual(options['availability_zone']['values'],[])
        self.assertTrue(all(value=='ok' for value in result['discovery_status'].values()))

    async def test_discover_link_options_isolates_vpc_failure(self):
        self._push_sources(vpcs=McpToolError('MCP_CLI_ERROR','vpc inventory unavailable'))
        result=await self.catalog.discover_link_create_options('Single')
        self.assertEqual(result['discovery_status']['vpcs'],'error: vpc inventory unavailable')
        self.assertEqual(result['network']['vpcs'],[])
        self.assertEqual(result['discovery_status']['subnets'],'ok')
        self.assertEqual(result['discovery_status']['security_groups'],'ok')
        self.assertIn('vpcs 查询失败',result['network']['note'])
        self.assertEqual(result['managed_instance_field_options']['flavor_ref']['recommended'],'rds.pg.n1.medium.2')
        self.assertEqual(result['network']['subnets'],[{'id':'subnet-1','name':'sub-a','vpc_id':'vpc-1'}])

    async def test_discover_link_options_rejects_invalid_mode_before_any_call(self):
        for bad in ('single','ha','',None,'Cluster'):
            with self.assertRaises(McpToolError) as ctx:
                await self.catalog.discover_link_create_options(bad)
            self.assertEqual(ctx.exception.code,'MCP_INVALID_ARGS')
        self.assertEqual(self.koocli.calls,[])

    async def test_discover_link_options_sorts_shuffled_versions_and_uses_max(self):
        self._push_sources(versions=('15','18','13'))
        result=await self.catalog.discover_link_create_options('Single')
        options=result['managed_instance_field_options']
        self.assertEqual(options['datastore.version']['values'],['13','15','18'])
        self.assertEqual(options['datastore.version']['recommended'],'18')
        self.assertEqual(self.koocli.calls[2][2]['version_name'],'18')

    def test_catalog_tools_register_under_new_names(self):
        from mcp_server_supabase.tools import operations

        class RecordingServer:
            def __init__(self):self.names=[]
            def tool(self):
                def decorate(func):
                    self.names.append(func.__name__)
                    return func
                return decorate

        server=RecordingServer()
        operations.register(server)
        for name in ('list_db_instance_engine_versions','list_db_instance_flavors_with_azs',
                     'list_db_instance_storage_types','discover_db_instance_create_options'):
            self.assertIn(name,server.names)
        for old in ('list_supabase_engine_versions','list_supabase_instance_flavors',
                    'list_supabase_instance_storage_types'):
            self.assertNotIn(old,server.names)


if __name__=='__main__':
    unittest.main()

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


if __name__=='__main__':
    unittest.main()

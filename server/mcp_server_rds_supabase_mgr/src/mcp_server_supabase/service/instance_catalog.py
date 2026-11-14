"""RDS PostgreSQL catalog reads (engine versions, flavors, storage types) via KooCLI for the create-with-new-instance scenario."""
import re
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.client.koocli import KoocliClient
from mcp_server_supabase.service.operations import safe

NOTE=('Catalog for the create-with-new-instance scenario: pick the PostgreSQL engine version, flavor and storage type '
      'before creating the managed instance. Only AZs whose az_status is normal are purchasable; each flavor and '
      'storage row carries its own AZ sale status.')


class InstanceCatalog:
    """Read-only RDS engine-level catalogs; the Supabase origin does not serve them, so they run through KooCLI."""

    def __init__(self,koocli=None):
        self.koocli=koocli or KoocliClient()

    async def list_engine_versions(self):
        data=await self.koocli.call('RDS','ListDatastores',{'database_name':'PostgreSQL'})
        return {'data':safe(self._rows(data,'dataStores')),'note':NOTE}

    async def list_flavors(self,version_name=None):
        params={'database_name':'PostgreSQL'}
        if version_name is not None:
            self._require_major(version_name)
            params['version_name']=version_name
        data=await self.koocli.call('RDS','ListFlavors',params)
        return {'data':safe(self._rows(data,'flavors')),'note':NOTE}

    async def list_storage_types(self,version_name,ha_mode):
        self._require_major(version_name)
        mode=str(ha_mode).lower()
        if mode not in ('single','ha'):
            raise McpToolError('MCP_INVALID_ARGS','ha_mode must be single or ha')
        data=await self.koocli.call('RDS','ListStorageTypes',
                                    {'database_name':'PostgreSQL','version_name':version_name,'ha_mode':mode})
        return {'data':safe(self._rows(data,'storage_type')),'note':NOTE}

    def _require_major(self,version_name):
        if not isinstance(version_name,str) or not re.fullmatch(r'\d{1,2}',version_name):
            raise McpToolError('MCP_INVALID_ARGS','version_name must be a major version like 17',
                               hint='Complete version numbers are not accepted here: take the major version first '
                                    '(list_supabase_engine_versions), then filter ListFlavors with it.')
        return version_name

    def _rows(self,data,key):
        rows=data.get(key) if isinstance(data,dict) else None
        if not isinstance(rows,list):
            raise McpToolError('MCP_SDK_ERROR','Catalog response is missing the '+key+' list',
                               hint='Verify the RDS response contract with `hcloud RDS <Operation> --help` before continuing.')
        return rows

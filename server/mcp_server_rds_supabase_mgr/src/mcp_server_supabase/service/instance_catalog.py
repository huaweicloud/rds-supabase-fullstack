"""RDS PostgreSQL catalog reads (engine versions, flavors, storage types) via KooCLI for the create-with-new-instance scenario, plus a one-call dependency discovery that pre-fills the managed_instance request body."""
import asyncio
import re
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.client.koocli import KoocliClient
from mcp_server_supabase.service.operations import safe

NOTE=('Catalog for the create-with-new-instance scenario: pick the PostgreSQL engine version, flavor and storage type '
      'before creating the managed instance. Only AZs whose az_status is normal are purchasable; each flavor and '
      'storage row carries its own AZ sale status.')

STORAGE_SKIPPED='skipped - engine version unavailable'


def _error_text(error):
    message=getattr(error,'message',None) or str(error) or error.__class__.__name__
    return ' '.join(str(message).split())[:60]


def _failure(error):
    return '（查询失败：'+error+'）'


def _flow_created(group):
    """Same tag contract as the security-group flow: AUTO_CREATE=true + USE_FOR=Supabase."""
    tags=group.get('tags') if isinstance(group,dict) else None
    pairs={}
    if isinstance(tags,dict):
        pairs={str(k):str(v) for k,v in tags.items()}
    elif isinstance(tags,list):
        for item in tags:
            if isinstance(item,dict) and 'key' in item:
                pairs[str(item['key'])]=str(item.get('value'))
    return pairs.get('AUTO_CREATE')=='true' and pairs.get('USE_FOR')=='Supabase'


async def _skipped_probe():
    """Placeholder for probes that cannot run (no engine version to query)."""
    return None


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

    async def discover_link_create_options(self,mode):
        """One-call dependency discovery for manage_type=newly_instance: engine versions,
        instance flavors with per-AZ sale status, mode-filtered storage types and the
        VPC/subnet/security-group inventory, assembled into a recommended value for
        every managed_instance request-body field. Each source fails independently."""
        if mode not in ('Single','Ha'):
            raise McpToolError('MCP_INVALID_ARGS','mode must be Single or Ha')
        storage_mode='ha' if mode=='Ha' else 'single'
        # Engine versions run first: the storage probe depends on the highest major version.
        version_names=[]
        version_error=''
        try:
            versions=await self.list_engine_versions()
            version_names=[row.get('name') for row in versions['data']
                           if isinstance(row,dict) and row.get('name')]
        except Exception as error:
            version_error=_error_text(error)
        candidates=[]
        for name in version_names:
            try:candidates.append((int(name),str(name)))
            except (ValueError,TypeError):continue
        ordered=[];seen=set()
        for number,name in sorted(candidates):
            if number not in seen:
                seen.add(number);ordered.append(name)
        highest=ordered[-1] if ordered else None
        # The remaining sources run concurrently; a single failure degrades only its own section.
        flavors_result,storage_result,vpcs_result,subnets_result,groups_result=await asyncio.gather(
            self.list_flavors(),
            self.list_storage_types(highest,storage_mode) if highest is not None else _skipped_probe(),
            self.koocli.call('VPC','ListVpcs/v3',{'limit':100}),
            self.koocli.call('VPC','ListSubnets',{'limit':100}),
            self.koocli.call('VPC','ListSecurityGroups/v3',{'limit':100}),
            return_exceptions=True)
        flavor_rows,flavor_error=self._rows_of(flavors_result,'data')
        if storage_result is None:
            storage_rows,storage_error=[],STORAGE_SKIPPED
        else:
            storage_rows,storage_error=self._rows_of(storage_result,'data')
        vpc_rows,vpc_error=self._rows_of(vpcs_result,'vpcs')
        subnet_rows,subnet_error=self._rows_of(subnets_result,'subnets')
        group_rows,group_error=self._rows_of(groups_result,'security_groups')
        saleable=[]
        normal_azs=set()
        for row in flavor_rows:
            az_status=row.get('az_status') if isinstance(row,dict) else None
            if not isinstance(az_status,dict):continue
            normal=[az for az,status in az_status.items() if status=='normal']
            normal_azs.update(normal)
            if normal and row.get('spec_code'):saleable.append(row['spec_code'])
        volume_names=[row['name'] for row in storage_rows if isinstance(row,dict) and row.get('name')]
        volume_recommended=next((name for name in volume_names if 'ESSD' in name),
                                volume_names[0] if volume_names else None)
        group_values=[{'id':row['id'],'name':row.get('name'),'flow_created':_flow_created(row)}
                      for row in group_rows if isinstance(row,dict) and row.get('id')]
        def option_note(base,error):
            return base+_failure(error) if error else base
        options={
            'datastore.type':{'fixed':'PostgreSQL'},
            'datastore.version':{'values':ordered,'recommended':highest,
                                 'note':option_note('PostgreSQL 引擎大版本',version_error)},
            'flavor_ref':{'values':saleable[:20],'recommended':saleable[0] if saleable else None,
                          'note':option_note('实例规格，形如 rds.pg.n1.medium.2；与应用规格（rds.supabase.*）是两回事',flavor_error)},
            'volume.type':{'values':volume_names,'recommended':volume_recommended,
                           'note':option_note('按 mode 过滤后的可售盘型',storage_error)},
            'volume.size':{'minimum':40,'maximum':40000,'recommended':40,'note':'GB'},
            'charge_info':{'values':[{'charge_mode':'postPaid'},
                                     {'charge_mode':'prePaid','period_type':'month','period_num':1},
                                     {'charge_mode':'prePaid','period_type':'year','period_num':1}],
                           'recommended':{'charge_mode':'postPaid'},
                           'note':'period_type 是字符串 month/year（不是数字）；包周期返回订单走订单工具支付'},
            'ha.mode':{'fixed':mode},
            'ha.replication_mode':{'values':['async','sync'],'recommended':'async'},
            'availability_zone':{'values':sorted(normal_azs),'note':'Ha 模式需两个不同 AZ（主+备）'},
            'port':{'recommended':5432,'note':'默认端口，可省略'},
            'enterprise_project_id':{'recommended':'0','note':'默认项目；多企业项目时让用户确认'},
            'password':{'note':'8-32 位三类字符，用户经本地请求文件提供，工具不生成'},
            'security_group_id':{'values':group_values,'recommended':None,
                                 'note':option_note('推荐新建专用数据库组（create_supabase_security_group，描述用 数据库接入（自动创建）），别复用共享组',group_error)},
            'configuration_id':{'note':'参数模板，可选，默认不传'},
        }
        network_note='子网需与所选 VPC 匹配且 IP 充足；在创建请求 basic_config 里给出 vpc_id/subnet_id'
        if vpc_error:network_note+='（vpcs 查询失败：'+vpc_error+'）'
        if subnet_error:network_note+='（subnets 查询失败：'+subnet_error+'）'
        status=lambda error:'error: '+error if error else 'ok'
        return {'mode':mode,
                'managed_instance_field_options':options,
                'network':{'vpcs':safe(vpc_rows),'subnets':safe(subnet_rows),'note':network_note},
                'top_level_reminder':['availability_zone 必须与顶层一致（服务端强制校验）',
                                      '数据库密码与应用密码同规则，可同值',
                                      '本工具只服务新建实例场景；托管已有实例用 list_supabase_manageable_instances'],
                'discovery_status':{'engine_versions':status(version_error),
                                    'flavors':status(flavor_error),
                                    'storage_types':status(storage_error),
                                    'vpcs':status(vpc_error),
                                    'subnets':status(subnet_error),
                                    'security_groups':status(group_error)}}

    def _rows_of(self,result,key):
        """Tolerant extraction for gathered probes: exceptions report, missing response keys stay empty."""
        if isinstance(result,BaseException):
            return [],_error_text(result)
        rows=result.get(key) if isinstance(result,dict) else None
        return (rows if isinstance(rows,list) else []),''

    def _require_major(self,version_name):
        if not isinstance(version_name,str) or not re.fullmatch(r'\d{1,2}',version_name):
            raise McpToolError('MCP_INVALID_ARGS','version_name must be a major version like 17',
                               hint='Complete version numbers are not accepted here: take the major version first '
                                     '(list_db_instance_engine_versions), then filter ListFlavors with it.')
        return version_name

    def _rows(self,data,key):
        rows=data.get(key) if isinstance(data,dict) else None
        if not isinstance(rows,list):
            raise McpToolError('MCP_SDK_ERROR','Catalog response is missing the '+key+' list',
                               hint='Verify the RDS response contract with `hcloud RDS <Operation> --help` before continuing.')
        return rows

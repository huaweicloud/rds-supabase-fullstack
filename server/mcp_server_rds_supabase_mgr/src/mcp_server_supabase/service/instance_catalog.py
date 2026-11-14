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
        # Network (VPC/subnet) belongs to discover_available_network_for_create; security groups
        # are intentionally NOT discovered or recommended here - before the network exists no
        # ingress source can be set meaningfully, and the creation flow provisions a dedicated
        # group (create_supabase_security_group) after the network is in place.
        flavors_result,storage_result=await asyncio.gather(
            self.list_flavors(),
            self.list_storage_types(highest,storage_mode) if highest is not None else _skipped_probe(),
            return_exceptions=True)
        flavor_rows,flavor_error=self._rows_of(flavors_result,'data')
        if storage_result is None:
            storage_rows,storage_error=[],STORAGE_SKIPPED
        else:
            storage_rows,storage_error=self._rows_of(storage_result,'data')
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
            'security_group_id':{'values':[],'recommended':None,
                                 'note':'网络配置（VPC/子网）就位后再新建专用数据库组（create_supabase_security_group，描述用 数据库接入（自动创建）），'
                                        '随后按入方向来源网段配置 5432 规则——网络未定时无法有效设置入方向，本工具不推荐既有组，也别复用共享组'},
            'configuration_id':{'note':'参数模板，可选，默认不传'},
        }
        status=lambda error:'error: '+error if error else 'ok'
        return {'mode':mode,
                'managed_instance_field_options':options,
                'top_level_reminder':['availability_zone 必须与顶层一致（服务端强制校验）',
                                      '数据库密码与应用密码同规则，可同值',
                                      '本工具只服务新建实例场景；托管已有实例用 list_supabase_manageable_instances',
                                      '网络与安全组不在本工具范围：先用 discover_available_network_for_create 选定 VPC/子网，再新建专用数据库组并配 5432 入方向规则'],
                'discovery_status':{'engine_versions':status(version_error),
                                    'flavors':status(flavor_error),
                                    'storage_types':status(storage_error)}}

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


class NetworkDiscovery:
    """Auto-discover a VPC and subnet with sufficient free IPs for the create-with-new-instance scenario.

    The Supabase creation request carries vpc_id/subnet_id in basic_config; this picker
    walks the VPC inventory and each VPC's subnets through KooCLI, preferring subnets
    with at least two free IPv4 addresses (the managed instance reserves more than one),
    falling back to at least one, and stops at the first match.
    """

    def __init__(self,koocli=None):
        self.koocli=koocli or KoocliClient()

    async def discover(self,minimum_ips=2,fallback_minimum=1,availability_zone=None):
        if type(minimum_ips) is not int or not 1<=minimum_ips<=254 or type(fallback_minimum) is not int or not 1<=fallback_minimum<=minimum_ips:
            raise McpToolError('MCP_INVALID_ARGS','minimum_ips must be an integer 1-254 and fallback_minimum must not exceed it')
        vpcs_data=await self.koocli.call('VPC','ListVpcs/v3',{'limit':100})
        vpcs=vpcs_data.get('vpcs') if isinstance(vpcs_data,dict) else None
        if not isinstance(vpcs,list):
            raise McpToolError('MCP_SDK_ERROR','VPC inventory unreadable')
        inspected=[]
        for vpc in vpcs:
            if not isinstance(vpc,dict) or not vpc.get('id'):continue
            vpc_id=vpc['id']
            try:
                sub_data=await self.koocli.call('VPC','ListSubnets',{'limit':100,'vpc_id':vpc_id})
            except McpToolError as error:
                inspected.append({'vpc_id':vpc_id,'vpc_name':vpc.get('name'),'error':error.message})
                continue
            subnets=sub_data.get('subnets') if isinstance(sub_data,dict) else None
            candidates=[]
            fallback=None
            for subnet in subnets if isinstance(subnets,list) else []:
                if not isinstance(subnet,dict) or not subnet.get('id'):continue
                if subnet.get('status') not in (None,'ACTIVE'):continue
                free=subnet.get('available_ip_address_count')
                free=free if type(free) is int else None
                entry={'vpc_id':vpc_id,'vpc_name':vpc.get('name'),'vpc_cidr':vpc.get('cidr'),
                       'subnet_id':subnet['id'],'subnet_name':subnet.get('name'),
                       'subnet_cidr':subnet.get('cidr'),'availability_zone':subnet.get('availability_zone'),
                       'available_ip_count':free}
                if free is not None and free>=minimum_ips:
                    candidates.append(entry)
                elif free is not None and free>=fallback_minimum and fallback is None:
                    fallback=entry
                elif free is None:
                    # Availability unknown: treat as fallback candidate only when nothing better is known.
                    if fallback is None:fallback={**entry,'available_ip_count':None}
            if candidates:
                return self._result(candidates[0],minimum_ips,fallback_minimum,inspected,preference='sufficient')
            if fallback is not None:
                return self._result(fallback,minimum_ips,fallback_minimum,inspected,preference='fallback')
            inspected.append({'vpc_id':vpc_id,'vpc_name':vpc.get('name'),'error':'no eligible subnet'})
        # Nothing exists to reuse: recommend the standard defaults instead of failing.
        # Huawei Cloud's default private range 192.168.0.0/16 is valid across all regions;
        # the default subnet 192.168.0.0/24 should be placed in the target availability zone
        # (the AZ the managed RDS instance will live in).
        return self._default_recommendation(availability_zone,minimum_ips,fallback_minimum,inspected)

    def _default_recommendation(self,availability_zone,minimum_ips,fallback_minimum,inspected):
        create={'vpc':{'name':'default_vpc','cidr':'192.168.0.0/16'},
                'subnet':{'name':'default_subnet','cidr':'192.168.0.0/24',
                          'availability_zone':availability_zone,
                          'gateway_ip':'192.168.0.1'}}
        return {'preference':'default_recommendation',
                'vpc_id':None,'vpc_name':'default_vpc','vpc_cidr':'192.168.0.0/16',
                'subnet_id':None,'subnet_name':'default_subnet','subnet_cidr':'192.168.0.0/24',
                'availability_zone':availability_zone,
                'available_ip_count':None,
                'ip_requirement':{'preferred':minimum_ips,'fallback':fallback_minimum},
                'default_create':create,
                'basic_config_usage':None,
                'note':'No existing VPC/subnet is usable in this region. The recommended default is VPC default_vpc '
                       '(192.168.0.0/16, the standard private range valid in all Huawei Cloud regions) with subnet '
                       'default_subnet (192.168.0.0/24) placed in the target availability zone. Create them first '
                       '(console or KooCLI: CreateVpc then CreateSubnet with the gateway 192.168.0.1), then re-run '
                       'discovery - basic_config requires the created vpc_id and subnet_id.',
                'inspected_vpcs':inspected}

    def _result(self,entry,minimum_ips,fallback_minimum,inspected,preference):
        return {**entry,
                'preference':preference,
                'ip_requirement':{'preferred':minimum_ips,'fallback':fallback_minimum},
                'basic_config_usage':{'vpc_id':entry['vpc_id'],'subnet_id':entry['subnet_id']},
                'note':'Fill these values into the Supabase creation request basic_config (vpc_id, subnet_id). '
                       'available_ip_count comes from the VPC service; a fallback pick means fewer free IPs than preferred - verify capacity before creating.',
                'inspected_vpcs':inspected}


class BasicOptionsDiscovery:
    """One-call discovery of the Supabase application's own creation basics.

    Covers the top-level application fields only - name/version/mode/flavor/
    availability_zone plus the deployment-mode probe. Network (basic_config
    vpc/subnet) is owned by NetworkDiscovery; the managed PG instance fields
    are owned by InstanceCatalog.discover_link_create_options.
    """

    def __init__(self,operations=None):
        self.operations=operations

    def _ops(self):
        if self.operations is None:
            from mcp_server_supabase.service.operations import Operations
            self.operations=Operations()
        return self.operations

    async def discover(self,az_code):
        az_code=az_code if isinstance(az_code,str) and re.fullmatch(r'[a-z]{2,}-[a-z]+-\d+[a-z]',az_code or '') else None
        if not az_code:
            raise McpToolError('MCP_INVALID_ARGS','az_code must be an availability-zone code like cn-east-3a (query it via list_supabase_flavors_with_azs)')
        probes={}
        flavors_single=flavors_ha=None
        try:
            result=await self._ops().creation_candidates('flavors',az_code=az_code,mode='Single')
            flavors_single=result.get('data') if isinstance(result,dict) else None
            flavors_single=flavors_single.get('flavors') if isinstance(flavors_single,dict) else flavors_single
            if not isinstance(flavors_single,list):flavors_single=[]
            probes['application_flavors_single']='ok'
        except McpToolError as error:
            probes['application_flavors_single']='error: '+_error_text(error)
        try:
            result=await self._ops().creation_candidates('flavors',az_code=az_code,mode='Ha')
            flavors_ha=result.get('data') if isinstance(result,dict) else None
            flavors_ha=flavors_ha.get('flavors') if isinstance(flavors_ha,dict) else flavors_ha
            if not isinstance(flavors_ha,list):flavors_ha=[]
            probes['application_flavors_ha']='ok'
        except McpToolError as error:
            probes['application_flavors_ha']='error: '+_error_text(error)
            flavors_ha=None  # a 400 rejection is the documented signal that Ha is unsupported here
        ha_supported=isinstance(flavors_ha,list) and bool(flavors_ha)
        rows=flavors_single if isinstance(flavors_single,list) else []
        versions=sorted({str(row.get('version')) for row in rows if isinstance(row,dict) and row.get('version')})
        # Application flavors carry per-AZ sale status; keep only specs saleable in the requested AZ.
        def saleable(row):
            return any(isinstance(az,dict) and az.get('code')==az_code and az.get('status')=='normal'
                       for az in row.get('availability_zones') or [])
        specs=[row for row in rows if isinstance(row,dict) and row.get('spec_code')]
        saleable_specs=[row for row in specs if saleable(row)]
        preferred=saleable_specs or specs
        options={
            'name':{'note':'应用名称，4-64 字符；由用户起名，工具不生成'},
            'version':{'values':versions,'recommended':versions[-1] if versions else None,
                       'note':'Supabase 应用版本（x.y.z，非 PG 引擎版本）；取可用最高版'},
            'mode':{'values':['Single','Ha'] if ha_supported else ['Single'],
                    'recommended':'Single',
                    'note':'Single 单机 / Ha 主备；Ha 是否可用按局点实时探测（本次探测：%s）'%('支持' if ha_supported else '不支持')},
            'flavor_ref':{'values':[row['spec_code'] for row in preferred[:20]],
                          'recommended':preferred[0]['spec_code'] if preferred else None,
                          'note':'应用规格（rds.supabase.*，与托管实例规格 rds.pg.* 是两回事）；仅列在所选 AZ 可售的规格，默认勾选 2U4G 档'},
            'availability_zone':{'values':[az_code],
                                 'note':'本次查询的 AZ；Ha 模式需两个不同 AZ（主+备），用 list_supabase_flavors_with_azs 查全部可售 AZ'},
            'password':{'note':'8-32 位三类字符；用户经本地请求文件提供，工具不生成'},
            'storage_component':{'values':[{'enabled':False},{'enabled':True}],
                                 'recommended':{'enabled':False},
                                 'note':'OBS 存储对接：有图片/视频/大文件需求才启用；启用需桶名与 AK/SK（经本地请求文件）'},
        }
        return {'az_code':az_code,
                'basic_options':options,
                'ha_supported':ha_supported,
                'excluded_scopes':['network (basic_config vpc/subnet) -> discover_available_network_for_create',
                                   'managed instance fields -> discover_db_instance_create_options'],
                'probe_status':probes,
                'note':'Top-level application basics for create_supabase_application. '
                       'Flavor sale status is per-AZ from the Supabase flavor API; the Ha probe uses the same API - '
                       'a rejection means this environment supports Single only.'}

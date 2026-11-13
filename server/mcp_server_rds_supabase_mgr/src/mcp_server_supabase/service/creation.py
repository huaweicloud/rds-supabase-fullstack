"""Single-mode creation subset from supplied SDK contract; cloud policy stays authoritative."""
import ipaddress
import re
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.client.rest import segment
from mcp_server_supabase.service.request_refs import fields,text,validate_request
from mcp_server_supabase.service.network import identifier

_PASSWORD_CLASSES=(re.compile(r'[A-Z]'),re.compile(r'[a-z]'),re.compile(r'\d'),re.compile(r'[~!@#$%^*\-_=+,?]'))
_PASSWORD_RULE='8-32 characters with at least three of: uppercase, lowercase, digits, special characters (~!@#$%^*-_+=?,)'


def password_rule(value,label):
    if not isinstance(value,str) or not 8<=len(value)<=32 or sum(bool(p.search(value)) for p in _PASSWORD_CLASSES)<3:
        raise ValueError(f'{label} must be {_PASSWORD_RULE}')


def validate_creation(body):
    try:
        required=('name','basic_config','version','mode','flavor_ref','availability_zone','password','storage_component','manage_type')
        fields(body,required+('managed_instance','existing_instance','data_vip','security_group_id'),required)
        if not isinstance(body['name'],str) or not 4<=len(body['name'])<=64 or any(ord(c)<32 for c in body['name']):raise ValueError('name must be 4-64 characters')
        if body['mode']!='Single':raise ValueError('mode must be Single (HA deployment is not supported)')
        if not isinstance(body['version'],str) or not re.fullmatch(r'[1-9]\d*\.(0|[1-9]\d*)\.(0|[1-9]\d*)',body['version']):raise ValueError('version must be X.Y.Z - the application version, currently "1.0.0", not the PG engine version')
        if not isinstance(body['flavor_ref'],str) or not re.fullmatch(r'rds\.supabase(\.[a-z0-9]+){3,4}',body['flavor_ref']):raise ValueError('flavor_ref must be an application flavor like rds.supabase.n1.large.2')
        az=segment(body['availability_zone']);password_rule(body['password'],'password')
        basic=body['basic_config'];fields(basic,('region','vpc_id','subnet_id','time_zone'),('region','vpc_id','subnet_id'))
        for key in ('region','vpc_id','subnet_id'):segment(basic[key])
        if 'time_zone' in basic:text(basic['time_zone'],64)
        if 'data_vip' in body:ipaddress.IPv4Address(body['data_vip'])
        if 'security_group_id' in body:identifier(body['security_group_id'])
        validate_request('storage',body['storage_component'])
        if body['storage_component']['enabled'] and not body['storage_component'].get('sk'):raise ValueError('storage_component requires the full AK/SK on the creation path (SK omission is only available via update)')
        if body['manage_type']=='existed_instance':
            if body.get('managed_instance') is not None:raise ValueError('manage_type existed_instance must not carry managed_instance')
            existing=body['existing_instance'];fields(existing,('instance_id','database_name','database_pwd'),('instance_id','database_name','database_pwd'))
            segment(existing['instance_id']);text(existing['database_name']);text(existing['database_pwd'])
        elif body['manage_type']=='newly_instance':
            if body.get('existing_instance') is not None:raise ValueError('manage_type newly_instance must not carry existing_instance')
            managed=body['managed_instance']
            required_pg=('datastore','charge_info','flavor_ref','volume','availability_zone','security_group_id','password','enterprise_project_id')
            fields(managed,required_pg+('ha','configuration_id','port','data_vip','tags'),required_pg)
            fields(managed['datastore'],('type','version'),('type','version'))
            if managed['datastore']['type']!='PostgreSQL':raise ValueError('managed_instance.datastore.type must be PostgreSQL')
            text(managed['datastore']['version'],64)
            if 'ha' in managed:
                ha=managed['ha'];fields(ha,('mode','replication_mode'),('mode','replication_mode'))
                if ha['mode']!='Single':raise ValueError('ha.mode must be Single (HA deployment is not supported)')
                if ha['replication_mode'] not in ('async','sync'):raise ValueError("ha.replication_mode must be 'async' or 'sync'")
            fields(managed['charge_info'],('charge_mode',),('charge_mode',))
            if managed['charge_info']['charge_mode']!='postPaid':raise ValueError('charge_info.charge_mode must be postPaid (prepaid is not supported)')
            fields(managed['volume'],('type','size'),('type','size'))
            text(managed['volume']['type'],32)
            if type(managed['volume']['size']) is not int or managed['volume']['size']<=0:raise ValueError('volume.size must be a positive integer (GB)')
            if managed['availability_zone']!=az:raise ValueError('managed_instance.availability_zone must equal the top-level availability_zone')
            text(managed['flavor_ref'],128);password_rule(managed['password'],'managed_instance.password')
            segment(managed['enterprise_project_id']);identifier(managed['security_group_id'])
            if 'configuration_id' in managed:segment(managed['configuration_id'])
            if 'port' in managed and (type(managed['port']) is not int or not 2100<=managed['port']<=9500):raise ValueError('port must be an integer in 2100-9500 (use 5432 or omit it for the default)')
            if 'data_vip' in managed:ipaddress.IPv4Address(managed['data_vip'])
            # Tag limits/field policies were referenced but not supplied: do not silently forward.
            if 'tags' in managed:raise ValueError('tags are not supported')
        else:raise ValueError('manage_type must be newly_instance or existed_instance')
        return body
    except McpToolError:
        raise
    except (ValueError,TypeError,KeyError) as e:
        raise McpToolError('MCP_INVALID_ARGS',f'Invalid creation request: {str(e) or e.__class__.__name__}',
                          hint='Fix the flagged field and preview again. Backend password, version, capacity and sale policies remain authoritative.') from None

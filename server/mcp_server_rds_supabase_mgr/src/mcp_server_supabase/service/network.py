"""Native VPC v3 security-group operations via KooCLI; ledger and response contracts unchanged."""
import ipaddress
import os
import re
import uuid
from huaweicloud_mcp_core.errors import McpToolError
from huaweicloud_mcp_core.guardrails import assert_not_protected
from mcp_server_supabase.client.koocli import KoocliClient
from mcp_server_supabase.failures import RecoveryError
from mcp_server_supabase.service.operations import safe
from mcp_server_supabase.service.plans import PlanStore, fingerprint

ROOT='/v3/{project}/vpc/'
DIRECTIONS=('ingress','egress')
PROTOCOLS=('tcp','udp')


def identifier(value):
    try:
        if not isinstance(value,str) or str(uuid.UUID(value))!=value:raise ValueError()
    except (ValueError,AttributeError):
        raise McpToolError('MCP_INVALID_ARGS','A canonical VPC resource UUID is required') from None
    return value


class Network:
    """Security-group requests run through KooCLI (hcloud); the RDS origin does not serve the VPC API."""

    def __init__(self,koocli=None,plans=None):
        self.koocli=koocli or KoocliClient()
        self.plans=plans or PlanStore()

    def intent_digest(self,method,path,body):
        return fingerprint({'endpoint':'hcloud:'+self.koocli.region,'credential':self.koocli.token,
                            'method':method,'path':path,'body':body})

    async def list_groups(self,limit=10,marker=None):
        if type(limit) is not int or not 1<=limit<=100:
            raise McpToolError('MCP_INVALID_ARGS','Use limit 1-100')
        params={'limit':limit}
        if marker is not None:params['marker']=identifier(marker)
        data=await self.koocli.call('VPC','ListSecurityGroups/v3',params)
        return {'data':safe(data),'note':'One bounded page; follow the service pagination marker.'}

    async def show_group(self,group_id):
        group=await self._read_group(group_id)
        return {'data':safe(group)}

    async def create_group(self,name,description=None,confirm=False,plan_id=None):
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',name):
            raise McpToolError('MCP_INVALID_ARGS','Use a 1-64 character ASCII group name with letters, digits, underscore, dot or hyphen')
        if description is not None:
            if not isinstance(description,str) or len(description)>255 or '<' in description or '>' in description:
                raise McpToolError('MCP_INVALID_ARGS','Use a description of at most 255 characters without angle brackets')
        body={'security_group':{'name':name}}
        if description is not None:body['security_group']['description']=description
        return await self._change('POST','security-groups','CreateSecurityGroup/v3',body,body,confirm,plan_id,'security_group')

    async def add_rule(self,group_id,source_cidr,port=8443,direction='ingress',protocol='tcp',confirm=False,plan_id=None):
        if direction not in DIRECTIONS or protocol not in PROTOCOLS:
            raise McpToolError('MCP_INVALID_ARGS','direction must be ingress or egress; protocol must be tcp or udp')
        identifier(group_id)
        try:
            source=ipaddress.ip_network(source_cidr,strict=True)
            if source.prefixlen==0 or type(port) is not int or not 1<=port<=65535:raise ValueError()
        except (ValueError,TypeError):
            raise McpToolError('MCP_INVALID_ARGS','Specify a bounded canonical CIDR and port 1-65535; world-wide rules are unsupported') from None
        rule={'security_group_id':group_id,'direction':direction,'ethertype':'IPv4' if source.version==4 else 'IPv6',
              'protocol':protocol,'multiport':str(port),'remote_ip_prefix':str(source),'action':'allow','priority':1}
        params={'security_group_rule':rule}
        return await self._change('POST','security-group-rules','CreateSecurityGroupRule/v3',
                                  {'security_group_rule':rule},params,confirm,plan_id,'security_group_rule',group_id)

    async def delete_rule(self,group_id,rule_id,confirm=False,plan_id=None):
        identifier(group_id);identifier(rule_id)
        params={'security_group_rule_id':rule_id}
        return await self._change('DELETE','security-group-rules/'+rule_id,'DeleteSecurityGroupRule/v3',
                                  None,params,confirm,plan_id,None,group_id,rule_id)

    async def delete_group(self,group_id,confirm=False,plan_id=None):
        identifier(group_id)
        params={'security_group_id':group_id}
        return await self._change('DELETE','security-groups/'+group_id,'DeleteSecurityGroup/v3',
                                  None,params,confirm,plan_id,None,group_id,None,
                                  ['Deleting removes every rule in the group at once; the backend rejects groups still referenced by instances or NICs - verify nothing uses it first.'])

    async def _read_group(self,group_id):
        identifier(group_id)
        data=await self.koocli.call('VPC','ShowSecurityGroup/v3',{'security_group_id':group_id})
        group=data.get('security_group') if isinstance(data,dict) else None
        if isinstance(group,dict) and isinstance(data.get('security_group_rules'),list) and 'security_group_rules' not in group:
            group={**group,'security_group_rules':data['security_group_rules']}
        if not isinstance(group,dict) or group.get('id')!=group_id:
            raise McpToolError('MCP_SDK_ERROR','Security group identity not verified')
        return group

    async def _change(self,method,suffix,operation,body,params,confirm,plan_id,result_key,group_id=None,rule_id=None,extra_warnings=None):
        path=ROOT+suffix
        # Bind the selected parent even for DELETE whose command only carries the rule ID.
        digest=self.intent_digest(method,path,{'request':body,'group_id':group_id})
        warnings=['Shared security-group changes affect every associated resource; verify the association inventory before confirming.',
                  'Creating a group does not attach it to an application or open port 8443.']
        if extra_warnings:warnings.extend(extra_warnings)
        notices={'warnings':warnings,'completion_verified':False}
        if not confirm:
            return {'status':'confirmation_required','execution':'not_executed','changes':body,'group_id':group_id,
                    'resource_path':path,**notices,**self.plans.issue(digest)}
        if os.getenv('SUPABASE_ENABLE_WRITES')!='true' or os.getenv('HUAWEICLOUD_MCP_READ_ONLY','false').lower()=='true':
            raise McpToolError('MCP_READ_ONLY','Writes are disabled')
        if group_id:
            group=await self._read_group(group_id)
            assert_not_protected(group)
            rules=group.get('security_group_rules')
            if rule_id:
                if not isinstance(rules,list) or not any(isinstance(r,dict) and r.get('id')==rule_id and r.get('security_group_id')==group_id for r in rules):
                    raise McpToolError('MCP_GUARDRAIL_BLOCKED','Rule ownership not verified')
            if method=='POST':
                requested=body['security_group_rule']
                if not isinstance(rules,list):
                    raise McpToolError('MCP_GUARDRAIL_BLOCKED','Existing rules must be read before adding rules')
                if any(isinstance(r,dict) and all(r.get(k)==v for k,v in requested.items() if k!='security_group_id') for r in rules):
                    raise McpToolError('MCP_GUARDRAIL_BLOCKED','An identical rule already exists')
        self.plans.claim(plan_id,digest)
        try:
            data=await self.koocli.call('VPC',operation,params)
            resource_id=rule_id or group_id
            if method=='DELETE':
                pass
            else:
                record=data.get(result_key) if isinstance(data,dict) else None
                if not isinstance(record,dict):raise ValueError()
                resource_id=identifier(record.get('id'))
                if group_id and record.get('security_group_id')!=group_id:raise ValueError()
            self.plans.finish(plan_id,'accepted')
            return {'status':'applied','resource_id':resource_id,'plan_id':plan_id,**notices,
                    'follow_up':'Read the resource and verify application connectivity. No RDS job is created. This ledger record remains non-replayable.'}
        except BaseException:
            self.plans.finish(plan_id,'unknown')
            raise RecoveryError('MCP_SDK_ERROR','VPC write result unknown','submission_unknown',
                                'Inspect the plan and VPC resource; never blindly repeat a write.',plan_id) from None

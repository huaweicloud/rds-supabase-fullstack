from huaweicloud_mcp_core.security import ToolRisk,guard
from mcp_server_supabase.service.network import Network

def register(server):
    service=Network()

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def list_supabase_security_groups(limit:int=10,marker:str|None=None)->dict:
        """Read a VPC security-group page through KooCLI (the RDS origin does not serve the VPC API)."""
        return await service.list_groups(limit,marker)

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def show_supabase_security_group(group_id:str)->dict:
        """Read a VPC group and its rules through KooCLI. Does not prove which applications share the group."""
        return await service.show_group(group_id)

    @server.tool()
    @guard(risk=ToolRisk.WRITE)
    async def create_supabase_security_group(name:str,description:str|None=None,confirm:bool=False,plan_id:str|None=None)->dict:
        """Preview then create a native VPC group through KooCLI; no automatic attachment or application ingress. Pass a purpose description (<=255 chars, no angle brackets) so auto-created groups stay auditable."""
        return await service.create_group(name,description,confirm,plan_id)

    @server.tool()
    @guard(risk=ToolRisk.DANGEROUS)
    async def add_supabase_security_group_rule(group_id:str,source_cidr:str,port:int=8443,direction:str='ingress',protocol:str='tcp',confirm:bool=False,plan_id:str|None=None)->dict:
        """Add one TCP/UDP rule after confirmation: ingress (source CIDR) or egress (destination CIDR). Verify every shared resource first."""
        return await service.add_rule(group_id,source_cidr,port,direction,protocol,confirm,plan_id)

    @server.tool()
    @guard(risk=ToolRisk.DANGEROUS)
    async def delete_supabase_security_group_rule(group_id:str,rule_id:str,confirm:bool=False,plan_id:str|None=None)->dict:
        """Delete only the specified rule after ownership and shared-resource impact checks; can interrupt traffic."""
        return await service.delete_rule(group_id,rule_id,confirm,plan_id)

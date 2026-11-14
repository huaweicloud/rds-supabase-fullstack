from huaweicloud_mcp_core.security import ToolRisk,guard
from mcp_server_supabase.service.network import Network

def register(server):
    service=Network()

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def list_supabase_security_groups(limit:int=10,marker:str|None=None)->dict:
        """Find security groups usable for RDS Supabase applications. Lists one page at a time."""
        return await service.list_groups(limit,marker)

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def show_supabase_security_group(group_id:str)->dict:
        """Inspect one security group's full rule set before wiring an RDS Supabase application."""
        return await service.show_group(group_id)

    @server.tool()
    @guard(risk=ToolRisk.WRITE)
    async def create_supabase_security_group(name:str,description:str|None=None,confirm:bool=False,plan_id:str|None=None)->dict:
        """Create a dedicated security group for an RDS Supabase application. Preview first, confirm to apply; describe the purpose so auto-created groups stay auditable."""
        return await service.create_group(name,description,confirm,plan_id)

    @server.tool()
    @guard(risk=ToolRisk.DANGEROUS)
    async def add_supabase_security_group_rule(group_id:str,source_cidr:str,port:int=8443,direction:str='ingress',protocol:str='tcp',confirm:bool=False,plan_id:str|None=None)->dict:
        """Open one port for an RDS Supabase application, matching the actual deployment: 8443 ingress is the default public entry, 5432 guards the managed PostgreSQL, and both move when the user customized ports at creation. Confirm before applying; shared groups affect neighbors."""
        return await service.add_rule(group_id,source_cidr,port,direction,protocol,confirm,plan_id)

    @server.tool()
    @guard(risk=ToolRisk.DANGEROUS)
    async def delete_supabase_security_group_rule(group_id:str,rule_id:str,confirm:bool=False,plan_id:str|None=None)->dict:
        """Remove one rule when tightening access (e.g. revoking a stale CIDR). Ownership-checked; deleting may interrupt live traffic."""
        return await service.delete_rule(group_id,rule_id,confirm,plan_id)

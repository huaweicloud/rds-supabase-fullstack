from huaweicloud_mcp_core.security import ToolRisk, guard
from mcp_server_supabase.service.planning import PlanningService


def register(server):
    service = PlanningService()

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def get_supabase_capabilities() -> dict[str, object]:
        """List the available capabilities of the RDS Supabase management MCP. Run first; returns an offline scope declaration (transport mode, execution policies, implemented operations, six scenario contracts), never cloud status."""
        return service.capabilities()

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def plan_supabase_creation(manage_type: str | None = None, needs_storage: bool | None = None, needs_public_access: bool | None = None, needs_ssl: bool | None = None, needs_email_login: bool | None = None, needs_github_login: bool | None = None) -> dict[str, object]:
        """Plan application creation from intent, without cloud calls. Args: manage_type is newly_instance or existed_instance (omit to keep the route as a decision point); needs_storage/needs_public_access/needs_ssl/needs_email_login/needs_github_login are optional intents (omit = open decision point, true = plan the branch, false = plan the exclusion). Returns a phase-structured plan (decision_points, pre_creation, creation, post_creation, external_dependencies, security_notes, missing); use create_supabase_application with a protected local request for submission."""
        return await service.creation(manage_type, needs_storage, needs_public_access, needs_ssl, needs_email_login, needs_github_login)

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def plan_supabase_ssl(enable_ssl: bool = True) -> dict[str, object]:
        """Plan SSL selection without cloud calls. Args: enable_ssl defaults true; false plans disabling. Returns planning status and missing contracts."""
        return await service.ssl(enable_ssl)

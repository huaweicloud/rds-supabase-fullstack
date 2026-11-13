"""Offline planning only; no cloud operation or invented resource data."""
import os
from mcp_server_supabase.service.contracts import ssl_body
from mcp_server_supabase.client.base import OfflineClient, SupabaseClient

SCENARIOS = {
    "create": "Single creation via local reference available: existing PG or postPaid new PG; intent-driven phase planning via plan_supabase_creation; backend policy/live acceptance pending",
    "delete": "Application-only execution available; PG cascade remains unavailable",
    "access": "SSL/EIP/application-password adapters available; certificate discovery and live validation pending",
    "security_group": "Native VPC group query/create and rule add/delete adapters available; shared-resource inventory and live validation pending",
    "apikey": "Metadata/reset and protected local-file key delivery available; automatic new-key correlation unavailable",
    "business_config": "Auth/SMTP/GitHub/confirmation-template/OBS adapters available; omitted SK requires enabled Storage and unchanged AK",
}


class PlanningService:
    def __init__(self, client: SupabaseClient | None = None):
        self.client = client if client is not None else OfflineClient()

    def capabilities(self) -> dict[str, object]:
        return {"mode": "configured_" + os.getenv("SUPABASE_TRANSPORT", "rest"), "generated_supabase_sdk": False, "input_policy": "reject_unknown_fields", "local_plan_cancellation": "prepared_only", "cloud_execution": "configured_subset", "implemented_operations": ["application queries", "key metadata", "auth query", "job query", "bounded job observation", "accepted Auth plan reconciliation", "SSL", "EIP", "application-only deletion", "key reset", "registration flags", "local request references", "application password", "Auth providers and confirmation template", "OBS full-credential update", "VPC group query/create", "VPC rule add/delete", "creation candidate queries", "Single creation", "protected local key delivery"], "scenarios": SCENARIOS.copy()}

    async def creation(self, manage_type=None, needs_storage=None, needs_public_access=None,
                       needs_ssl=None, needs_email_login=None, needs_github_login=None) -> dict[str, object]:
        if manage_type is not None and manage_type not in ("newly_instance", "existed_instance"):
            return {"error": {"code": "MCP_INVALID_ARGS", "message": "Invalid manage_type", "hint": "Use newly_instance or existed_instance"}}
        decision = []
        if manage_type is None:
            decision.append("database route: newly_instance (create a new PG together) or existed_instance (manage an existing PG) - ask the user")
        if needs_storage is None:
            decision.append("file storage requirement (images/videos/files): decides the OBS bucket and the storage_component in the creation request")
        if needs_public_access is None:
            decision.append("public access requirement (browser/API from outside the VPC): decides EIP binding, security-group opening and api_external_url")
        if needs_ssl is None:
            decision.append("https requirement: decides an external CCM certificate purchase and the post-creation SSL switch")
        if needs_email_login is None:
            decision.append("email login requirement: decides the SMTP provider setup after creation")
        if needs_github_login is None:
            decision.append("GitHub login requirement: decides the OAuth App setup after creation")

        pre = ["collect application name (4-64 chars) and region/project from the environment",
               "select the Supabase flavor via list_supabase_flavors (requires az_code)",
               "generate the application password locally into the protected request file - never in chat",
               "select the VPC/subnet via KooCLI (pick a subnet with free IPs)"]
        if needs_storage is True:
            pre.append("decide the OBS bucket: reuse an existing private bucket (KooCLI hcloud obs ls; a public bucket needs explicit risk acknowledgment) or create a dedicated private multi-AZ bucket (KooCLI hcloud obs mb); write bucket name plus persistent AK/SK into storage_component - the creation path requires full credentials, SK omission is not available")
        elif needs_storage is False:
            pre.append("write storage_component as {enabled:false} - the field is mandatory even when storage is not used")
        pre.append("prepare both security groups before submit: a dedicated application group (optional at creation but cannot be attached later) and, on route A, the database group (required); rules are added after creation")
        if manage_type == "newly_instance":
            pre += ["choose the AZ via KooCLI RDS ListAvailableZones",
                    "choose the PG engine version via KooCLI RDS ListDatastores",
                    "choose the database flavor via KooCLI RDS ListFlavors (depends on version and AZ - not the same list as the application flavor)",
                    "choose the disk type from the environment's available storage types via KooCLI RDS ListStorageTypes (prefer a high-performance SSD) and the size",
                    "Single mode and postPaid billing only - HA and prepaid are rejected; omit port to keep the backend default"]
        elif manage_type == "existed_instance":
            pre += ["select a manageable PG via list_supabase_manageable_instances (status normal, no in-flight action)",
                  "collect database_name (the connection username) from the user",
                  "the user writes the root password into the protected request file - never in chat"]

        create = ["preview create_supabase_application (confirm=false) with the request-file reference",
                  "submit once after user confirmation with confirm=true plus the returned plan_id (10-minute TTL)",
                  "expect roughly 20-30 minutes; route A returns two jobs (application and database) - track both",
                  "verify with show_supabase_application: status normal and no in-flight action"]

        post = []
        if needs_public_access is True or needs_public_access is None:
            post += ["bind an EIP (list or create via KooCLI, bind via change_supabase_eip) and verify public_ip is set",
                     "open the security-group rules: application group 8443 ingress from the user CIDR (0.0.0.0/0 only after explicit confirmation, via KooCLI), application group 5432 egress (KooCLI), database group 5432 ingress from the subnet",
                     "update api_external_url to the assembled public address via update_supabase_auth_config - mandatory after a successful bind; email links and OAuth callbacks point at it",
                     "probe the access address (any HTTP status means reachable)"]
        else:
            post.append("internal access only: hand over the private_ip address; no EIP or security-group opening")
        if needs_ssl is True or needs_ssl is None:
            post.append("https: the user purchases a CCM certificate externally (this MCP has no purchase capability), then change_supabase_ssl with the certificate id; the switch briefly interrupts service - schedule a low-peak window and update api_external_url to https afterwards")
        else:
            post.append("http only (enable_ssl stays false) - acceptable for internal or trial use")
        if needs_email_login is True or needs_email_login is None:
            post.append("email login: collect SMTP non-secret fields in chat, the SMTP password goes to the request file, update via update_supabase_auth_config, verify by sending a real test email")
        if needs_github_login is True or needs_github_login is None:
            post.append("GitHub login: the user creates a GitHub OAuth App, the client secret goes to the request file, the callback URL must match the public access address, verify with a real login")
        post.append("deliver the access info card (show_supabase_application + list_supabase_api_keys; key values only to protected local files)")

        return {"status": "planning_only", "execution": "not_executed", "manage_type": manage_type,
                "decision_points": decision, "pre_creation": pre, "creation": create, "post_creation": post,
                "external_dependencies": ["AZ, PG version, database flavor, disk type, VPC/subnet and idle-EIP queries run via KooCLI - this MCP ships no input-discovery tools",
                                          "OBS bucket listing and creation run via KooCLI",
                                          "CCM certificate purchase runs in the console - no purchase tool exists",
                                          "the route-B root password and SMTP/GitHub secrets are provided by the user outside the chat"],
                "security_notes": ["application password, database password, storage AK/SK, SMTP password and GitHub client secret live only in the protected local request file; previews mask them",
                                   "API key values are delivered only to protected local files, never into chat"],
                "missing": ["verified live candidates (queries go through KooCLI/console)", "backend password/version/capacity/sale policies", "CCM certificate discovery and purchase", "resource and business acceptance"]}

    async def ssl(self, enable_ssl: bool) -> dict[str, object]:
        if not enable_ssl:
            return {"status": "planning_only", "execution": "not_executed", "request_body": ssl_body(False), "missing": ["verified transport", "job terminal schema", "live state verification"]}
        return {"status": "planning_only", "execution": "not_executed",
                "steps": ["list certificates", "select compatible certificate", "review SSL enable plan", "submit once after execution support exists", "verify application state"],
                "certificates": await self.client.list_certificates(),
                "missing": ["certificate schema/compatibility", "response and SSL effective-state contract"]}

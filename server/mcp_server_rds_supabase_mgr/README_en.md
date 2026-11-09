# RDS Supabase Control-Plane MCP Server

> **Language switch:** English | [中文](./README.md)

## Version

0.3.8a2 (development prerelease; full six-scenario production acceptance is
not yet complete)

## Overview

MCP Server for the **fully-managed lifecycle administration** of Huawei Cloud
RDS Supabase (self-hosted Supabase on RDS PostgreSQL) — the control plane:
application creation, configuration, secure access, and deletion. It operates
Supabase applications through the native RDS management API. SQL and data
operations belong to a separate data-plane capability, see
`server/mcp_server_rds_supabase`; the two servers are delivered independently
and do not replace each other.

Companion skill: `skills/huaweicloud-supabase/rds-supabase-mgr-mcp` (intent
understanding, information completion, impact presentation, and confirmation
guidance). See the [user guide](docs/USER_GUIDE.md) for the full workflow.

## Category

Database / RDS Supabase fully-managed lifecycle (control plane)

## Features

**Application query**

- List and inspect Supabase applications in the current project
- Report the MCP's own capability subset and gaps (cloud_verified=false; no
  cloud probing)

**Application creation**

- Discover creation candidates: manageable PG instances, Supabase flavors
- Single-mode creation submission (existing PG or on-demand new PG) with
  two-phase confirmation

**Application deletion**

- Delete the Supabase application while retaining the PG (which may continue
  to incur charges); no PG cascade deletion

**Access control**

- SSL toggle (enabling requires a verified certificate ID)
- EIP bind/unbind
- Application password change (via protected local request references; no
  plaintext collection)

**Security groups (dedicated VPC endpoint)**

- Query security groups and rules, create groups, add/remove TCP port rules

**ApiKey**

- Metadata query (six-field whitelist, no plaintext)
- Reset (with prominent downstream-invalidation warning)
- Deliver a designated key to a protected local file (never echoed in chat)

**Business configuration**

- Sign-up/anonymous flags, Auth providers (GitHub/SMTP), URLs and
  confirmation mail templates, OBS storage configuration

**Jobs and execution ledger**

- Job status query and bounded read-only observation
- Local plan inspection/cancellation/reconciliation; unknown outcomes are
  persisted and never replayed

**Common capabilities**

- Two-phase confirmation (confirm + plan_id bound to parameters, target, and
  credential digest)
- Cloud-write opt-in off by default; shared-core read-only interception,
  protection lists, structured audit, and output masking

## Tool list

| Tool | Scenario | Risk | Notes |
|---|---|---|---|
| `get_supabase_capabilities` | Query MCP capabilities and gaps | READ | cloud_verified=false |
| `list_supabase_applications` | List applications (paginated) | READ | May include other types; verify type=supabase |
| `show_supabase_application` | Application detail and status | READ | Status is not proof of completion |
| `list_supabase_api_keys` | ApiKey metadata query | READ | Whitelisted output, no plaintext |
| `reset_supabase_api_key` | Reset ApiKey (confirm required) | DANGEROUS | Pre-submit exact-ID uniqueness check |
| `deliver_supabase_api_key` | Deliver designated key to local file (confirm required) | DANGEROUS | Via delivery_ref alias |
| `show_supabase_auth_config` | Auth configuration query | READ | Secrets excluded |
| `update_supabase_auth_flags` | Sign-up/anonymous flags (confirm required) | WRITE | Only explicitly provided booleans are updated |
| `update_supabase_auth_config` | Auth providers/URL/templates (confirm required) | WRITE | Via local request_ref |
| `update_supabase_storage` | OBS storage configuration (confirm required) | WRITE | Full credentials required on first enablement |
| `plan_supabase_creation` | Creation planning | READ | planning_only, not an execution plan |
| `list_supabase_flavors` | Supabase flavor candidates | READ | creation_ready=false, not a quote |
| `list_supabase_manageable_instances` | Manageable PG query | READ | Same |
| `create_supabase_application` | Single creation submission (confirm required) | DANGEROUS | Via local request_ref; Single mode only |
| `delete_supabase_application` | Delete application, retain PG (confirm required) | DANGEROUS | No PG cascade deletion |
| `change_supabase_ssl` | SSL toggle (confirm required) | WRITE | Enable needs cert ID; disable passes null |
| `plan_supabase_ssl` | SSL toggle planning | READ | Certificate steps and gaps, no submission |
| `change_supabase_eip` | EIP bind/unbind (confirm required) | WRITE | Bind needs ID + IPv4; unbind must omit binding args |
| `change_supabase_application_password` | Application password change (confirm required) | DANGEROUS | Via local request_ref, no plaintext |
| `list_supabase_security_groups` | List security groups | READ | Dedicated VPC endpoint |
| `show_supabase_security_group` | Security group detail | READ | |
| `create_supabase_security_group` | Create security group (confirm required) | WRITE | Creating a group does not make the app reachable |
| `add_supabase_security_group_rule` | Add inbound rule (confirm required) | DANGEROUS | TCP port specified (default 8443) |
| `delete_supabase_security_group_rule` | Delete rule (confirm required) | DANGEROUS | |
| `show_supabase_job` | Job status query | READ | completion_verified=false |
| `wait_supabase_job` | Bounded read-only observation | READ | Default 3, at most 10 attempts |
| `inspect_supabase_plan` | Local plan inspection | READ | No cloud calls |
| `cancel_supabase_plan` | Cancel an unsubmitted plan | WRITE | Local ledger only, idempotent |
| `reconcile_supabase_auth_plan` | Auth plan reconciliation | WRITE | Cloud read + local write; Auth flags only |

## Usage guide

### Prerequisites

- Python 3.10+
- UV

**Linux/macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installation

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run mcp-huaweicloud-rds-supabase-mgr          # stdio (default)
uv run mcp-huaweicloud-rds-supabase-mgr -t streamable-http
```

`mcp-huaweicloud-rds-supabase-mgr` is the canonical entry point; the legacy
entry `mcp_server_supabase` is retained for transition and is equivalent.

### Verification

```bash
uv run pytest                       # 80% coverage gate
uv run python tests/smoke_stdio.py
```

### Diagnostics CLI

```bash
uv run python -m mcp_server_supabase.diagnostics check       # config syntax and dependencies only
uv run python -m mcp_server_supabase.diagnostics offline     # offline stdio self-check
# Real read-only checks only in an authorized test environment:
uv run python -m mcp_server_supabase.diagnostics readonly --allow-cloud-read
```

The diagnostics CLI never submits cloud writes and reports summary checks
only — no raw resource values or credentials.

## Configuration

### Environment variables

Choose one credential mode: **REST token mode** (default,
`HUAWEICLOUD_AUTH_TOKEN`) or **sdk_core mode**
(`SUPABASE_TRANSPORT=sdk_core` + AK/SK). Credentials are injected by the
trusted host environment and are never tool arguments.

| Variable | Required | Description | Default |
|---|---|---|---|
| `SUPABASE_RDS_ENDPOINT` | Yes | Native RDS HTTPS service origin (no path/query/userinfo; not the Console or a /rest proxy) | - |
| `HUAWEICLOUD_PROJECT_ID` | Yes | Target project ID (matching the site) | - |
| `HUAWEICLOUD_AUTH_TOKEN` | REST mode | Externally provisioned service token, read per request | - |
| `SUPABASE_TRANSPORT` | No | Set `sdk_core` to use Huawei SDK Core signing | REST token |
| `HUAWEICLOUD_ACCESS_KEY` | sdk_core mode | Account AK | - |
| `HUAWEICLOUD_SECRET_KEY` | sdk_core mode | Account SK | - |
| `HUAWEICLOUD_SECURITY_TOKEN` | No | STS temporary credential token | - |
| `SUPABASE_VPC_ENDPOINT` | No | Dedicated native VPC endpoint for security-group scenarios | - |
| `SUPABASE_ENABLE_WRITES` | No | Cloud-write opt-in; cloud writes require `true` | `false` |
| `HUAWEICLOUD_MCP_READ_ONLY` | No | `true` intercepts all WRITE/DANGEROUS tools | `false` |
| `SUPABASE_STATE_FILE` | No | Local execution ledger (SQLite); keep one ledger across restarts | User-local state dir |
| `SUPABASE_REQUESTS_FILE` | No | Sensitive-request local reference registry (operator-provisioned) | - |
| `REQUESTS_CA_BUNDLE` | No | Custom trusted CA (PEM file) | - |
| `HUAWEICLOUD_MCP_PROTECTED_IDS` | No | Guardrail: protected resource IDs (comma-separated, block on match) | empty |
| `HUAWEICLOUD_MCP_PROTECTED_NAMES` | No | Guardrail: protected resource names (comma-separated, block on match) | empty |
| `HUAWEICLOUD_MCP_PROTECTED_TAGS` | No | Guardrail: protected tags (comma-separated `k` or `k=v`) | empty |
| `HUAWEICLOUD_MCP_GUARDRAILS_CONFIG` | No | Advanced rules file `guardrails.yaml` | empty |
| `HUAWEICLOUD_MCP_AUDIT_FILE` | No | Audit JSONL file (audit always on, defaults to stderr) | empty |
| `MCP_SERVER_PORT` | No | streamable-http port | `8000` |
| `MCP_SERVER_HOST` | No | streamable-http bind address | `0.0.0.0` |

### Safety mechanisms

- **Two-phase confirmation**: write tools default to `confirm=false`, persist
  a ten-minute plan, and return a `plan_id`; submission requires the **same
  parameters** with `confirm=true` + `plan_id`. Changed parameters, project,
  service origin, or credentials require a fresh preview.
- **Execution ledger**: a local SQLite ledger records plans, jobs, and
  states. On timeout or unknown outcomes, run `inspect_supabase_plan` first;
  `submitted`/`accepted`/`unknown` intents are never replayed, and the ledger
  must not be deleted to bypass protection.
- **Local sensitive-request references**: passwords, SMTP, GitHub, and OBS
  credentials are provided via an operator-provisioned local registry
  (`SUPABASE_REQUESTS_FILE`) by alias; tools accept no plaintext and never
  read delivered files.
- **202 means accepted, not completed**: job `completed` is not business
  verification; re-query the resource.
- **Layered write permissions**: the cloud-write opt-in
  (`SUPABASE_ENABLE_WRITES`, off by default) and the shared-core read-only
  interception (`HUAWEICLOUD_MCP_READ_ONLY`) act independently; neither may
  be modified by the agent itself.

**Guardrail known limitation (parameter-level matching):** protection rules
match resource IDs and name-like parameters in tool calls. Protection
configured only on the cloud side but absent from call parameters cannot
match; configure protection lists proactively via environment variables or
`guardrails.yaml`.

Example `guardrails.yaml`:

```yaml
version: 1
rules:
  - id: protect-prod-supabase
    match:
      tools: ["delete_supabase_application"]
      risks: [DANGEROUS]
      resources:
        name_patterns: ["^prod-"]
    action: block
    message: Production Supabase applications are protected; contact ops.
```

### uvx (git repository version)

```json
{
    "mcpServers": {
        "rds-supabase-mgr-mcp": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr",
                "mcp-huaweicloud-rds-supabase-mgr"
            ],
            "env": {
                "SUPABASE_RDS_ENDPOINT": "",
                "HUAWEICLOUD_PROJECT_ID": "",
                "HUAWEICLOUD_AUTH_TOKEN": "",
                "HUAWEICLOUD_MCP_READ_ONLY": "true",
                "SUPABASE_ENABLE_WRITES": "false"
            }
        }
    }
}
```

For sdk_core mode (AK/SK) see [examples/mcp-sdk.example.json](examples/mcp-sdk.example.json).

## Examples

### Cursor / Claude Desktop / Trae

Fill the JSON config into your MCP client with credentials (stay read-only on
first setup), then use natural language:

- "What Supabase scenarios does this MCP support?" → `get_supabase_capabilities()`
- "List the Supabase applications in this project" → `list_supabase_applications()`
- "Show the status of application app-123" → `show_supabase_application(application_id="app-123")`
- "List the ApiKey types and statuses of app-123, without values" → `list_supabase_api_keys(application_id="app-123")`
- "Preview disabling SSL for app-123, do not execute yet" → `change_supabase_ssl(application_id="app-123", enable_ssl=false)` (`confirm=false` returns a plan and `plan_id`)
- "Confirm the SSL change I just previewed" → same parameters with `confirm=true` + `plan_id`
- "List the manageable PG instances" → `list_supabase_manageable_instances()`
- "Delete application app-123, explain the impact first" → `delete_supabase_application(...)` (preview first; deletes the app, retains the PG)
- "Check the status of job job-456" → `show_supabase_job(job_id="job-456")`

## Further documentation

- [User guide](docs/USER_GUIDE.md) — installation, verification, and the
  natural-language workflow
- [Tool contracts](docs/TOOL_CONTRACTS.md) — authoritative input/output and
  confirmation semantics
- [Recovery rules](docs/RECOVERY.md), [reconciliation](docs/RECONCILIATION.md)
- [Local secret I/O](docs/LOCAL_REQUESTS.md) — the sensitive-request
  reference mechanism
- [SDK mode](docs/SDK.md), [migration notes](docs/MIGRATION.md)
- [docs/legacy/](docs/legacy/) — archived Windows offline-bundle workflow

## License

MIT

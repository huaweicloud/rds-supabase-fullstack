# RDS Supabase Control-Plane MCP Server

> **Language switch:** English | [中文](./README.md)

## Version

0.4.0a18 (development prerelease); Python `3.10+`; MCP Python SDK `2.x`;
31 tools.

## Overview

This server wraps the Huawei Cloud RDS Supabase (self-hosted Supabase on RDS
PostgreSQL) management API as MCP tools, covering application creation,
configuration, public access provisioning, change, and deletion. It is the
control plane: Supabase applications are operated through the native RDS
management API. SQL and data operations belong to a separate data-plane
service, see `server/mcp_server_rds_supabase`; the two servers are delivered
independently and do not replace each other.

Security-group operations execute through the KooCLI channel
(see [Security groups and the KooCLI channel](#security-groups-and-the-koocli-channel)).

Companion skill: `skills/huaweicloud-supabase/rds-supabase-mgr-mcp` (intent
understanding, information completion, impact presentation, and confirmation
guidance).

## Quick start

Prepare Python 3.10+, [uv](https://docs.astral.sh/uv/), and Huawei Cloud
credentials (AK/SK or a service token). Stay read-only on first contact:

```bash
export HUAWEICLOUD_MCP_READ_ONLY="true"
uvx --from "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr" \
  mcp-huaweicloud-rds-supabase-mgr
```

Generic stdio client configuration (token mode; AK/SK mode see
[examples/mcp-sdk.example.json](examples/mcp-sdk.example.json)):

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
        "SUPABASE_RDS_ENDPOINT": "<native RDS HTTPS endpoint>",
        "HUAWEICLOUD_PROJECT_ID": "<project ID>",
        "HUAWEICLOUD_AUTH_TOKEN": "<service token>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

Once connected, call `list_supabase_applications` to verify the endpoint,
permissions, and project. Full installation, credential modes, and the
security-group prerequisites are covered below.

## Category

Database / cloud resource management / operations automation (RDS Supabase
lifecycle, control plane).

## Features

**Application query**

- Application list: pagination, filtering, sorting
- Application detail: basic configuration (name, mode, status), flavor
  configuration (flavor, nodes), security configuration (SSL), network
  configuration (public/private IPs, port), storage configuration (OBS
  bucket integration)
- Capability list: what this service manages, what it does not, and what
  stays with the user

**Application creation**

- Analyze the business scenario and usage pattern before creating, then
  break it down item by item - what to prepare for each scenario and
  how:
  - **Managed database instance**: create a new instance, or attach an
    existing one
  - **OBS storage integration**: for image, video, and large-file
    storage needs
  - **EIP binding**: for public-network access
  - **SSL integration**: for high-security requirements; a CCM
    certificate must be purchased first
- Application flavor list query: defaults to Single-mode flavors; whether
  Ha (primary/standby) flavors are available depends on real-time,
  region-specific queries
- Manageable PostgreSQL instance query — create-with-existing-instance
  scenario
- Database instance flavor query — create-with-new-instance scenario
  (via KooCLI)
- Surrounding dependency queries: VPC, subnet, availability zone,
  security group, OBS bucket, and more (via KooCLI)
- Creation submission: Single/Ha, pay-per-use or yearly/monthly,
  two-phase confirmation; yearly/monthly returns a console-payable order

**Application deletion**

- Delete the application, retaining PG (no cascade deletion)
- Delete the managed PG instance: four-layer verification (dual
  identifiers, managed binding, shared-reference check, live pre-delete
  read); pay-per-use only

**Access control**

- SSL enable/disable (enabling requires a purchased CCM certificate)
- Elastic public IP bind/unbind (controls public access)
- Application password change (via protected local request references;
  no plaintext collection)

**Security group configuration (KooCLI channel)**

- Security group list and detail queries
- Create security groups matching application requirements
- Delete application security groups
- Add or remove inbound/outbound access rules

**ApiKey**

- Metadata query (whitelisted output, no plaintext)
- Reset (with a strong downstream-invalidation warning)
- Delivery to a protected local file (never echoed in chat)

**Business configuration**

- Sign-up/anonymous toggles, Auth providers (GitHub/SMTP), URLs and mail
  templates, OBS storage

**Jobs and execution record**

- Job status query and bounded watching
- Plan inspection/cancellation/reconciliation; unknown outcomes durably
  recorded, never replayed

**Cross-cutting**

- Two-phase confirmation (confirm + plan_id binding parameters, target,
  and a credential digest)
- Cloud-write switch off by default; read-only interception, protection
  lists, structured audit, output redaction

## Tool list

| Tool | Scenario | Risk |
|---|---|---|
| `get_supabase_capabilities` | List management capabilities | READ |
| `list_supabase_applications` | List applications (pagination, filter, sort) | READ |
| `show_supabase_application` | Application detail (status/SSL/IP) | READ |
| `list_supabase_api_keys` | API Key metadata (no values) | READ |
| `reset_supabase_api_key` | Reset an ApiKey (confirm) | DANGEROUS |
| `deliver_supabase_api_key` | Deliver a key to a local file (confirm) | DANGEROUS |
| `show_supabase_auth_config` | Query Auth configuration | READ |
| `update_supabase_auth_flags` | Sign-up/anonymous toggles (confirm) | WRITE |
| `update_supabase_auth_config` | Auth providers/URLs/templates (confirm, via request_ref) | WRITE |
| `update_supabase_storage` | OBS storage configuration (confirm) | WRITE |
| `plan_supabase_creation` | Creation planning (intent-driven, no execution) | READ |
| `list_supabase_flavors` | Supabase flavor candidates | READ |
| `list_supabase_manageable_instances` | Manageable PG instances | READ |
| `create_supabase_application` | Creation submission (confirm, via request_ref) | DANGEROUS |
| `delete_supabase_application` | Delete application, keep PG (confirm) | DANGEROUS |
| `delete_supabase_managed_instance` | Delete the managed PG instance (confirm; binding-verified, unshared, pay-per-use only) | DANGEROUS |
| `change_supabase_ssl` | SSL toggle (confirm) | WRITE |
| `plan_supabase_ssl` | SSL switch planning | READ |
| `change_supabase_eip` | EIP bind/unbind (confirm) | WRITE |
| `change_supabase_application_password` | Application password change (confirm, via request_ref) | DANGEROUS |
| `list_supabase_security_groups` | List security groups | READ |
| `show_supabase_security_group` | Group detail with rules | READ |
| `create_supabase_security_group` | Create group (confirm) | WRITE |
| `add_supabase_security_group_rule` | Add one rule (confirm; ingress/egress, TCP/UDP) | DANGEROUS |
| `delete_supabase_security_group_rule` | Remove one rule (confirm, ownership-checked) | DANGEROUS |
| `delete_supabase_security_group` | Delete whole group (confirm, reference-checked) | DANGEROUS |
| `show_supabase_job` | Job status query | READ |
| `wait_supabase_job` | Bounded read-only watching | READ |
| `inspect_supabase_plan` | Local plan inspection | READ |
| `cancel_supabase_plan` | Cancel an unsubmitted plan | WRITE |
| `reconcile_supabase_auth_plan` | Auth plan reconciliation | WRITE |

READ tools are always available; WRITE/DANGEROUS tools are governed by
two-phase confirmation and environment switches (see
[Safety mechanisms](#safety-mechanisms)).

## Security groups and the KooCLI channel

The six security-group tools do not go through the RDS endpoint: the native
RDS origin does not proxy the VPC API, so direct calls always fail. They
execute via the local KooCLI (`hcloud`), calling VPC v3 operations
(`CreateSecurityGroup/v3`, `CreateSecurityGroupRule/v3`, and so on).

- **KooCLI prerequisite**: hcloud must be installed locally and its first-run
  privacy agreement accepted. Installation: section 4 of the skill
  [INSTALL.md](../../skills/huaweicloud-supabase/rds-supabase-mgr-mcp/INSTALL.md).
- **Binary location**: `HCLOUD_BIN` environment variable → fixed install
  directories → PATH, re-resolved on every call; no session restart needed
  after installation.
- **Credential injection**: credentials are injected per command only when
  both `HUAWEICLOUD_ACCESS_KEY` and `HUAWEICLOUD_SECRET_KEY` are set;
  otherwise the hcloud profile is used. **REST token mode requires a local
  hcloud profile** (`hcloud configure init`), or these tools report missing
  credentials.
- **Region and project**: region comes from `HUAWEICLOUD_REGION`, falling
  back to derivation from the `SUPABASE_RDS_ENDPOINT` hostname; the project
  is resolved by KooCLI as the region default project — sub-project accounts
  must configure `--cli-project-id` in the hcloud profile.
- **Error passthrough**: VPC backend error_code/error_msg/request_id pass
  through verbatim; an unaccepted privacy agreement, a missing binary, and
  timeouts each map to a dedicated error code with remediation guidance.

## Usage guide

### Prerequisites

1. Python 3.10+; [uv](https://docs.astral.sh/uv/) when using uvx.
2. Huawei Cloud credentials with the minimal required permissions
   (see [Permission recommendations](#permission-recommendations)).
3. For security-group tools: KooCLI installed locally with the privacy
   agreement accepted (see the previous section).

### Installation

**uvx direct run (recommended; the git repository is the only canonical
source):**

```bash
uvx --from "git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr" \
  mcp-huaweicloud-rds-supabase-mgr
```

The server is not published to PyPI; same-named third-party packages on
PyPI are not this server and must not be installed.

**Clone for development:**

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run mcp-huaweicloud-rds-supabase-mgr          # stdio (default)
uv run mcp-huaweicloud-rds-supabase-mgr -t streamable-http
```

`mcp-huaweicloud-rds-supabase-mgr` is the canonical entry; the legacy entry
`mcp_server_supabase` is kept transitionally and is equivalent. For
slow-network uvx startup timeouts, see the
[skill install reference](../../skills/huaweicloud-supabase/rds-supabase-mgr-mcp/references/install.md).

### Diagnostics CLI

```bash
uv run python -m mcp_server_supabase.diagnostics check       # config and dependency check only
uv run python -m mcp_server_supabase.diagnostics offline     # offline stdio self-check
# Auto-discover project and candidate RDS endpoints from credentials (REST token or AK/SK):
uv run python -m mcp_server_supabase.diagnostics discover
uv run python -m mcp_server_supabase.diagnostics discover --probe   # add read-only reachability probing
# Real read-only checks, only in an authorized test environment:
uv run python -m mcp_server_supabase.diagnostics readonly --allow-cloud-read
```

`discover` queries IAM for the project list and derives candidate endpoints
per region, listing `suggested_env` for selection; an explicitly configured
`SUPABASE_RDS_ENDPOINT` wins. Reachability does not imply permissions or
production acceptance. The diagnostics CLI submits no cloud writes and its
summaries contain no resource values or credentials.

## Configuration

### Environment variables

Pick one credential mode: **REST token mode** (default,
`HUAWEICLOUD_AUTH_TOKEN`) or **sdk_core mode** (`SUPABASE_TRANSPORT=sdk_core`
+ AK/SK). Credentials are injected by a trusted host environment, never as
tool parameters.

| Variable | Required | Description | Default |
|---|---|---|---|
| `SUPABASE_RDS_ENDPOINT` | yes | Native RDS HTTPS origin (no path/query/userinfo; not the Console or a /rest proxy). Derivable via `diagnostics discover` | - |
| `HUAWEICLOUD_PROJECT_ID` | yes | Target project ID (region-consistent) | - |
| `HUAWEICLOUD_AUTH_TOKEN` | REST mode | Pre-provisioned service token, read per request | - |
| `SUPABASE_TRANSPORT` | no | Set `sdk_core` to enable Huawei SDK Core signing | REST token |
| `HUAWEICLOUD_ACCESS_KEY` | sdk_core mode | Account AK | - |
| `HUAWEICLOUD_SECRET_KEY` | sdk_core mode | Account SK | - |
| `HUAWEICLOUD_SECURITY_TOKEN` | no | STS temporary-credential token | - |
| `HUAWEICLOUD_REGION` | no | Region for the security-group KooCLI channel; derived from the `SUPABASE_RDS_ENDPOINT` hostname when absent | derived |
| `HCLOUD_BIN` | no | Explicit KooCLI binary path override | auto-located |
| `SUPABASE_ENABLE_WRITES` | no | Cloud-write switch; must be `true` for cloud writes | `false` |
| `HUAWEICLOUD_MCP_READ_ONLY` | no | `true` intercepts all WRITE/DANGEROUS tools | `false` |
| `SUPABASE_STATE_FILE` | no | Local execution-record (SQLite) path; keep one record across restarts | user state dir |
| `SUPABASE_REQUESTS_FILE` | no | Local sensitive-request reference registry (operator-provisioned) | - |
| `REQUESTS_CA_BUNDLE` | no | Custom trusted CA bundle (PEM file) | - |
| `HUAWEICLOUD_MCP_PROTECTED_IDS` | no | Guardrail: protected resource IDs (comma-separated, hit = block) | empty |
| `HUAWEICLOUD_MCP_PROTECTED_NAMES` | no | Guardrail: protected resource names (comma-separated) | empty |
| `HUAWEICLOUD_MCP_PROTECTED_TAGS` | no | Guardrail: protected tags (comma-separated `k` or `k=v`) | empty |
| `HUAWEICLOUD_MCP_GUARDRAILS_CONFIG` | no | Path to a `guardrails.yaml` rules file | empty |
| `HUAWEICLOUD_MCP_AUDIT_FILE` | no | Audit JSONL file path (audit always on; defaults to stderr) | empty |
| `MCP_SERVER_PORT` | no | streamable-http port | `8000` |
| `MCP_SERVER_HOST` | no | streamable-http bind address | `0.0.0.0` |

### Safety mechanisms

- **Two-phase confirmation**: write tools default to `confirm=false`,
  persisting a ten-minute plan and returning a `plan_id`; confirm by
  resubmitting **identical parameters** with `confirm=true` + `plan_id`.
  Any change to parameters, project, endpoint, or credentials requires a
  fresh preview.
- **Local execution record**: SQLite records plans, jobs, and states. On a
  timeout or unknown outcome, inspect first (`inspect_supabase_plan`);
  `submitted`/`accepted`/`unknown` must never be replayed, and deleting the
  record to bypass protection is forbidden.
- **Local sensitive-request references**: password, SMTP, GitHub, and OBS
  credentials are supplied via an operator-provisioned local registry
  (`SUPABASE_REQUESTS_FILE`) by alias; tools accept no plaintext and never
  read delivered files.
- **202 means accepted only**: a `completed` job is not business
  verification; re-read the resource.
- **Layered write gating**: the cloud-write switch
  (`SUPABASE_ENABLE_WRITES`, default off) and the shared-core read-only
  interception (`HUAWEICLOUD_MCP_READ_ONLY`) act independently; neither can
  be modified by the agent itself.

**Known guardrail limitation (parameter-level matching):** protection rules
match resource IDs and name-like parameters in tool arguments. Protected
attributes configured only on the cloud side but absent from arguments
cannot match; configure protection lists via environment variables or
`guardrails.yaml` proactively.

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

## Examples

### Workflow 1: create a reachable application from scratch

1. Call `plan_supabase_creation` with the intent (database route / storage /
   public access / SSL) to get the staged preparation plan and required
   fields.
2. Prepare per the plan: dedicated security groups
   (`create_supabase_security_group`, then
   `add_supabase_security_group_rule` for 8443 ingress and 5432 egress),
   and the local request file (root password, storage credentials, and
   other secrets).
3. Preview with `create_supabase_application(request_ref, confirm=false)`,
   show the redacted parameters to the user, then submit identical
   parameters with `confirm=true` + `plan_id`.
4. Track the returned `job_id` with `show_supabase_job` (or bounded
   `wait_supabase_job`) to a terminal state.
5. Re-read `show_supabase_application`; if no public IP, bind an EIP with
   `change_supabase_eip`, then deliver access information via
   `list_supabase_api_keys` + `deliver_supabase_api_key`.

### Workflow 2: open security-group ports for an application

1. Preview and confirm `create_supabase_security_group` — a dedicated group
   with a purpose description.
2. Add the 8443 ingress rule (source CIDR) and the 5432 egress rule
   (`direction='egress'`) with `add_supabase_security_group_rule`, each
   previewed then confirmed.
3. Re-read with `show_supabase_security_group` and verify direction and
   port.
4. To revoke, use `delete_supabase_security_group_rule` (after verifying
   the group is not shared); retire the whole group with
   `delete_supabase_security_group` (after verifying no instance/NIC
   references).

Every write may execute asynchronously. A successful MCP call means the
cloud API accepted the request, not that the change has completed.

## Client compatibility

| Client | Transport | Notes |
|---|---|---|
| opencode | stdio | Project-level `opencode.json`, `mcp.servers.*` structure; connects automatically on save |
| Claude Code | stdio | Project-level `.mcp.json`; approve once in-session |
| Claude Desktop / Cursor / Trae | stdio | `command`/`args`/`env` configuration |
| CodeArts | stdio | Project-level `mcp_settings.json` (Settings → MCP tools); editing an entry needs a manual restart |
| Remote mode | Streamable HTTP | `mcp-huaweicloud-rds-supabase-mgr -t streamable-http`, endpoint `/mcp`; front it with HTTPS and authentication in production |

No legacy SSE transport is provided.

## Permission recommendations

- **Read-only discovery**: RDS application/flavor/instance queries plus IAM
  project listing; VPC, subnet, AZ, and EIP queries for creation planning
  run through KooCLI and follow the hcloud profile permissions.
- **Write operations**: grant only the RDS application create/change
  permissions and VPC security-group write permissions matching the tools
  actually enabled.
- **Dangerous operations**: deletions, password changes, and key resets
  should use a separate identity or temporary authorization, combined with
  `HUAWEICLOUD_MCP_PROTECTED_*` lists and confirmation rules.
- Never configure long-lived administrator credentials to an MCP client for
  convenience; prefer temporary security credentials in production.

## Development, testing, and verification

```bash
uv sync --all-groups
uv run ruff check src tests
uv run pytest                       # no cloud access by default; 80% coverage gate
uv run python tests/smoke_stdio.py  # offline stdio smoke test
```

Live validation must only run in a dedicated test account; when creating
billable resources, always clean up on failure paths and confirm deletion
jobs reach a terminal state. Before release, check wheel metadata, a fresh
Python 3.10 installation, and the MCP tool list.

## Contributing and support

Contribution workflow, security reporting, and version history live in the
repository-root `CONTRIBUTING.md`, `SECURITY.md`, and `CHANGELOG.md`. Use
GitHub Issues for general questions; credential leaks and security issues
must never be filed in public issues.

## Further documentation

- [User guide](docs/USER_GUIDE.md) — installation, verification, and the
  natural-language operation workflow
- [Tool contracts](docs/TOOL_CONTRACTS.md) — the authoritative input/output
  and confirmation semantics
- [Recovery rules](docs/RECOVERY.md) and
  [reconciliation contract](docs/RECONCILIATION.md) — failure routing and
  Auth plan reconciliation
- [Local secret I/O](docs/LOCAL_REQUESTS.md) — the sensitive-request
  reference mechanism
- [SDK mode](docs/SDK.md), [migration notes](docs/MIGRATION.md)
- [docs/legacy/](docs/legacy/) — archived offline Windows delivery process

## License

MIT

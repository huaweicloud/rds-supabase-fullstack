# RDS Supabase Control-Plane MCP Server

> **Language switch:** English | [中文](./README.md)

## Version

0.4.0a23 (development prerelease); Python `3.10+`; MCP Python SDK `2.x`;
32 tools.

## Overview

This server wraps the Huawei Cloud RDS Supabase (self-hosted Supabase on RDS
PostgreSQL) management API as MCP tools, covering application creation,
configuration, public access provisioning, change, and deletion. It is the
control plane: Supabase applications are operated through the native RDS
management API. SQL and data operations belong to a separate data-plane
service, see `server/mcp_server_rds_supabase`; the two servers are delivered
independently and do not replace each other.

The security-group tools wrap the KooCLI capability and work out of the box
(see [Security-group tools and the KooCLI division of labor](#security-group-tools-and-the-koocli-division-of-labor)).

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
- Capability list: declares this service's management scope and
  responsibility boundary — which operations it performs, and which
  remain with the user via the console

**Application creation**

- Analyze the business scenario and usage pattern before creating, then
  break it down item by item - what to prepare for each scenario and
  how:
  - **Managed database instance**: create a new instance, or attach an
    existing one. Creation returns differ by scenario - attaching returns
    the application job id and application id only; creating new builds
    the instance first and the application creation starts only after it
    succeeds, returning the instance job id and instance id, with the
    application job absent until the instance is ready
  - **OBS storage integration**: for image, video, and large-file
    storage needs
  - **EIP binding**: for public-network access
  - **SSL integration**: for high-security requirements; a CCM
    certificate must be purchased first
- Application flavor list query: returns the AZ list each flavor
  supports, doubling as the availability-zone selection source; defaults
  to Single-mode flavors, with Ha availability per real-time region query
- Manageable PostgreSQL instance query — create-with-existing-instance
  scenario
- Managed-instance catalog queries: engine versions, instance flavors,
  storage types — create-with-new-instance scenario
- One-call discovery of the application creation basics: versions,
  deployment mode (Single/Ha live-probed), saleable application flavors
- One-call discovery for the new-instance scenario: concurrent dependency
  queries with per-field recommended configuration
- Network auto-discovery: walks VPCs and their subnets, locks a subnet
  with sufficient free IPs, and yields the basic_config vpc_id/subnet_id
- Database instance flavor query — create-with-new-instance scenario
  (via KooCLI)
- Automatic dependency discovery: lists and detail configuration of
  surrounding resources — VPC, subnet, availability zone, security group,
  OBS bucket, and more (using KooCLI capability exploration)
- Creation submission: Single/Ha, pay-per-use or yearly/monthly,
  two-phase confirmation; yearly/monthly returns an order paid via the order tools

**Order management (yearly/monthly instances)**

- Prepaid order query: status, amounts, currency, paginated line items
- Order payment: balance payment for the approved order ID, amount and
  currency; preview-then-confirm two-phase, one submission
- Unpaid order cancellation: abandon an unneeded pending-payment order

**Application deletion**

- Delete the application, retaining PG (no cascade deletion)
- Delete the managed PG instance: four-layer verification (dual
  identifiers, managed binding, shared-reference check, live pre-delete
  read); pay-per-use only

**Access control**

- SSL enable/disable (enabling requires a purchased CCM certificate)
- Elastic public IP bind/unbind (controls public access)

**Security group configuration**

- Security group list and detail queries
- Create security groups matching application requirements
- Delete application security groups
- Add or remove inbound/outbound access rules

**Application access API keys**

- API key list query, filterable by purpose: `publishable` (public
  client-side), `secret` (server-side confidential), `anon` (anonymous
  access), `service_role` (server-side administrator)
- Reset a specific API key: counter key leakage and abuse
- Retrieve an API key value: never displayed in conversation; written to
  a protected local file to prevent privacy exposure

**Business configuration**

- Sign-up/anonymous toggles, Auth providers (GitHub/SMTP), URLs and mail
  templates, OBS storage

**Task status tracking**

- Query the status of a submitted task
- Poll task status to a terminal state within a bounded timeout, for
  waiting on task completion

**Local execution record**

- Plan inspection/cancellation/reconciliation; unknown outcomes durably
  recorded, never replayed

**Cross-cutting**

- Two-phase confirmation (confirm + plan_id binding parameters, target,
  and a credential digest)
- Cloud-write switch off by default; read-only interception, protection
  lists, structured audit, output redaction

## Tool list

Every write tool runs a two-phase confirmation: a preview returns the
changes and a plan identifier first, and only an explicit confirmation
submits. Tools that carry passwords or credentials accept no plaintext -
secrets are pre-provisioned into a local request file and referenced by
alias.

| Tool | Scenario | Risk | API doc |
|---|---|---|---|
| `get_supabase_capabilities` | See the scenarios and boundaries this service manages | READ | - |
| `list_supabase_applications` | Browse all Supabase applications with pagination, name filtering and sorting | READ | [ListSupabaseApplications](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplications) |
| `show_supabase_application` | Inspect one application's full configuration: flavor, nodes, network, SSL and storage integration | READ | [ShowSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ShowSupabaseApplication) |
| `list_supabase_api_keys` | View every API key's type and status; key values are never returned | READ | [ListSupabaseApplicationApiKeys](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplicationApiKeys) |
| `reset_supabase_api_key` | Reset a key on suspected leakage or scheduled rotation; the old key stops working | DANGEROUS | [ResetSupabaseApplicationApiKey](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ResetSupabaseApplicationApiKey) |
| `deliver_supabase_api_key` | Write a key's value to a protected local file for secure delivery | DANGEROUS | [ShowSupabaseApplicationApiKeyValue](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ShowSupabaseApplicationApiKeyValue) |
| `show_supabase_auth_config` | View the authentication baseline: sign-up toggles, third-party login, mail templates | READ | [ShowSupabaseApplicationAuthConfig](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ShowSupabaseApplicationAuthConfig) |
| `update_supabase_auth_flags` | Toggle user sign-up and anonymous access | WRITE | [ModifySupabaseApplicationAuthConfig](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationAuthConfig) |
| `update_supabase_auth_config` | Configure GitHub and SMTP login, callback URLs and mail templates | WRITE | [ModifySupabaseApplicationAuthConfig](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationAuthConfig) |
| `update_supabase_storage` | Integrate or change the OBS storage bucket | WRITE | [ModifySupabaseApplicationStorage](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationStorage) |
| `discover_supabase_create_basic_options` | One-call discovery of the application creation basics: versions, Single/Ha support (live-probed), saleable application flavors in the chosen AZ | READ | [ListSupabaseApplicationFlavors](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplicationFlavors) |
| `plan_supabase_creation` | Pre-creation planning: staged resource preparation checklist and operation flow | READ | - |
| `list_supabase_flavors_with_azs` | Query application flavors with the AZ list each flavor supports, for sizing and AZ selection | READ | [ListSupabaseApplicationFlavors](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplicationFlavors) |
| `list_supabase_manageable_instances` | Query existing PostgreSQL instances available for attachment | READ | [ListSupabaseManageableInstances](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseManageableInstances) |
| `list_db_instance_engine_versions` | Query PostgreSQL engine versions for managed instances | READ | [ListDatastores](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListDatastores) |
| `list_db_instance_flavors_with_azs` | Query managed-instance flavors with per-AZ sale status | READ | [ListFlavors](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListFlavors) |
| `list_db_instance_storage_types` | Query managed-instance storage types by engine version and deployment mode | READ | [ListStorageTypes](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListStorageTypes) |
| `discover_db_instance_create_options` | One-call discovery for the new-instance scenario: engine versions, flavors, storage, and per-field recommended configuration (network and security groups out of scope, guided separately) | READ | composite query (ListDatastores/ListFlavors/ListStorageTypes) |
| `discover_available_network_for_create` | Auto-discover a VPC and subnet with sufficient free IPs (prefer 2, fall back to 1), yielding the basic_config vpc_id/subnet_id directly; with no usable network in the region, returns the default recommendation (default_vpc 192.168.0.0/16 + default_subnet 192.168.0.0/24) | READ | [ListVpcs](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ListVpcs) + [ListSubnets](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ListSubnets) |
| `create_supabase_application` | Create a Supabase application with a new or existing instance; each scenario returns its own job combination | DANGEROUS | [CreateSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=CreateSupabaseApplication) |
| `delete_supabase_application` | Delete the application; on the user's choice also delete the managed database instance, two deletions with separate job ids | DANGEROUS | [DeleteSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=DeleteSupabaseApplication) |
| `delete_supabase_managed_instance` | Delete the managed database instance - irreversible; verifies the managed binding and shared references layer by layer to prevent wrong deletion | DANGEROUS | [DeleteInstance](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=DeleteInstance) |
| `get_supabase_order` | Query a prepaid order's status, amounts, currency and line items | READ | [ShowCustomerOrderDetails](https://console.huaweicloud.com/apiexplorer/#/openapi/BSS/doc?api=ShowCustomerOrderDetails) |
| `pay_supabase_order` | Complete a balance payment for the approved order, amount and currency to start prepaid delivery | DANGEROUS | [PayOrders](https://console.huaweicloud.com/apiexplorer/#/openapi/BSS/doc?api=PayOrders) |
| `cancel_supabase_order` | Abandon an unneeded pending-payment order | DANGEROUS | [CancelCustomerOrder](https://console.huaweicloud.com/apiexplorer/#/openapi/BSS/doc?api=CancelCustomerOrder) |
| `change_supabase_ssl` | Enable or disable SSL-encrypted transport for the application | WRITE | [SwitchSupabaseApplicationSsl](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=SwitchSupabaseApplicationSsl) |
| `plan_supabase_ssl` | Pre-switch planning: certificate requirements and impact assessment | READ | - |
| `change_supabase_eip` | Bind or unbind an elastic public IP to open or close public access | WRITE | [SwitchSupabaseApplicationEipBind](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=SwitchSupabaseApplicationEipBind) |
| `change_supabase_application_password` | Change the application password; the new password is supplied via the local request file, never through conversation | DANGEROUS | [ModifySupabaseApplicationPassword](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationPassword) |
| `list_supabase_security_groups` | Browse security groups | READ | [ListSecurityGroups](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ListSecurityGroups) |
| `show_supabase_security_group` | Inspect a security group and all its rules | READ | [ShowSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ShowSecurityGroup) |
| `create_supabase_security_group` | Create a dedicated security group, auto-tagged with origin and purpose | WRITE | [CreateSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=CreateSecurityGroup) |
| `add_supabase_security_group_rule` | Add one inbound or outbound access rule, sized to the actual deployment ports | DANGEROUS | [CreateSecurityGroupRule](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=CreateSecurityGroupRule) |
| `delete_supabase_security_group_rule` | Remove a specific access rule to narrow the exposed surface | DANGEROUS | [DeleteSecurityGroupRule](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=DeleteSecurityGroupRule) |
| `delete_supabase_security_group` | Delete an entire security group with all its rules; only flow-created, unreferenced groups | DANGEROUS | [DeleteSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=DeleteSecurityGroup) |
| `show_operation_job_status` | Query the current status of a submitted operation task | READ | [ListJobInfo](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListJobInfo) |
| `show_supabase_creation_progress` | Analyze end-to-end creation progress: instance creating, application waiting, application creating, succeeded or failed | READ | - |
| `wait_operation_job_complete` | Poll an operation task to a terminal state within a bounded timeout | READ | [ListJobInfo](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListJobInfo) |

The full API reference is at the [Huawei Cloud RDS API docs](https://support.huaweicloud.com/api-rds/rds_01_0002.html); some Supabase APIs are newer than the published catalog - when API Explorer lacks one, this server's actual behavior is authoritative.

## Security-group tools and the KooCLI division of labor

The six security-group tools (queries, group create/delete, rule add/remove)
**already wrap the KooCLI capability and work out of the box** - the agent
does not need to run hcloud separately: the tools invoke the VPC v3
operations internally with credential injection and result parsing, plus
preview confirmation, origin tagging, and wrong-deletion protection.

**Principle: prefer the tools; fall back to raw KooCLI only when they do
not cover the need.**

| Scenario | Use |
|---|---|
| Every routine security-group operation (list/detail, create group, add/remove rules, delete group) | **This service's tools** |
| Opening 0.0.0.0/0 world-wide ingress (tools refuse by design; requires explicit user confirmation) | Raw KooCLI commands |
| Edge operations the tools deliberately do not support (e.g. address-group management) | Raw KooCLI commands |

Internal implementation (relevant for operations troubleshooting only):

- The native RDS origin does not proxy the VPC API; the tools call VPC v3
  operations (`CreateSecurityGroup/v3`, `CreateSecurityGroupRule/v3`, ...)
  through the local KooCLI (`hcloud`).
- **KooCLI prerequisite**: hcloud installed locally with its first-run
  privacy agreement accepted. Installation: section 4 of the skill
  [INSTALL.md](../../skills/huaweicloud-supabase/rds-supabase-mgr-mcp/INSTALL.md).
- **Binary location**: `HCLOUD_BIN` environment variable → fixed install
  directories → PATH, re-resolved on every call; no session restart needed
  after installation.
- **Credential injection**: injected per command only when both
  `HUAWEICLOUD_ACCESS_KEY` and `HUAWEICLOUD_SECRET_KEY` are set; otherwise
  the hcloud profile is used. **REST token mode requires a local hcloud
  profile** (`hcloud configure init`), or these tools report missing
  credentials.
- **Region and project**: region comes from `HUAWEICLOUD_REGION`; the
  project is resolved by KooCLI as the region default project —
  sub-project accounts must configure `--cli-project-id` in the hcloud
  profile.
- **Error passthrough**: VPC backend error_code/error_msg/request_id pass
  through verbatim; an unaccepted privacy agreement, a missing binary, and
  timeouts each map to a dedicated error code with remediation guidance.
- **Origin tagging**: every created group is auto-tagged AUTO_CREATE=true
  and USE_FOR=Supabase; whole-group deletion verifies the tag pair and
  rejects every group not created by this flow, preventing wrong deletion.

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
| `SUPABASE_RDS_ENDPOINT` | no | Native RDS HTTPS origin (no path/query/userinfo; not the Console or a /rest proxy). When absent, derived from `HUAWEICLOUD_REGION` as `https://rds.<region>.myhuaweicloud.com`; also derivable via `diagnostics discover` | derived per region |
| `HUAWEICLOUD_PROJECT_ID` | no | Target project ID; discovered via IAM from `HUAWEICLOUD_REGION` when absent (AK/SK with project-list permission required; sub-project accounts should set it explicitly) | IAM discovery |
| `HUAWEICLOUD_AUTH_TOKEN` | REST mode | Pre-provisioned service token, read per request | - |
| `SUPABASE_TRANSPORT` | no | Set `sdk_core` to enable Huawei SDK Core signing | REST token |
| `HUAWEICLOUD_ACCESS_KEY` | sdk_core mode | Account AK | - |
| `HUAWEICLOUD_SECRET_KEY` | sdk_core mode | Account SK | - |
| `HUAWEICLOUD_SECURITY_TOKEN` | no | STS temporary-credential token | - |
| `HUAWEICLOUD_REGION` | no | Region: shared by the security-group tools and RDS endpoint derivation; sub-project resolution stays with the hcloud profile | - |
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
- **Local execution record**: SQLite records every plan and execution
  state. On a timeout or unknown outcome, verify directly against the
  operation task and the target resource; no submitted plan may be
  resubmitted, preventing double execution.
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
4. Track the returned `job_id` with `show_operation_job_status` (or bounded
   `wait_operation_job_complete`) to a terminal state.
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

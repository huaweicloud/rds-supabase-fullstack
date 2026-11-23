# Huawei Cloud RDS Supabase MCP Server

[中文](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/README.md)

## Version

Current version: `0.4.0`; Python `3.10+`;
MCP Python SDK `2.x`; 58 tools.

## Overview

This server wraps the full lifecycle management of Huawei Cloud RDS Supabase
applications as MCP tools, covering creation arrangement and scenario-based
creation (two managed-instance sources), network and security-group
specification, EIP provisioning and binding, SSL certificate query and
purchase, OBS storage integration,
authentication and login configuration, API key delivery, prepaid orders,
application and managed-instance start/stop/restart, security-group
binding changes, routine changes, and deletion. It serves AgentArts and other MCP clients; the REST-token
and SDK credential modes, over stdio and Streamable HTTP, share one tool set,
one set of safety guardrails, and one output protocol. It is read-only by
default: every write runs a preview/confirm two-phase flow, and sensitive
fields travel through a local request file, never through conversation.
Discovery and arrangement results carry chart-rendered output (visual) for
direct inspection. The companion skill
`skills/huaweicloud-supabase/rds-supabase-mgr-mcp` provides scenario-based
operational guidance. This server covers the control plane only and performs
no SQL or data operations; the data plane is a separate service,
`server/mcp_server_rds_supabase`, delivered separately — neither substitutes
for the other.

## Quick start

Prepare Python 3.10+, [uv](https://docs.astral.sh/uv/), and Huawei Cloud
credentials. The minimal configuration is three variables:
`HUAWEICLOUD_ACCESS_KEY`, `HUAWEICLOUD_SECRET_KEY`, and `HUAWEICLOUD_REGION`
(pair with `SUPABASE_TRANSPORT=sdk_core` to enable SDK signing); the project
ID is discovered through IAM and the RDS endpoint is derived from the region.
Stay read-only on first contact:

```bash
export HUAWEICLOUD_ACCESS_KEY="<AK>"
export HUAWEICLOUD_SECRET_KEY="<SK>"
export HUAWEICLOUD_REGION="<region, e.g. cn-north-4>"
export SUPABASE_TRANSPORT="sdk_core"
export HUAWEICLOUD_MCP_READ_ONLY="true"
uvx mcp-server-huaweicloud-rds-supabase-mgr
```

Generic stdio client configuration (token mode; AK/SK mode see
[examples/mcp-sdk.example.json](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/examples/mcp-sdk.example.json)):

```json
{
  "mcpServers": {
    "rds-supabase-mgr-mcp": {
      "command": "uvx",
      "args": ["mcp-server-huaweicloud-rds-supabase-mgr"],
      "env": {
        "HUAWEICLOUD_AUTH_TOKEN": "<service token>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

Once connected, first call `get_supabase_capabilities` to verify the endpoint,
permissions, and project, then run `plan_supabase_creation_arrangement` to
produce the creation arrangement baseline. Full installation, credential
modes, and the security-group prerequisites are covered below.

## Category

Cloud resource management / application lifecycle orchestration /
database hosting.

## Feature overview

- **Arrangement and discovery**
  - Creation arrangement baseline: two managed-instance decisions, three mandatory modules consolidated live, SSL and public-access (EIP) as independent modules, step-numbered creation flow
  - Flavor discovery: every saleable spec grouped by group_type (ten official classes); application and instance flavors asked separately, instance default matching the application's spec
  - Disk types: Chinese labels, official constraints, and live compatibility lists
  - Four discovery families (application, instance, network, security group) consolidating parameters live with recommendations
- **Scenario-based creation**: two scenario tools — create with a new instance (recommended) or by attaching an existing one; dedicated security groups and the OBS bucket auto-prepared, parameters backfilled and injected, one submission. The request file must NOT carry security_group_id (top-level or managed_instance) - presence is rejected with a removal hint; to use your own groups, rebind with change_supabase_security_group after creation
- **Network and security groups**
  - VPC/subnet placement: free-IP preference, default recommendation when no network exists
  - Dedicated group creation and rules, dual-tag protection (AUTO_CREATE/USE_FOR), three-way ingress source choice
  - Security-group rebinding: three targets (application / managed instance / attachable instance), multiple groups with full-replacement semantics
- **EIP**: idle-first provisioning (pay-per-use, dedicated full-dynamic BGP bandwidth); binding with triple validation (in32 application ID, ownership, format)
- **SSL certificates**
  - Account certificate inventory (SCM global service)
  - Two-phase purchase and application: free-tier DV_SSL_CERT_BASIC recommended; pure-EIP public-IP certificates support file validation only
  - SSL switch changes
- **OBS storage**: reuse / create-new options; fixed private-bucket specification (standard / multi-AZ / block-public-access); temporary-credential detection and a read test
- **Authentication and login**: sign-up toggles, email/GitHub login, confirmation templates; application password change (application login password only — the managed-instance root password is out of scope)
- **Key delivery**: key metadata query, reset, and protected local-file delivery — key values never enter conversation
- **Orders**: prepaid order query, balance payment, and cancellation with amount and currency verified item by item
- **Application lifecycle**
  - Start (does not start the managed instance), stop (does not stop the instance, which keeps billing), restart (brief interruption, off-peak advised)
  - Status guardrails; asynchronous tasks tracked to terminal state via `show_operation_job_status`
- **Managed-instance lifecycle**
  - Detail query: engine/version/status/flavor/disk/AZ/in-progress actions, with billing and the fifteen-day auto-start note
  - Target strictly resolved from the application's `managed_instance`; bare `instance_id` never accepted, preventing operations on standalone instances
  - Stop for pay-per-use instances only (VM stops billing, EIP/storage/backup continue); start the instance before the application
- **Change and deletion**: SSL, EIP, and storage-integration changes; application deletion (optional managed-instance cascade) and standalone managed-instance teardown
- **Safety and experience**: read-only mode with risk grading, sensitive-field redaction, JSONL audit, chart-rendered output, four-layer wrong-deletion verification

## Business scenarios

### Scenario 1: Pre-creation preparation

Pre-creation preparation is completed in one call of
`plan_supabase_creation_arrangement`; it plans only and creates no resource. It first presents the two managed-instance
sources and requires a definitive conclusion from the user: a new instance is
the recommended default, attaching an existing instance the alternative. It
then consolidates the key parameter modules live - three mandatory modules and
one key optional module:

- **Supabase basics**: name suggestion and naming rules, version, deployment
  mode, and flavor (all saleable flavors selectable or custom, general 2U4G
  recommended), from `discover_supabase_create_basic_options`.
- **Managed instance**: the new-instance source returns per-field
  recommendations for engine version, flavor, and storage via
  `discover_db_instance_for_create` — the application flavor and the instance
  flavor are asked in two separate interactions: instance flavors are grouped
  by group_type into ten categories with all saleable flavors shown and the
  application's flavor recommended by default, and storage types display
  their Chinese name, official note, and live compatible flavor types for
  selection; the attach source lists attachable instances paginated (20 per
  page) with version, deployment type, port, availability zone, creation
  time, and current action (action lock) — instances being restarted,
  upgraded, or changed must be excluded to avoid task conflicts.
- **Network control**: VPC/subnet placement and the two-group security-group
  specification — application group 8443 ingress three-way choice plus 5432
  egress, database group 5432 ingress, all CIDRs from the chosen subnet, from
  `discover_network_for_create`.
- **OBS bucket storage integration (key optional)**: whether large-file
  storage applies (images, videos, large files) must be answered explicitly —
  enabling it at creation time is strongly recommended (avoids omissions and
  longer flows; apps created without it can integrate storage afterwards via
  `update_supabase_storage`, which requires the full credentials - bucket
  name plus AK/SK - on first integration). Once confirmed, the module carries
  the reuse/new choice (existing-bucket list with **private buckets first**),
  the complete new-bucket specification, and the temporary-credential notice,
  submitted once with the creation request.

The arrangement also emits two independent intent modules: **public access (EIP)**
carries the purchase baseline (pay-per-use, dedicated full-dynamic BGP bandwidth
on-demand billing fixed (no prepaid periods) with full-dynamic BGP dedicated bandwidth - the **billing method is chosen by the user per scenario** (bandwidth-based or traffic-based, traffic mode capped at a 300 Mbps peak per EIP) and the **bandwidth size is decided by the user**; the fee schedule is shown before purchase: bandwidth/traffic fee plus IP retention fee, official examples 6Mbps ~0.565 CNY/hour / 0.64 CNY/GB / 0.02 CNY/hour retention, exact unit prices per the official pricing details), the binding, and the `api_external_url` sync steps;
**SSL configuration** carries the three certificate acquisition paths — reuse an
existing certificate (`list_ssl_certificates` inventory), purchase a new one
(`purchase_supabase_ssl_cert`, recommended; free-tier DV_SSL_CERT_BASIC, paid
tiers produce pending-payment orders), or import your own. Pure-EIP public-IP
certificates support file validation only. The output
is a step-numbered creation flow plus a post-creation action list, to be
followed 1:1 during creation.

### Scenario 2: Full application creation flow

**Passwords and dashboard login**: the password follows the cloud rule (8-32
characters, at least three classes); the strong recommendation is 12-16
characters of upper + lower case letters and digits with **no special
characters** (use only `-`/`_` if a symbol is required), avoiding IME,
URL/JSON escaping and transcription problems - the preview warns when a
password carries characters beyond letters/digits/`-`/`_`. The creation path
never generates or alters the password: the dashboard login user is fixed
`supabase` and the password is exactly the local request file's
`create.password`; the accepted response carries a `dashboard_credential`
note - on login failure verify the file first, and change the password via
`change_supabase_application_password`.

Both managed-instance sources share one discipline: intents first, parameters
consolidated through the arrangement, sensitive fields only in the local
request file, and a preview/confirm two-phase submission. The creation tool
completes the resource preparation automatically (dedicated security groups
and, when storage is enabled, the OBS bucket) and backfills every prepared
identifier into the request before one successful submission.

#### New-instance scenario (recommended, `create_supabase_with_new_instance`)

1. Confirm the intents: managed-instance source is a new instance; large-file
   storage or not (decide at creation time whenever possible; storage can be
   integrated afterwards via `update_supabase_storage`), public access or
   not, HTTPS or not.
2. Produce the arrangement baseline (Scenario 1); `az_code` triggers live
   discovery, and with no VPC the default recommendation applies with the
   network created per `default_create`.
3. Assemble the local request file: all parameters and sensitive fields
   (application password, database password, storage AK/SK) go into the file
   only, never into conversation.
4. Preview (`request_ref`, `public_access_cidr`, `confirm=false`): resolves
   the three-way ingress choice and returns a `plan_id`.
5. Confirm and submit (`confirm=true` + `plan_id`): the application group and
   the database group are created automatically; with storage enabled, the
   OBS bucket is ensured to exist (existing reused, missing created, short
   uuid appended on global-name collision); everything is backfilled and
   injected before one submission.
6. application_id/instance_id and both workflow IDs are echoed; keep
   querying via `show_supabase_creation_progress`: roughly 20-30 minutes
   overall, the instance becomes ready first and only then does the
   application task start.
7. Verify readiness with `show_supabase_application`; then proceed as needed
   with public access (Scenario 3), SSL (three certificate paths: reuse /
   purchase / import your own), login configuration, and access
   information delivery.

#### Existing-instance attach scenario (`create_supabase_link_exist_instance`)

1. Confirm the intents as above, with the managed-instance source being an
   existing instance.
2. The arrangement lists the attachable candidates paginated at 20 per page
   with version, deployment type, port, availability zones, creation time and
   current action locks - after excluding instances mid-restart, upgrade or
   change, the user picks the `instance_id` and backfills the arrangement.
3. Assemble the local request file: `manage_type=existed_instance` and
   `existing_instance{instance_id, database_name:"root", database_pwd}`;
   the database password goes into the file only.
4. Preview and submit: the application group is created automatically (8443
   ingress with the three-way choice plus 5432 egress to the instance's
   subnet CIDR) while the instance's own security group stays untouched;
   with storage enabled the OBS bucket is ensured likewise; backfilled and
   injected before one submission.
5. application_id and the application workflow ID are echoed (no instance
   task); track to readiness via `show_supabase_creation_progress`.
6. Verification and post-creation actions match the new-instance scenario.

### Scenario 3: EIP creation and binding

**Provisioning**: `create_supabase_eip` is idle-first
(`prefer_idle=true`) — it first lists unbound EIPs for the user to pick,
and the selection binds directly with nothing created; with no idle EIP, it
creates per the baseline: on-demand billing fixed (no prepaid periods),
full-dynamic BGP (`publicip.type=5_bgp`), dedicated bandwidth
(`share_type=PER`) on-demand billing fixed - the billing method (bandwidth-based or traffic-based, no default, chosen by the user per scenario) and the size (bandwidth 5-1000 / traffic 5-300 peak cap) are both user decisions; the fee schedule is shown and confirmed before purchase, auto-tagged USAGE_FOR. When the submission response is lost, the tool reconciles first (baseline set-difference + attribute matching): a confirmed creation returns the real result (`reconciliation.verified`), a verified absence reports `verified_absent`, several new candidates report `ambiguous_candidates` (never auto-claimed), and only an unreadable reconciliation falls back to `submission_unknown`; a failed tag write degrades to `tag_warning` without affecting the creation result.

**Binding (first time)**: `bind_supabase_eip` runs triple validation — `instance_id` must
be an in32-suffixed Supabase application ID that actually exists (verified against the
application detail endpoint), `public_ip_id` a canonical UUID, and `public_ip` a valid
IPv4; only a running application with no in-flight actions and no EIP bound yet can be
bound here, submitted through the application-level public-eip endpoint
(SwitchSupabaseApplicationEipBind). Swapping or unbinding an already-bound application
belongs to `change_supabase_eip`.

After a successful binding, `update_supabase_auth_config` must sync
`api_external_url` (email links and OAuth callbacks depend on it), followed
by a liveness check.

When HTTPS is needed, SSL certificates are obtained through this server — no
console purchase required: `list_ssl_certificates` inventories existing
account certificates (the SCM global service) for reuse; and
`purchase_supabase_ssl_cert` purchases and applies in two phases — free-tier
DV_SSL_CERT_BASIC recommended, paid tiers producing pending-payment orders,
pure-EIP public-IP certificates supporting file validation only. Once the
`cert_id` is at hand, enable it via `change_supabase_ssl`.

### Scenario 4: Application and managed-instance operations

Day-to-day operations after launch — application start/stop/restart,
managed-instance detail and start/stop/restart, security-group rebinding,
password change, key reset, and SSL switching — share one rhythm:
**verify before acting** (`show_supabase_application` or
`show_supabase_managed_instance` to confirm the target state and any
in-progress actions; guardrails reject mismatched states and the rejection is
relayed verbatim) → **two-phase submission** (preview with `confirm=false` for
a `plan_id`, then one confirmed submission) → **job tracking** (the accepted
`job_id`/`workflowId` is tracked to a terminal state via
`show_operation_job_status`) → **re-verification** (a read-only re-read of the
resource). Start/stop/restart briefly affects availability — prefer off-peak
windows.

#### Application start/stop/restart

`start_supabase_application` accepts stopped applications only and does not
start the managed instance automatically (an unhealthy instance may fail the
start); `stop_supabase_application` accepts running applications only, with
features unavailable while stopped, the managed instance not stopped and still
billing; `restart_supabase_application` accepts running applications only,
briefly interrupting the service and clearing the memory cache; stopped
applications must start first.

#### Managed-instance detail and start/stop/restart

`show_supabase_managed_instance` and the three start/stop/restart tools all
take `application_id`; the target instance is strictly resolved from the
application's `managed_instance` field — a bare `instance_id` is never
accepted, preventing operations on standalone database instances. The detail
query returns engine/version/instance_status semantics/flavor/disk/AZ/
in-progress actions, with billing and fifteen-day auto-start notes. Stop
accepts normal, action-free pay-per-use instances on ultra-high-IO/SSD cloud
disk/ESSD storage only (dedicated clouds unsupported): the VM stops billing
while EIP/storage/backup keep billing; if not started again within fifteen
days, the instance auto-starts in the maintenance window; a stopped instance
is deleted without the recycle bin; stopping the primary also stops its read
replicas. Start accepts shutdown instances only and may fail on insufficient
resources; restart accepts normal, unfrozen, action-free instances only, with
the instance unavailable during restart. **Start the instance first, then the
application** — starting the application does not pull the instance up
automatically.

#### Security-group rebinding

`change_supabase_security_group` serves three targets (the application
itself, its managed instance, and the attachable instance of the
attach-existing scenario) with **full-list replacement** semantics — the given
list is the final list, unlisted groups are detached, and keep-needed groups
must be listed; removing the group carrying the 8443/5432 allowance makes the
application unreachable. Instances in creation, database upgrade, flavor
change, or user creation/deletion states cannot be set. This tool decides
which groups are bound; rule add/remove within a group stays with
`add_supabase_security_group_rule` / `delete_supabase_security_group_rule`.
The accepted workflowId is tracked via `show_operation_job_status`.

#### Password change and key reset

`change_supabase_application_password` changes the **application login
password** only (dashboard user supabase); the managed-instance root login
password is out of this tool's scope — instance passwords are changed via
console instance management; old-password sessions are invalidated; the new
password travels through the local request file, never conversation.
`reset_supabase_api_key` resets a given key (asynchronous): the old key fades
out and the new key is a new record, delivered again via
`deliver_supabase_api_key`; warn downstream consumers in advance.

#### SSL switching

`change_supabase_ssl` requires a certificate ID to enable (three acquisition
paths per Scenario 3) and must carry none to disable; the switch briefly drops
connections — off-peak recommended, with a reminder to sync callback URL
protocols afterwards. EIP bind/unbind, storage-bucket rotation, sign-up
toggles, and other routine changes follow the same rhythm above.

### Scenario 5: Application deletion (with the managed PG instance)

`delete_supabase_application`'s `delete_managed_instance` is mandatory:
`false` deletes only the application, with the managed instance retained and
still billing; `true` deletes both concurrently — instance deletion is
irreversible and cascade applies to pay-per-use only. Four verification
layers run before submission (while the application stays readable):
instance ownership, live re-check of the cloud `managed_instance` state, no
other application mounting the instance, and a **billing-mode gate** —
yearly/monthly (prepaid) instances do not support API deletion (including
prepaid PG instances linked in the attach-existing scenario): `true` is
rejected as a whole (the application is not deleted); re-issue with `false`
and unsubscribe the instance in the console (fee center -> unsubscribe
management). A missing `charge_info` fails closed too. Submission returns
two job IDs; track them to a terminal state with
`wait_operation_job_complete` and re-verify the resources.

The managed instance can also be torn down standalone via
`delete_supabase_managed_instance` while the application lives, under the
same four verification layers (the billing-mode gate applies here too: only
pay-per-use instances can be deleted directly; prepaid instances are
unsubscribed console-side). Auto-created security groups are cleaned up
via `delete_supabase_security_group` behind the tag gate: only groups bearing
the `AUTO_CREATE=true`/`USE_FOR=Supabase` tag pair and free of references
may be deleted.

### Scenario 5 supplement: post-deletion resource cleanup (explicit or linked)

Three dedicated cleanup tools follow the application deletion, each two-phase
with live verification before submission:

- **EIP**: `delete_supabase_eip` (KooCLI EIP DeletePublicip) - reads the EIP to
  verify identity, optionally cross-checks the address, and sweeps the full
  application inventory to block an EIP still referenced by a live
  application's public address; a bound EIP is rejected by the backend itself
  (unbind first via `change_supabase_eip` with `is_bind=false`); deletion
  stops the IP retention fee immediately.
- **Application data directory**: `clean_supabase_obs_ws` (KooCLI embedded
  obsutil) - the deletion scope is strictly confined to the bucket-root
  folder named exactly the application ID (`obs://<bucket>/<application_id>/`);
  the bucket and every other directory stay untouched (the prefix is built
  solely from the validated bucket name and the in32-format application ID,
  with no caller-supplied path fragment); a still-live application ID is
  blocked (delete the application first); a missing or empty folder returns
  `already_clean` idempotently.
- **OBS bucket**: `delete_supabase_obs` (obsutil rm) - blocks while any live
  application's `storage_component` still references the bucket, and blocks
  non-empty buckets (clear each application directory with
  `clean_supabase_obs_ws` first, review anything else manually); a missing
  bucket returns `already_absent` idempotently.

### Scenario 6: Purchase modes

The RDS Supabase application is free during public beta; charges arise only
from the managed instance. The billing mode is fixed to on-demand in
`managed_instance.charge_info` of the creation request.

#### Billing boundary (application free, instance charged)

- **The application itself**: free during public beta, no charge.
- **The managed instance**: the only billing subject - **fixed on-demand
  billing** (creation supports `postPaid` only, no prepaid periods): the
  billable items are the instance flavor and storage space (both mandatory)
  plus backup space beyond the free allowance (100% of the purchased
  storage), with public bandwidth / cross-region backup as optional items;
  billed per second and settled hourly, from the moment the instance is
  created successfully until it is deleted (billing rules:
  https://support.huaweicloud.com/price-rds-pg/rds_00_0005.html ).
- With on-demand billing fixed, creation no longer produces payable orders;
  the order tools (`get`/`pay`/`cancel`) remain for prepaid orders created
  console-side (e.g. existing instances).

#### Billing-mode presentation (fixed on-demand)

- **The managed instance is on-demand (postPaid) fixed**: `charge_info`
  carries `charge_mode` only; prepaid periods are not supported. Show the
  billing rules and the fee composition to the user before submission (the
  discovery and arrangement outputs carry the same notice) and obtain
  explicit approval.

#### Prepaid order payment (console-side legacy orders)

1. Once the creation returns `order_id`, first query the order status,
   amounts, currency and lines with `get_supabase_order(order_id)` (20 lines
   by default, `marker` pagination); `amount_after_discount` is the
   post-discount amount excluding coupons and cards, and amounts must be read
   together with the returned currency and unit.
2. After verifying and obtaining the user's approval of the exact amount and
   currency, call `pay_supabase_order(order_id, expected_amount, currency,
   confirm=true)`: `expected_amount` must equal both `official_amount` and
   `amount_after_discount` - a difference means a discount or coupon exists,
   and the tool rejects the payment to avoid losing it; such orders are
   handled in the billing center. For managed accounts the final charge
   follows the bill.
3. One confirmation, one submission, no automatic retry; the result carries
   `payment_submitted` and `payment_verified`, and the order status and
   payment time are re-checked after payment. Timeouts may leave the outcome
   unknown (`payment_submitted=false`): query the same order first and never
   pay automatically again.
4. Once the payment completes and the order provisions, a creation task
   appears - track and verify per Scenario 2.

#### Prepaid order cancellation

1. To abandon an unpaid order: confirm it accurately with `get_supabase_order`
   first, then `cancel_supabase_order(order_id, confirm=true)`.
2. The service re-checks the cloud-side pending-payment state, product scope
   and every order line; only unpaid orders qualify; cancellation is
   permanent; already-cancelled orders return an idempotent result.
3. The result carries `cancellation_verified`; when false, keep querying with
   `get_supabase_order` instead of blindly resubmitting. Paid resources must
   go through the console unsubscription workflow, which this tool does not
   handle.

### Scenario 7: Resource cleanup and retention

Decommissioning when the full Supabase capability is no longer needed: after the
application deletion (the PG-instance choice stays mandatory - the
create-with-new-instance scenario recommends deleting the instance together to
avoid residuals), the associated resources are cleaned up behind explicit
confirmation. **Full-flow protection mechanism (resource ledger)**: every
create/reuse/bind/modify step this MCP performs is recorded in a local resource
ledger (EIP auto-created vs reused, OBS bucket auto-created vs integrated, the
two dedicated security groups, the application-to-managed-instance mapping, and
the instance choice at deletion) so cleanup and linked operations are scoped
precisely - never guessed.

**Entry**: `show_supabase_residuals(application_id)` (READ) - ledger-scoped,
live-verified residual inventory across the four categories with per-item
recommendations: EIP (existence, address, auto-created ones recommended for
deletion, reused ones left to the user), OBS bucket (existence, deletion
recommendation), the application data directory `obs://<bucket>/<appid>/`
(object count; **high-risk reminder when the bucket is retained: stored data
bills continuously - cleanup strongly recommended**), security groups
(application vs database role; **the database group is undeletable while the
instance is retained**); plus the managed-instance state and the one-click
description. A missing ledger record is refused honestly (resources created
before the mechanism need manual review via the single-item tools).

**One-click cleanup**: `cleanup_supabase_residuals(application_id, cleanup_eip,
cleanup_obs_bucket, cleanup_obs_workspace, cleanup_security_groups, confirm,
plan_id)` (DANGEROUS) - the four category switches are mandatory booleans (all
True cleans everything the inventory listed; declining means per-category
confirmation through the single-item tools). The preview carries the live
residual inventory and per-category warnings (including the high-risk
storage-billing reminder for retained buckets); one confirmation, one plan:
per-item guard re-checks (live references, non-empty buckets, live application
directories, the tag gate), blocked items skipped with honest reasons (e.g. the
database group while the instance is retained), failures never abort the other
categories; the ledger is updated for every cleaned item. Re-run
`show_supabase_residuals` afterwards to verify.

**Confirmation discipline**: EIP and OBS buckets are deleted only behind the
user's explicit confirmation, with auto-created ones recommended for deletion
(avoiding residuals and continuous billing); a retained bucket must surface the
storage-occupancy reminder (high risk: continuous billing - strongly
recommended to clear the application directory); auto-created security groups
are recommended for deletion, the database group blocked while the instance is
retained; security-group rebinding keeps the ledger in sync (removed
auto-created groups become unbound residuals).

**Single-item tools** (partial cleanup): `delete_supabase_eip`,
`delete_supabase_obs`, `clean_supabase_obs_ws`,
`delete_supabase_security_group` (scenario 5 supplement).

## Available tools

Every write tool runs a two-phase confirmation: a preview returns the changes
and a plan identifier first, and only an explicit confirmation submits. Tools
that carry passwords or credentials accept no plaintext — secrets are
pre-provisioned into a local request file and referenced by alias.

| Tool | Scenario | Risk | API doc |
|---|---|---|---|
| `get_supabase_capabilities` | Service capability and scope declaration | READ | - |
| `list_supabase_applications` | Browse applications with filters | READ | [ListSupabaseApplications](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplications) |
| `show_supabase_application` | Application details and access materials | READ | [ShowSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ShowSupabaseApplication) |
| `list_supabase_api_keys` | Key metadata, never values | READ | [ListSupabaseApplicationApiKeys](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplicationApiKeys) |
| `reset_supabase_api_key` | Reset a key for rotation | DANGEROUS | [ResetSupabaseApplicationApiKey](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ResetSupabaseApplicationApiKey) |
| `deliver_supabase_api_key` | Deliver key to protected local file | DANGEROUS | [ShowSupabaseApplicationApiKeyValue](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ShowSupabaseApplicationApiKeyValue) |
| `show_supabase_auth_config` | Auth configuration baseline | READ | [ShowSupabaseApplicationAuthConfig](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ShowSupabaseApplicationAuthConfig) |
| `update_supabase_auth_flags` | Toggle sign-up and anonymous access | WRITE | [ModifySupabaseApplicationAuthConfig](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationAuthConfig) |
| `update_supabase_auth_config` | Email/GitHub login and templates | WRITE | [ModifySupabaseApplicationAuthConfig](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationAuthConfig) |
| `update_supabase_storage` | Attach or rotate OBS storage | WRITE | [ModifySupabaseApplicationStorage](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationStorage) |
| `discover_supabase_storage` | OBS options and credential checks | READ | `KooCLI OBS ls` |
| `discover_supabase_create_basic_options` | App basics with grouped flavors | READ | [ListSupabaseApplicationFlavors](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplicationFlavors) |
| `plan_supabase_creation_arrangement` | End-to-end creation arrangement baseline | READ | live composite (read-only queries of the three discovery tools) |
| `list_supabase_flavors_with_azs` | App flavors and AZ availability | READ | [ListSupabaseApplicationFlavors](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseApplicationFlavors) |
| `list_supabase_manageable_instances` | Attachable PostgreSQL instances | READ | [ListSupabaseManageableInstances](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSupabaseManageableInstances) |
| `list_db_instance_engine_versions` | Managed-instance engine versions | READ | [ListDatastores](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListDatastores) |
| `list_db_instance_flavors_with_azs` | Instance flavors and AZ status | READ | [ListFlavors](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListFlavors) |
| `list_db_instance_storage_types` | Disk types and compatibility | READ | [ListStorageTypes](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListStorageTypes) |
| `discover_db_instance_for_create` | Instance discovery with grouped flavors | READ | composite query (ListDatastores/ListFlavors/ListStorageTypes) + ListManageableInstances |
| `discover_network_for_create` | Network placement and group specs | READ | [ListVpcs](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ListVpcs) + [ListSubnets](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ListSubnets) |
| `create_supabase_with_new_instance` | Create with new instance (recommended) | WRITE | [CreateSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=CreateSupabaseApplication) |
| `create_supabase_link_exist_instance` | Create by attaching an instance | WRITE | [CreateSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=CreateSupabaseApplication) |
| `delete_supabase_application` | Delete app; instance choice required | DANGEROUS | [DeleteSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=DeleteSupabaseApplication) |
| `delete_supabase_managed_instance` | Remove the managed instance alone | DANGEROUS | [DeleteInstance](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=DeleteInstance) |
| `delete_supabase_eip` | Delete the EIP, post-deletion cleanup | DANGEROUS | [DeletePublicip](https://console.huaweicloud.com/apiexplorer/#/openapi/EIP/doc?api=DeletePublicip) (KooCLI) |
| `clean_supabase_obs_ws` | Empty and delete the application-ID folder at the bucket root | DANGEROUS | KooCLI `hcloud OBS rm` (folder-level, emptied then removed) |
| `delete_supabase_obs` | Delete the OBS bucket | DANGEROUS | KooCLI `hcloud OBS rm` (bucket) |
| `show_supabase_residuals` | Residual inventory (ledger + live checks, scenario 7 entry) | READ | ledger + EIP/OBS/VPC/RDS reads |
| `cleanup_supabase_residuals` | One-click cleanup of four residual categories (mandatory booleans) | DANGEROUS | ledger + EIP/OBS/VPC deletions |
| `start_supabase_application` | Start a stopped application | DANGEROUS | [StartSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=StartSupabaseApplication) |
| `stop_supabase_application` | Stop app; instance keeps billing | DANGEROUS | [StopSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=StopSupabaseApplication) |
| `restart_supabase_application` | Restart a running application | DANGEROUS | [RestartSupabaseApplication](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=RestartSupabaseApplication) |
| `show_supabase_managed_instance` | Managed-instance detail and status | READ | [ListSimplifiedInstances](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListSimplifiedInstances) |
| `stop_supabase_managed_instance` | Stop instance; VM stops billing | DANGEROUS | [StopInstance](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=StopInstance) |
| `start_supabase_managed_instance` | Start a shutdown instance | DANGEROUS | [StartupInstance](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=StartupInstance) |
| `restart_supabase_managed_instance` | Restart instance; off-peak advised | DANGEROUS | [StartInstanceRestartAction](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=StartInstanceRestartAction) |
| `get_supabase_order` | Order status, amount, and items | READ | [ShowCustomerOrderDetails](https://console.huaweicloud.com/apiexplorer/#/openapi/BSS/doc?api=ShowCustomerOrderDetails) |
| `pay_supabase_order` | Pay pending order after verification | DANGEROUS | [PayOrders](https://console.huaweicloud.com/apiexplorer/#/openapi/BSS/doc?api=PayOrders) |
| `cancel_supabase_order` | Cancel an unpaid order | DANGEROUS | [CancelCustomerOrder](https://console.huaweicloud.com/apiexplorer/#/openapi/BSS/doc?api=CancelCustomerOrder) |
| `change_supabase_ssl` | Enable or disable SSL | WRITE | [SwitchSupabaseApplicationSsl](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=SwitchSupabaseApplicationSsl) |
| `plan_supabase_ssl` | SSL switch planning | READ | - |
| `list_ssl_certificates` | Inventory existing SSL certificates | READ | - |
| `purchase_supabase_ssl_cert` | Two-phase certificate purchase | DANGEROUS | - |
| `create_supabase_eip` | Idle-first EIP provisioning | WRITE | [CreatePublicip](https://console.huaweicloud.com/apiexplorer/#/openapi/EIP/doc?api=CreatePublicip) |
| `bind_supabase_eip` | First-time EIP binding (application-level public-eip) | WRITE | [SwitchSupabaseApplicationEipBind](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=SwitchSupabaseApplicationEipBind) |
| `create_supabase_new_obs` | Create a private OBS bucket | WRITE | `KooCLI OBS mb` |
| `change_supabase_eip` | Bind or unbind EIP | WRITE | [SwitchSupabaseApplicationEipBind](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=SwitchSupabaseApplicationEipBind) |
| `change_supabase_application_password` | Change app login password only | DANGEROUS | [ModifySupabaseApplicationPassword](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ModifySupabaseApplicationPassword) |
| `list_supabase_security_groups` | Browse security groups | READ | [ListSecurityGroups](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ListSecurityGroups) |
| `show_supabase_security_group` | Group details and rules | READ | [ShowSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=ShowSecurityGroup) |
| `create_supabase_security_group` | Create tagged dedicated group | WRITE | [CreateSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=CreateSecurityGroup) |
| `add_supabase_security_group_rule` | Add ingress/egress rules | DANGEROUS | [CreateSecurityGroupRule](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=CreateSecurityGroupRule) |
| `delete_supabase_security_group_rule` | Delete a rule | DANGEROUS | [DeleteSecurityGroupRule](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=DeleteSecurityGroupRule) |
| `delete_supabase_security_group` | Tag-gated group deletion | DANGEROUS | [DeleteSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/VPC/doc?api=DeleteSecurityGroup) |
| `change_supabase_security_group` | Rebind groups; full replacement | DANGEROUS | [SetSecurityGroup](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=SetSecurityGroup) |
| `show_operation_job_status` | Query async job status | READ | [ListJobInfo](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListJobInfo) |
| `show_supabase_creation_progress` | Track creation phases | READ | - |
| `wait_operation_job_complete` | Bounded wait to terminal state | READ | [ListJobInfo](https://console.huaweicloud.com/apiexplorer/#/openapi/RDS/doc?api=ListJobInfo) |

The full API reference is at the
[Huawei Cloud RDS API docs](https://support.huaweicloud.com/api-rds/rds_01_0002.html);
some Supabase APIs are newer than the published catalog — when API Explorer
lacks one, this server's actual behavior is authoritative.

## Usage guide

Starting, stopping, and restarting an application are asynchronous
operations: once accepted with a `job_id`, track it to a terminal state with
`show_operation_job_status` and re-read the application; stopping does not
stop the managed instance (it keeps billing) and starting does not
start the instance; restarting briefly interrupts the service — prefer
off-peak windows.

Stopping and restarting the managed instance are asynchronous operations as
well, tracked to a terminal state via `show_operation_job_status` and re-read
via `show_supabase_managed_instance`: the target instance is strictly
resolved from the application's `managed_instance` field (a bare
`instance_id` is never accepted, preventing operations on standalone database
instances); only pay-per-use instances on ultra-high-IO/SSD cloud disk/ESSD
storage can be stopped (dedicated clouds unsupported) — the VM stops billing
while EIP/storage/backup keep billing, and a default fifteen-day stop
auto-starts in the maintenance window if not started within fifteen days;
stopping the primary instance also stops its read replicas, and restarting
acts on them likewise; the instance is unavailable while stopped or
restarting, application features are affected (the application keeps failing
requests), and a start may fail on insufficient resources. **Start the
instance first, then the application** — starting the application does not
pull the managed instance up automatically.

### Prerequisites

1. Python 3.10+; [uv](https://docs.astral.sh/uv/) when using uvx.
2. Huawei Cloud credentials with the minimal required permissions
   (see [Permission recommendations](#permission-recommendations)).
3. For security-group tools: KooCLI installed locally with the privacy
   agreement accepted (see [KooCLI integration](#koocli-integration)).

### Installation

**uvx direct run (recommended):**

```bash
uvx mcp-server-huaweicloud-rds-supabase-mgr
```

The server is published on PyPI as
`mcp-server-huaweicloud-rds-supabase-mgr`; pin it with
`uv tool install mcp-server-huaweicloud-rds-supabase-mgr` (update via
`uv tool update mcp-server-huaweicloud-rds-supabase-mgr`). Near-named
third-party packages are not this server.

**pip install:**

```bash
pip install mcp-server-huaweicloud-rds-supabase-mgr
mcp-server-huaweicloud-rds-supabase-mgr
```

**Clone for development:**

```bash
git clone https://github.com/huaweicloud/rds-supabase-fullstack.git
cd rds-supabase-fullstack/server/mcp_server_rds_supabase_mgr
uv sync
uv run mcp-server-huaweicloud-rds-supabase-mgr          # stdio (default)
uv run mcp-server-huaweicloud-rds-supabase-mgr -t streamable-http
```

`mcp-server-huaweicloud-rds-supabase-mgr` is the canonical entry (it
matches the package name for direct uvx runs); the compatibility alias
`mcp-huaweicloud-rds-supabase-mgr` is equivalent. For slow-network uvx
startup timeouts, see the
[skill install reference](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-mgr-mcp/references/install.md).

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
| `HUAWEICLOUD_MCP_PROTECTED_NAMES` | no | Guardrail: protected resource names (comma-separated, hit = block) | empty |
| `HUAWEICLOUD_MCP_PROTECTED_TAGS` | no | Guardrail: protected tags (comma-separated `k` or `k=v`) | empty |
| `HUAWEICLOUD_MCP_GUARDRAILS_CONFIG` | no | Path to a `guardrails.yaml` rules file | empty |
| `HUAWEICLOUD_MCP_AUDIT_FILE` | no | Audit JSONL file path (audit always on; defaults to stderr) | empty |
| `MCP_SERVER_PORT` | no | streamable-http port | `8000` |
| `MCP_SERVER_HOST` | no | streamable-http bind address | `0.0.0.0` |

### Safety guardrails

Every write tool runs a preview/confirm two-phase flow: `confirm=false`
persists a ten-minute plan and returns a `plan_id`; confirmation resubmits
identical parameters with `confirm=true` + `plan_id`. Any change to
parameters, project, endpoint, or credentials requires a fresh preview. The
SQLite execution record (`SUPABASE_STATE_FILE`) registers every plan and
execution state: on a timeout or unknown outcome, verify directly against
the operation task and the target resource; no submitted plan may be
resubmitted, preventing double execution.

Passwords and credentials for SMTP, GitHub, and OBS never enter conversation;
the operator pre-provisions them into the local request registry
(`SUPABASE_REQUESTS_FILE`) and tools reference them by alias only,
accepting no plaintext. The cloud-write switch (`SUPABASE_ENABLE_WRITES`,
default off) and the read-only interception (`HUAWEICLOUD_MCP_READ_ONLY`)
act independently, and neither can be modified by the agent itself. A
`completed` job means the cloud API accepted the request only; re-read the
resource to confirm the business outcome.

Protection lists are configured via `HUAWEICLOUD_MCP_PROTECTED_*`
environment variables or `guardrails.yaml`, matching by tool name, risk
level, resource ID, name regex, or tag with block/confirm/warn actions.
Guardrails match at the parameter level: protected attributes that exist
only on the cloud side and never appear in tool arguments cannot match —
configure the protection lists proactively.

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

### KooCLI integration

The six VPC security-group tools (list/detail, create group, add/remove rules,
delete group) already embed the KooCLI capability and work out of the box:
the native RDS origin does not proxy the VPC API, so the tools call the VPC
v3 operations through the local KooCLI (`hcloud`) internally, with credential
injection, result parsing, preview confirmation, origin tagging, and
wrong-deletion protection. Changing which security groups a target binds
goes through `change_supabase_security_group` (the RDS SetSecurityGroup API,
not via KooCLI): multiple groups with full-list replacement semantics — the
given list is the final list, unlisted groups are detached, keep-needed
groups must be listed, and a missing 8443/5432 allowance after replacement
makes the application unreachable; rule add/remove within a group stays
with the existing rule tools. Principle: prefer these tools; fall back to raw
KooCLI commands only where they do not cover the need.

| Scenario | Use |
|---|---|
| Every routine security-group operation (list/detail, create group, add/remove rules, delete group, rebind groups) | This service's tools |
| Opening 0.0.0.0/0 world-wide ingress (tools refuse by design; requires explicit user confirmation) | Raw KooCLI commands |
| Edge operations the tools deliberately do not support (e.g. address-group management) | Raw KooCLI commands |

Operations-troubleshooting notes:

- **Prerequisite**: hcloud installed locally with its first-run privacy
  agreement accepted; installation is covered in
  [section 4 of the skill INSTALL.md](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/skills/huaweicloud-supabase/rds-supabase-mgr-mcp/INSTALL.md).
- **Binary location**: `HCLOUD_BIN` environment variable → fixed install
  directories → PATH, re-resolved on every call; no session restart needed
  after installation.
- **Credential injection**: injected per command only when both
  `HUAWEICLOUD_ACCESS_KEY` and `HUAWEICLOUD_SECRET_KEY` are set; otherwise
  the hcloud profile is used. REST token mode requires a local hcloud
  profile (`hcloud configure init`), or these tools report missing
  credentials.
- **Region and project**: region comes from `HUAWEICLOUD_REGION`; the
  project is resolved by KooCLI as the region default project — sub-project
  accounts must configure `--cli-project-id` in the hcloud profile.
- **Error passthrough**: VPC backend error_code/error_msg/request_id pass
  through verbatim; an unaccepted privacy agreement, a missing binary, and
  timeouts each map to a dedicated error code with remediation guidance.
- **Origin tagging**: every created group is auto-tagged AUTO_CREATE=true
  and USE_FOR=Supabase; whole-group deletion verifies the tag pair and
  rejects every group not created by this flow.

## Running with UVX

UVX stdio configuration for AgentArts and other clients:

```json
{
  "mcpServers": {
    "rds-supabase-mgr-mcp": {
      "command": "uvx",
      "args": ["mcp-server-huaweicloud-rds-supabase-mgr"],
      "env": {
        "HUAWEICLOUD_AUTH_TOKEN": "<service token>",
        "HUAWEICLOUD_MCP_READ_ONLY": "true",
        "SUPABASE_ENABLE_WRITES": "false"
      }
    }
  }
}
```

AgentArts supports UVX stdio and Streamable HTTP. Remote mode startup:

```bash
mcp-server-huaweicloud-rds-supabase-mgr -t streamable-http
```

It listens on `0.0.0.0:8000` by default with the endpoint at `/mcp`; front it
with HTTPS and client authentication in production. The server is
published on PyPI; uvx resolves and installs it directly
(see [Installation](#installation)).

## Examples

### Workflow 1: create a reachable application from scratch

1. Call `plan_supabase_creation_arrangement(manage_type, az_code, ...)` with
   the managed-source decision and intents (including the `needs_storage`
   answer) to get the end-to-end arrangement baseline: consolidated
   three-module parameters, the two independent modules (public access via EIP
   and SSL configuration), the OBS bucket plan,
   and the step-numbered creation flow.
2. Execute step by step per the arrangement: network ready (create the
   defaults per `default_create` when recommended) -> storage ready
   (`discover_supabase_storage` to decide reuse or new,
   `create_supabase_new_obs` when creating) -> the local request file (root
   password, storage credentials, and other secrets).
3. Submit with the creation tool matching the managed source (security
   groups are auto-created and injected by the tool — no manual
   `security_group_id`): `create_supabase_with_new_instance(request_ref,
   confirm=false)` for a new instance (recommended), or
   `create_supabase_link_exist_instance(request_ref, confirm=false)` to
   attach an existing one. Preview, show the redacted parameters to the
   user, then submit identical parameters with `confirm=true` + `plan_id`.
4. Track the returned workflow IDs with `show_supabase_creation_progress`
   (or `show_operation_job_status` / bounded `wait_operation_job_complete`)
   to a terminal state.
5. Re-read `show_supabase_application`; if public access is not open, run
   the Scenario 3 EIP provisioning and binding and sync `api_external_url`,
   then deliver access information via `list_supabase_api_keys` +
   `deliver_supabase_api_key`.

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
| Remote mode | Streamable HTTP | `mcp-server-huaweicloud-rds-supabase-mgr -t streamable-http`, endpoint `/mcp`; front it with HTTPS and authentication in production |

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

## Development, testing, and release

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

- [User guide](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/USER_GUIDE.md) — installation, verification, and the
  natural-language operation workflow
- [Tool contracts](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/TOOL_CONTRACTS.md) — the authoritative input/output
  and confirmation semantics
- [Recovery rules](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/RECOVERY.md) and
  [reconciliation contract](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/RECONCILIATION.md) — failure routing and
  Auth plan reconciliation
- [Local secret I/O](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/LOCAL_REQUESTS.md) — the sensitive-request
  reference mechanism
- [SDK mode](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/SDK.md), [migration notes](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/MIGRATION.md)
- [docs/legacy/](https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/docs/legacy/) — archived offline Windows delivery process

## License

MIT

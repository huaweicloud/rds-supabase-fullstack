---
name: huaweicloud-rds-pg-ops
description: '华为云 RDS for PostgreSQL 实例运维技能：实例生命周期（创建/重启/停机）、备份策略、库账号管理、变配扩容、监控告警、日志排查、参数调优、插件管理。Use this skill when the user wants to provision or manage Huawei Cloud RDS for PostgreSQL instances (create an instance, reset the admin password, reboot or stop an instance); check instance status and flavors; configure backup policy or take a manual backup; create databases, schemas, users and grant privileges; resize flavor, extend volume, or convert single to HA; query monitoring metrics and create alarm rules; troubleshoot slow SQL and error logs; tune database parameters or apply parameter templates; install extensions such as pgvector. Not for: SQL authoring best practices, Supabase application development, instance/backup deletion or restore (out of scope), and instance-level writes on any AI-application-bound instance (Supabase / GraphRAG / ContextBase or future types - the tools auto-detect bindings and block; route such operations to the corresponding AI application management plane; read-only tools remain available).
  English triggers: rds postgresql instance create reboot stop, backup policy manual backup, database user grant privilege, resize flavor extend volume, ces metric alarm rule, slow log audit log, postgres parameter tuning, install extension pgvector.'
license: MIT
version: "1.1.0"
tags: [huawei-cloud, rds, postgresql, ops, mcp]
metadata:
  version: "1.1.0"
  author: donel9527
  server: server/mcp_huaweicloud_rds_pg
---

# Huawei Cloud RDS for PostgreSQL Operations

## 1. Overview

This skill guides an Agent to operate Huawei Cloud RDS for PostgreSQL instances through the `mcp-huaweicloud-rds-pg` MCP server (74 tools). The tool layer enforces two-phase commit, replay protection, read-only guardrails, output redaction and JSONL auditing; this skill governs **which tool to use, in what order, and under what discipline**.

Position in the skill family: this skill is the guidance layer for PG instance operations — tool execution goes through `mcp_huaweicloud_rds_pg` (installation: references/install.md); in-database SQL quality rules are out of scope.

Typical use cases:

1. Provision a new RDS for PostgreSQL instance (sizing plan → confirmed creation → job polling).
2. Recover an unresponsive instance via a disciplined reboot; stop/start pay-per-use instances for cost savings.
3. Deliver connection info and SSL certificate to an application team; change port or security groups.
4. Configure backup policy per company standard and take a manual backup before risky changes.
5. Onboard a new application: create database + dedicated account + least-privilege grants.

## 2. Security Hard Constraints

These are non-negotiable for every write-class tool (WRITE / DANGEROUS):

1. **Two-phase commit**: always call with `confirm=false` first, present `changes` and `warnings` to the user, and only after explicit user consent re-issue the same call with `confirm=true` + `plan_id`. If the plan_id is stale (expired / already used / parameters changed), re-run the preview — never re-submit from memory.
2. **User-only decisions**: billing-related choices (subscription period, EIP bandwidth billing mode) must be decided by the user personally. The Agent must not choose on the user's behalf and must not silently apply defaults.
3. **No blind replay + digest-conflict handling**: when a write returns `unknown` (timeout / transport error), first check `show_pg_instance_job` and instance state — the cloud may already have executed. When a re-run of a previously-succeeded operation is legitimately needed (new session, same goal) and you get `Equivalent intent has an unresolved execution`: the intent ledger binds digests to exact parameters, so an identical parameter set collides with the historical record. **Vary a non-semantic parameter** (backup name suffix, window value, description text) to express the same intent with a fresh digest — never delete or edit the ledger, and never retry the exact same parameters in a loop.
4. **Action lock**: check instance `current_actions` before dispatching a write. RDS accepts one change operation per instance at a time (409 DBS.201015 means a prior task is still running — wait and retry, do not hammer concurrently).
5. **Password discipline**: instance/account passwords always go through `write_pg_secret_request` into a local request file; tools take a `password_ref` path. The Agent must never read, print or record the file content.
6. **Job completion**: asynchronous tasks (create / resize / backup, returning job_id) must be polled to a terminal state (Completed / Failed) and the instance state re-verified before the next step.
7. **Serial operations**: consecutive writes (create db → create schema → create user → grant) must wait for the previous one to take effect (cloud APIs apply asynchronously, ~20-60 s); on DBS.201015 / DBS.200019 wait 30-40 s before retrying.
8. **Read-only onboarding recommended**: writes are enabled by default (out-of-the-box), but for first onboarding consider running with `HUAWEICLOUD_MCP_READ_ONLY=true` to verify read paths before allowing writes; `RDS_PG_ENABLE_WRITES=false` is the service-level opt-out.
9. **IAM rate-limit awareness (401 APIGW.0301)**: this error means the ACCOUNT-LEVEL IAM lock tripped - not wrong credentials, not a tool bug. It fires when calls are too frequent or a retry loop keeps hitting IAM. Response discipline: (a) recognize `APIGW.0301` / "verify ak sk signature failed" as the lock signature; (b) STOP ALL cloud calls immediately (including read-only - every call renews the lock); (c) inform the user the lock expires after a quiet period (minutes; sustained quiet recovers fastest - retrying prolongs it); (d) after 5+ minutes of silence, probe ONCE with a single read (`list_pg_instances`) before resuming; (e) if the probe 401s again, wait another 5 minutes - do not probe in a loop. Prevention: keep poll intervals >= 15 s, batch writes serially, never run unattended retry loops.

## 3. Prerequisites

- **MCP server**: `mcp-huaweicloud-rds-pg` installed from this repository only (never the PyPI namesake) — see references/install.md.
- **Credentials**: `HUAWEICLOUD_ACCESS_KEY` / `HUAWEICLOUD_SECRET_KEY` / `HUAWEICLOUD_REGION` environment variables (project id auto-resolved via IAM when absent). Never ask the user to paste AK/SK into the conversation; configure out-of-band.
- **Write switch**: two-phase commit requires `RDS_PG_ENABLE_WRITES=true` and `HUAWEICLOUD_MCP_READ_ONLY` unset.
- **IAM permissions**: see references/iam-policies.md — 403 DBS.280015 means the AK/SK lacks the needed write permission; follow the policy-grant flow there and pause until the user confirms.
- **Python**: 3.10+ with `uv` for the MCP server runtime (references/install.md).

## 4. Workflow

Standard write workflow (all scenarios follow this spine):

```
show current state (READ) → preview write (confirm=false)
→ present changes/warnings to user → explicit consent
→ commit (confirm=true + plan_id) → poll job to terminal state
→ re-verify instance state → report
```

Read-only workflows (list / show / logs / metrics) skip the confirmation phases.

Scenario routing:

| User intent | Scenario file | Core tool chain |
|---|---|---|
| New instance (with sizing) | references/creation.md | plan_pg_instance_creation → write_pg_secret_request → create_pg_instance → show_pg_instance_job |
| Reboot / stop / start | Lifecycle (this page) | reboot/stop/start_pg_instance |
| Change root password | Lifecycle (this page) | write_pg_secret_request → reset_pg_admin_password |
| App needs to connect | references/connection.md | show_pg_connection_info → download_pg_ssl_cert → (security groups) → show_pg_dns_name / create_pg_dns_name / update_pg_dns_name (intranet domain) |
| Backup policy / manual backup | references/backup.md | show/set_pg_backup_policy → create_pg_manual_backup |
| Create db / account / grants | references/database.md | create_pg_database → create_pg_schema → create_pg_db_user → grant_pg_db_privilege |
| Resize / upgrade / single-to-HA | references/resize.md | resize_pg_flavor / extend_pg_volume / switch_pg_single_to_ha |
| Monitoring & alarms | references/monitoring.md | list_pg_resource_metrics → show_pg_metric_data → create_pg_alarm_rule |
| Slow SQL / error troubleshooting | references/logs.md | list_pg_slow_logs → download_pg_slow_log |
| Parameter tuning | references/parameters.md | show_pg_parameters → update_pg_parameter |
| Install / remove extensions | references/extensions.md | list_pg_extensions → install_pg_extension |

## 5. Core Commands (MCP tools by function group)

MCP-type skill: tools are invoked via the MCP protocol, not `hcloud`. Naming is `verb_object`; risk level is declared per tool by `@guard`.

| Group | Tools (READ unless noted) |
|---|---|
| Instance lifecycle | list/show_pg_instance, show_pg_instance_job, reboot/stop/start_pg_instance (WRITE), create_pg_instance (DANGEROUS), reset_pg_admin_password (DANGEROUS) |
| Sizing / catalog | list_pg_flavors, list_pg_datastores, list_pg_storage_types, show_pg_quotas, plan_pg_instance_creation |
| Connection | show_pg_connection_info, download_pg_ssl_cert, list_pg_hba_conf, show_pg_dns_name; change_pg_instance_port / change_pg_security_group / change_pg_hba_conf / create_pg_dns_name / update_pg_dns_name (WRITE) |
| Backup | show/list_pg_backup*, list_pg_restore_times; set_pg_backup_policy / create_pg_manual_backup (WRITE) |
| Database / account | list_pg_databases/schemas/db_users; create_pg_database / create_pg_schema / create_pg_db_user / grant_pg_db_privilege (WRITE), set_pg_db_user_password (DANGEROUS) |
| Resize | list_pg_read_replicas; resize_pg_flavor / extend_pg_volume / reduce_pg_volume / set_pg_auto_enlarge_policy / switch_pg_single_to_ha / change_pg_ops_window (DANGEROUS/WRITE) |
| Monitoring (CES) | list_pg_resource_metrics, show_pg_metric_data; create_pg_alarm_rule (WRITE) |
| Logs | list/download_pg_slow_log, list/download_pg_error_log, list_pg_audit_logs; set_pg_audit_log_policy (WRITE) |
| Parameters | show_pg_parameters, list/compare_pg_configurations; update_pg_parameter / apply_pg_configuration (WRITE) |
| Extensions | list_pg_extensions; install/uninstall_pg_extension (WRITE) |

## 6. Parameter Confirmation

| Parameter | Who decides | Default |
|---|---|---|
| charge_mode (postPaid/prePaid) + period | **user-only** | none — Agent must not choose |
| EIP bandwidth billing mode | **user-only** | none |
| flavor / volume size / HA mode | user-confirm | Agent recommends from `list_pg_flavors` baseline |
| port / availability_zone | agent-default | 5432 / first AZ with `normal` status |
| admin & db account passwords | user (via write_pg_secret_request) | never in conversation; `password_ref` only |

## 7. Output Format

Every tool returns a JSON envelope (`page_result` / `confirmation_required` / `submitted` / error envelope with `request_id` + `hint`). For user-facing reports: state before → changes applied → state after → job outcome; never include password values, AK/SK or raw credential material (redaction is enforced in the tool layer and must not be bypassed).

## 8. Verification Method

After any write: poll `show_pg_instance_job` to terminal state, re-run the corresponding READ tool (e.g. `show_pg_instance` → ACTIVE, no action lock) and, for connection changes, verify with a real client connect. Full three-level verification procedure (connection → functional → acceptance five-check): references/verification-method.md.

## 9. Best Practices

- Pre-check quotas with `show_pg_quotas` before creating an instance.
- Read references/creation.md for the dual-AZ rule (`ha_mode=Ha` requires "az1,az2") and other field contracts.
- Stopped pay-per-use instances still incur storage cost — surface the warning, don't hide it.
- Keep operations serial; DBS.201015 / DBS.200019 means wait 30-40 s, not retry storm.
- For production instances, set `HUAWEICLOUD_MCP_PROTECTED_IDS/NAMES` before enabling writes.

## 10. References

- references/install.md — MCP server install & host registration, env vars
- references/creation.md / connection.md / backup.md / database.md / resize.md / monitoring.md / logs.md / parameters.md / extensions.md — per-scenario playbooks (all field contracts live-tested)
- references/iam-policies.md — required IAM permissions and least-privilege policy
- references/verification-method.md — three-level verification & acceptance
- references/acceptance-criteria.md — MCP-skill acceptance checklist

## 11. Notes (Gotchas)

| Symptom | Handling |
|---|---|
| `MCP_READ_ONLY` | Read-only guardrail; open writes via RDS_PG_ENABLE_WRITES=true + unset READ_ONLY, restart server |
| `MCP_GUARDRAIL_BLOCKED: already used` | plan_id consumed — normal replay protection, re-preview |
| `MCP_GUARDRAIL_BLOCKED: Equivalent intent has an unresolved execution` | **Digest conflict**: the exact same operation+parameters was recorded before (possibly in a previous session — accepted rows never expire). Not an error in your logic. Resolution: verify the prior outcome first (show_pg_instance_job / show the changed resource); if the prior op is settled and you need to run the same operation again, **deliberately vary a non-semantic parameter** (e.g. a different backup name, a different ops-window value) so the intent digest differs, then preview → confirm as usual |
| `DBS.201015 / DBS.200019` | Instance busy (prior op unfinished) — wait 30-40 s, or check show_pg_instance_job |
| `MCP_INVALID_ARGS: only postPaid` | Subscription instances do not support stop |
| 403 DBS.280015 | AK/SK lacks the write permission (e.g. parameter change) — grant policy via references/iam-policies.md |
| Engine guard `is a MySQL instance` | Wrong instance id; this server manages PostgreSQL only |
| DBS.200019 on consecutive writes | Async effect lag — wait, see Security Hard Constraints #7 |

Lifecycle quick reference (reboot / stop / start / reset password, kept on this page): reboot = preview → consent → commit → poll job → verify ACTIVE (fastest recovery for a hung instance). Stop = postPaid only, tool auto-rejects subscription instances, storage still billed. Reset root password = `write_pg_secret_request(password)` → `reset_pg_admin_password(instance_id, password_ref)` two-phase; old-password sessions die after the change lands.

Installation and registration of the MCP server: **references/install.md**; skill install instructions: **INSTALL.md**.

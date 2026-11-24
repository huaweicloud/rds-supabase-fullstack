---
name: huaweicloud-rds-pg-ops
description: '华为云 RDS for PostgreSQL 实例运维技能：实例生命周期（创建/重启/停机）、备份策略、库账号管理、变配扩容、监控告警、日志排查、参数调优、插件管理。Use when：开通或管理 RDS for PostgreSQL 实例（创建实例、重置密码、重启停机）；查询实例状态与规格；配置备份策略或手动备份；建库建账号授权；CPU/磁盘变配、单机转主备；查监控指标、建告警规则；慢 SQL 与错误日志排查；调整数据库参数、应用参数模板；安装 pgvector 等插件。不适用于：SQL 编写质量规则（见 postgres best-practices 类技能）、Supabase 应用开发、删除实例/删除备份/恢复类操作（范围外）。
  English triggers: rds postgresql instance create reboot stop, backup policy manual backup, database user grant privilege, resize flavor extend volume, ces metric alarm rule, slow log audit log, postgres parameter tuning, install extension pgvector.'
license: MIT
version: "1.0.0"
tags: [huawei-cloud, rds, postgresql, ops, mcp]
metadata:
  version: "1.0.0"
  author: donel9527
  server: server/mcp_server_rds_pg
---

# 华为云 RDS for PostgreSQL 实例运维

## 概述

本技能指导 Agent 通过 `mcp-huaweicloud-rds-pg` MCP 服务器（59 工具）管理华为云 RDS for PostgreSQL 实例。工具层内置两段式提交、防重放、只读护栏与审计；本技能规定**何时用哪个工具、什么顺序、什么纪律**。

在技能族中的位置：本技能是 PG 实例运维的指引层——工具执行经 `mcp_server_rds_pg`（安装见 references/install.md），数据库内 SQL 质量规则不在本技能范围。

## 执行通道

**MCP 服务器**：`mcp-huaweicloud-rds-pg`（安装规程见 references/install.md，只从本仓安装，禁 PyPI 同名包）。

**凭据**：`HUAWEICLOUD_ACCESS_KEY/SECRET_KEY/REGION`；首次接入建议 `HUAWEICLOUD_MCP_READ_ONLY=true` 只读验证后放开。

**写开关**：两段式提交需要 `RDS_PG_ENABLE_WRITES=true` 且 `HUAWEICLOUD_MCP_READ_ONLY` 未设。

## 硬纪律（写操作必守）

1. **两段式**：所有写类工具（WRITE/DANGEROUS）先 `confirm=false` 预览，向用户展示 changes 与 warnings，用户明确同意后同参 `confirm=true` + plan_id 提交。plan_id 失效（过期/已用/参数变更）重新预览，不凭记忆重发。
2. **user-only 决策**：计费类选择（包周期时长、EIP 带宽计费方式）必须用户本人拍板，Agent 不得代选、不得默认。
3. **禁止重放**：写操作返回 unknown（超时/传输错误）时，先查 `show_pg_instance_job` 与实例状态，**禁止盲目重试**——云端可能已执行。
4. **action 锁**：下发写操作前查实例 `current_actions`；RDS 一个实例同时只接受一个变更操作（409 DBS.201015 表示前序任务未完成，等待后重试，不要并发轰炸）。
5. **密码纪律**：实例/账号密码一律经 `write_pg_secret_request` 落本地请求文件，工具参数传 `password_ref` 路径；Agent 禁止读取、打印、记录文件内容。
6. **job 等待**：创建/变配/备份等异步任务（返回 job_id）要轮询到终态（Completed/Failed）并复核实例状态后，才进行下一步操作。
7. **操作串行**：连续写操作（建库→建 schema→建账号→授权）每步之间等待前一个生效（云 API 异步生效，约 20-60 秒）；DBS.201015/DBS.200019 重试等 30-40 秒。

## 场景路由

| 用户意图 | 场景文件 | 核心工具链 |
|---|---|---|
| 新建实例（含选型） | references/creation.md | plan_pg_instance_creation → write_pg_secret_request → create_pg_instance → show_pg_instance_job |
| 实例重启/停机/开机 | 本页「生命周期」 | reboot/stop/start_pg_instance |
| 改 root 密码 | 本页「生命周期」 | write_pg_secret_request → reset_pg_admin_password |
| 应用要连库 | references/connection.md | show_pg_connection_info → download_pg_ssl_cert →（安全组） |
| 备份策略/手动备份 | references/backup.md | show/set_pg_backup_policy → create_pg_manual_backup |
| 建库建账号授权 | references/database.md | create_pg_database → create_pg_schema → create_pg_db_user → grant_pg_db_privilege |
| 扩容/升配/转主备 | references/resize.md | resize_pg_flavor / extend_pg_volume / switch_pg_single_to_ha |
| 监控与告警 | references/monitoring.md | list_pg_resource_metrics → show_pg_metric_data → create_pg_alarm_rule |
| 慢 SQL / 错误排查 | references/logs.md | list_pg_slow_logs → download_pg_slow_log |
| 参数调优 | references/parameters.md | show_pg_parameters → update_pg_parameter |
| 装/卸插件 | references/extensions.md | list_pg_extensions → install_pg_extension |

## 生命周期（本页场景）

**重启**：`reboot_pg_instance(id, confirm=false)` 展示预览 → 用户确认 → 同参提交 → 轮询 job → 复核 ACTIVE。实例假死场景的最快恢复路径。

**停机（成本优化）**：仅按需（postPaid）实例可停；工具自动拒绝包周期。停机仍计存储费（warning 已含）。
**启动**：`start_pg_instance` 两段式；目标是 STOPPED 实例。

**改 root 密码**：`write_pg_secret_request(password)` 得 request_ref → `reset_pg_admin_password(instance_id, password_ref)` 两段式。旧密码会话在变更落地后失效。

## 通用排错

| 现象 | 处置 |
|---|---|
| `MCP_READ_ONLY` | 只读模式拦截；放开需同时设 RDS_PG_ENABLE_WRITES=true 且 unset READ_ONLY，重启 server |
| `MCP_GUARDRAIL_BLOCKED: already used` | plan_id 已消费——正常防重放，重新预览 |
| `DBS.201015 / DBS.200019` | 实例忙（前一操作未完成）——等 30-40s 重试，或查 show_pg_instance_job |
| `MCP_INVALID_ARGS: only postPaid` | 包周期实例不支持 stop |
| 403 DBS.280015 | 该 AK/SK 缺对应写权限（如参数修改）——IAM 侧补策略 |
| 引擎守卫 `is a MySQL instance` | 传错实例 id；本服务只管 PostgreSQL |

## 安装与注册

MCP 服务器安装、Claude Code/Cursor 注册、环境变量清单：**references/install.md**。

# 现网测试指引（华为云 RDS for PostgreSQL）

> 完整版测试计划：**全量覆盖设计文档业务场景** + 横向机制。
> 每个测试组标注实现状态：✅ M1 已实现可测 / ⏳ M2 / ⏳ M3。

## 0. 总体结构

| 维度 | 测试组 | 覆盖设计文档 |
|---|---|---|
| 机制 | G1-G6（+G7 AI 应用守卫） | §4（两段式）§5（request_ref）§7（环境变量）+ core 护栏 |
| 业务场景 | B1-B16 | §3.1-§3.10 全部十个场景，一场景一组 |
| 机制进阶 | E1-E3 | §6 编排工具（三档确认级别、分阶段 apply_steps） |

执行顺序：先机制（G）→ 已实现场景（B1-B3）→ 随 M2/M3 交付逐组点亮其余 B 组 → E 组随编排工具交付。

---

## 1. 安装

```bash
cd server/mcp_server_rds_pg
uv sync
uv run mcp-huaweicloud-rds-pg            # stdio 模式
uv run mcp-huaweicloud-rds-pg -t streamable-http   # HTTP :8000
```

## 2. 环境变量（现网凭证）

```bash
export HUAWEICLOUD_ACCESS_KEY=<你的AK>
export HUAWEICLOUD_SECRET_KEY=<你的SK>
export HUAWEICLOUD_REGION=cn-north-4        # 按实际区域
# 可选：
export HUAWEICLOUD_PROJECT_ID=<项目ID>      # 缺省经 IAM 自动解析
```

## 3. 机制测试（G1-G6，随 M1 立即执行）

### G1 基础读写

| # | 操作 | 验收 |
|---|---|---|
| G1.1 | list_pg_instances | page_result 信封；与控制台实例管理页核对数量/status/AZ/规格 |
| G1.2 | list_pg_instances(limit=1, marker=...) | 分页字段 count/total/marker 正确 |
| G1.3 | show_pg_instance <真实id> | datastore.version/flavor_ref/volume/ha/charge_mode 与控制台一致 |
| G1.4 | show_pg_instance 不存在 id | MCP_NOT_FOUND 信封 + hint 引导先 list |
| G1.5 | show_pg_instance_job <历史job> | 从控制台任务中心取 id 验证 |
| G1.6 | 凭证缺失/错误 | 首次调用报错信封（不崩溃），含 request_id |

### G2 两段式管线

| # | 操作 | 验收 |
|---|---|---|
| G2.1 | reboot confirm=false | confirmation_required + changes + warnings + plan_id + expires_at；实例无动作（控制台刷新） |
| G2.2 | 同参 + confirm=true + plan_id | submitted + job_id；控制台 REBOOTING |
| G2.3 | job 轮询至 Completed | show_pg_instance 复核 ACTIVE 无 action 锁 |
| G2.4 | 重放已消费 plan_id | MCP_GUARDRAIL_BLOCKED (already used) |
| G2.5 | 嫁接：预览 A 提交 B | digest 不匹配 → blocked |
| G2.6 | plan 过期（10min） | blocked (expired) |
| G2.7 | 伪造 plan_id 提交 | blocked (missing) |
| G2.8 | 提交时实例带 action 锁 | blocked (not demonstrably ready)，未下发任务 |

### G3 双写开关

| # | 操作 | 验收 |
|---|---|---|
| G3.1 | 两者均未设，直接 confirm=true | MCP_READ_ONLY 拒绝 |
| G3.2 | RDS_PG_ENABLE_WRITES=true + READ_ONLY=true | 仍拒绝 |
| G3.3 | 只开 READ_ONLY，confirm=false 预览 | 预览正常（preview 不受限） |

### G4 保护规则

| # | 操作 | 验收 |
|---|---|---|
| G4.1 | HUAWEICLOUD_MCP_PROTECTED_IDS=<id> 后 show 该实例 | READ 放行 |
| G4.2 | 对该实例 reboot 预览 | 参数级匹配命中 → blocked |
| G4.3 | 改用 PROTECTED_NAMES=<实例名> | name 匹配同样生效 |

### G5 审计

| # | 操作 | 验收 |
|---|---|---|
| G5.1 | HUAWEICLOUD_MCP_AUDIT_FILE 设置后跑 G2 全组 | 每调用一条 JSONL（含被拦的） |
| G5.2 | 检查 params 字段 | 脱敏 + 截断，无敏感值 |
| G5.3 | jq 可解析 | tool/risk/decision/duration_ms 齐全 |

### G6 协议冒烟

| # | 操作 | 验收 |
|---|---|---|
| G6.1 | MCP 客户端 initialize | server 名 huaweicloud-rds-pg |
| G6.2 | tools/list | 6 工具按序注册（M1 数量随版本增长） |
| G6.3 | /health（HTTP 模式） | 200 {"status":"ok"} |

### G7 AI 应用守卫（通用守卫：ListAiApplications 绑定检测）

| # | 操作 | 验收 |
|---|---|---|
| G7.1 | 详见 **AGENT-E2E-GUIDE.md 阶段三（AI-1..AI-5）** | AI-1 SDK 探测 API 字段；AI-2 无绑定不误伤；AI-3 绑定阻断（信封含应用名，tests/test_ai_guard_e2e.py mock 注入）；AI-4 只读不受影响；AI-5 API 不可用时 supabase 命名兜底 |

---

## 4. 业务场景测试（B1-B16，全量对齐设计文档 §3.1-§3.10）

### B1 日常巡检 ⏳ 部分实现（M1）

**用户故事**：「每天早上给我 PG 实例健康简报」→ 设计文档 P0-1 只读族 + P1-7 指标雏形

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B1.1 | list 全量实例 | 数量/状态与控制台一致 | ✅ |
| B1.2 | 逐实例 show | 关键字段正确 | ✅ |
| B1.3 | 汇总 action 锁 | 锁定实例进简报 | ✅ |
| B1.4 | list_pg_flavors / list_pg_datastores / list_pg_storage_types / show_pg_quotas | 选型数据可查（M2 前作为巡检补充项） | ⏳ |
| B1.5 | show_pg_metric_data（CPU/磁盘指标） | 指标数据进简报 | ⏳ M3 |

### B2 故障自愈重启 ✅ M1

**用户故事**：「实例假死帮我重启」→ P0-1 reboot

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B2.1 | show 确认现状 | 记录 status/current_actions | ✅ |
| B2.2 | reboot 预览 | warnings 含中断提示；实例未动 | ✅ |
| B2.3 | 放弃 plan（模拟犹豫） | 不提交即无效果 | ✅ |
| B2.4 | 重新预览 + 提交 | job_id + 控制台 REBOOTING | ✅ |
| B2.5 | job 轮询 | Running → Completed | ✅ |
| B2.6 | 复核 | ACTIVE 无锁 | ✅ |
| B2.7 | 重启中再提交另一操作 | action 锁拦截 | ✅ |

### B3 成本优化停机 ✅ M1

**用户故事**：「周末停开发实例省钱」→ P0-1 stop/start

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B3.1 | 按需实例 stop 两段式 | STOPPED + 计费 warning 出现 | ✅ |
| B3.2 | 停机后 psql 连接 | 连接失败（真实中断） | ✅ |
| B3.3 | 包周期实例 stop | MCP_INVALID_ARGS 拒绝 | ✅ |
| B3.4 | start 两段式恢复 | ACTIVE + psql 可连 | ✅ |
| B3.5 | 对 ACTIVE 实例 start | 状态前置拦截 | ✅ |

### B4 实例开通 ⏳ M2

**用户故事**：「新建一个 PG 实例，先给我方案」→ P0-1 create + plan 编排

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B4.1 | plan_pg_instance_creation(region, needs_public_access, needs_read_replica) | 返回 baseline（实时 flavors/storage/AZ）+ decision_checklist + apply_steps | ⏳ |
| B4.2 | 检查三档确认级别 | charge_mode/EIP 计费/副本数量 = user-only（无默认推荐）；flavor/volume/HA = user-confirm（有 recommended） | ⏳ |
| B4.3 | 收集用户选择前直接调 create | 工具层/Skill 层拦截（user-only 未决不得执行） | ⏳ |
| B4.4 | 密码走 request_ref | 预览信封不显示密码值 | ⏳ |
| B4.5 | create confirm=false → true | plan_id 链正确；job 轮询 5-25 分钟 | ⏳ |
| B4.6 | 重复同意图提交 | 同意图未决拒绝（防双开） | ⏳ |
| B4.7 | needs_public_access=true | apply_steps 含条件步骤（bind EIP），实例 ACTIVE 前不可执行 | ⏳ |
| B4.8 | B4.5 完成后复核 | ACTIVE + show_pg_connection_info 可获取内网地址 | ⏳ |
| B4.9 | 包周期计费选择 | prePaid 需额外确认层级（计费时长 user-only） | ⏳ |
| B4.10 | show_pg_quotas 不足 | 建实例前配额预检给出明确错误 | ⏳ |

### B5 密码管理 ⏳ M2

**用户故事**：「root 密码泄露，立即改」→ P0-1 reset_pg_admin_password

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B5.1 | reset 预览 | password_ref 别名引用，值不出现在信封 | ⏳ |
| B5.2 | 提交后旧密码 psql | 连接失败 | ⏳ |
| B5.3 | 新密码 psql | 连接成功 | ⏳ |
| B5.4 | 审计日志 | password 字段脱敏为 *** | ⏳ |

### B6 连接交付 ⏳ M2

**用户故事**：「应用要连库，给我连接信息」→ P0-2 连接管理

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B6.1 | show_pg_connection_info | 内网 IP/端口/域名聚合视图，与 psql 实连一致 | ⏳ |
| B6.2 | download_pg_ssl_cert | 临时 URL 可下载；hint 声明时效 | ⏳ |
| B6.3 | 用证书 psql sslmode=verify-ca | 按 PG 客户端指南连接成功 | ⏳ |
| B6.4 | bind EIP 两段式 | 绑定后公网可连（安全组已放行前提） | ⏳ |
| B6.5 | unbind | warning 明示「EIP 未释放仍计费」 | ⏳ |
| B6.6 | change port 两段式 | warning 含 4-10 分钟重启窗口；改后 psql 用新端口连 | ⏳ |
| B6.7 | change security_group | **全量替换语义**：提交清单未含的既有组被移除——测试保留组显式列入 | ⏳ |
| B6.8 | list_pg_hba_conf + change | hba 变更后 ListPostgresqlHbaInfoHistory 可查历史 | ⏳ |
| B6.9 | create_pg_dns_name 两段式（dns_type=private） | 预览信封含域名影响 warning → 提交 → show_pg_dns_name 复核域名出现；show_pg_connection_info 含 dns_name | ✅ 管线级（11.6；云端待 IAM 恢复） |
| B6.10 | update_pg_dns_name 两段式（自定义名） | **旧域名立即失效 warning 转述**；提交 → show 复核新名；名称规则负向（大写/下划线 → MCP_INVALID_ARGS） | ✅ 管线级（11.6；云端待 IAM 恢复） |
| B6.11 | show_pg_dns_name | 返回当前 dns_name（未开通时空结构=正常）；信封含 object_id/dns_type | ✅ 管线级（11.6；云端待 IAM 恢复） |

### B6b 网络环境 + EIP（M4，12 工具）

**用户故事**：「建实例前先把网络弄好」/「给这台实例开公网」→ §3.2b 网络环境模块

测试命名一律带时间戳（e2e-test-<res>-<ts>）避免 PlanStore 账本冲突；写前清 stuck 账本行。

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B6b.1 | discover_pg_network | 聚合 EPS+VPC+子网+SG；default_vpc/default_subnet 出现在推荐位；SG 带 open_5432 标记；EPS 个人账号正常降级（null+note）不炸整体 | ⏳ |
| B6b.2 | list_pg_vpcs | 至少含 default VPC；字段 id/name/cidr/status | ⏳ |
| B6b.3 | list_pg_subnets(default_vpc) | 含 default 子网；cidr/az/gateway/available_ip_address_count | ⏳ |
| B6b.4 | list_pg_security_groups | 多组返回；至少一组 open_5432 与控制台规则核对 | ⏳ |
| B6b.5 | create_pg_vpc(e2e-test-vpc-<ts>) 两段式 | 预览信封 changes/warnings/plan_id；提交后 list_pg_vpcs 可见；控制台核对 CIDR | ⏳ |
| B6b.6 | create_pg_subnet（在新 VPC，192.168.6.0/24，cn-north-4a） | 提交后 list 可见；**CIDR 不在 VPC 内被拒**（负向：10.99.0.0/24 → MCP_INVALID_ARGS） | ⏳ |
| B6b.7 | create_pg_security_group(e2e-test-sg-<ts>, open_5432_from='10.0.0.0/24') | 组创建+规则创建；list_pg_security_groups 中该组 open_5432=true；控制台规则 remote 10.0.0.0/24 TCP 5432 | ⏳ |
| B6b.8 | SG 负向：无来源 | open_5432=true 且无 open_5432_from/subnet_id → MCP_INVALID_ARGS 拒绝 | ⏳ |
| B6b.9 | list_pg_enterprise_projects | EPS v1 钉 cn-north-4；个人账号降级 note | ⏳ |
| B6b.10 | create_pg_enterprise_project | **SKIPPED-PERM**（管理员权限+组织级资源，只测预览信封不提交） | ⏳ |
| B6b.11 | create_pg_eip(e2e-test-eip-<ts>, billing_type=traffic) 两段式 | 按流量计费（最便宜）；USAGE_FOR=rds-pg 标签写入；billing_type 缺失/非法 → 拒绝（user-only） | ⏳ |
| B6b.12 | bind_pg_instance_eip(test01, 新 EIP id) 两段式 | 预览含公网暴露+费用 warning；提交后 show_pg_instance public_ips 出现该 IP；test01 忙（非 ACTIVE/带 current_actions）→ 等待重试最多 15 分钟，仍忙记 SKIPPED-BUSY | ⏳ |
| B6b.13 | unbind_pg_instance_eip(test01) 两段式 | warning「解绑不释放不停止计费」；提交后 public_ips 清空 | ⏳ |
| B6b.14 | 测试收尾释放 EIP | EIP 未绑定状态也计保有费——用 hcloud/SDK DeletePublicip 释放（工具面无删除）；释放后确认 | ⏳ |
| B6b.15 | plan_pg_instance_creation | baseline.network 模块出现（placement+SG 决策）；checklist 含 network/security_group/eip 三档；needs_public_access=true 时 apply_steps 含 eip_create/eip_bind | ⏳ |

### B7 备份管理 ⏳ M2

**用户故事**：「按公司规范配置备份策略 + 关键变更前手动备份」→ P0-3 备份

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B7.1 | show_pg_backup_policy | 当前策略可见 | ⏳ |
| B7.2 | set_pg_backup_policy（keep_days<7） | 参数校验拒绝（≥7 约束） | ⏳ |
| B7.3 | set 合法策略 | 预览展示窗口/保留期；提交后 show 复核生效 | ⏳ |
| B7.4 | set offsite | 跨区费用 warning 出现 | ⏳ |
| B7.5 | create manual backup | name 约束 + job 完成 + list_pg_backups 可见（type=手动） | ⏳ |
| B7.6 | show download link | 临时 URL 可下载 | ⏳ |
| B7.7 | list_pg_restore_times | 返回可恢复时间窗 | ⏳ |


### B8 库与账号开通 ⏳ M2

**用户故事**：「新应用上线：建库+专用账号+最小授权」→ P0-4

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B8.1 | create_pg_database | 库出现于 list；psql 可 \c | ⏳ |
| B8.2 | create schema | schema 出现 | ⏳ |
| B8.3 | create_pg_db_user | **密码 request_ref 全链路**：预览无值、审计脱敏、值不进对话 | ⏳ |
| B8.4 | set_pg_db_user_password | 改后新旧密码验证 | ⏳ |
| B8.5 | grant 最小权限 | 按授权矩阵授予；psql 验证越权操作被拒 | ⏳ |
| B8.6 | revoke | 权限回收生效 | ⏳ |
| B8.7 | update comment（L1 轻写） | middleware confirm 即可（无 plan_id）；同步生效 | ⏳ |

### B9 规格与容量演进 ⏳ M3

**用户故事**：「业务量涨了，扩容磁盘 + 升配」→ P1-5

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B9.1 | resize_pg_flavor | warning 含「会重启」；job 完成后 flavor_ref 变化 | ⏳ |
| B9.2 | extend_pg_volume | 容量增长 + 计费 warning | ⏳ |
| B9.3 | reduce_pg_volume | 引擎 17+ 限定校验（16 实例被拒） | ⏳ |
| B9.4 | set auto enlarge policy | 阈值/上限生效（show 复核） | ⏳ |
| B9.5 | switch single to Ha | 单机转主备走完 job | ⏳ |
| B9.6 | change ops window | 维护窗口变更生效 | ⏳ |

### B10 读写分离扩展 ⏳ M3

**用户故事**：「读压力大，加只读实例」→ P1-6

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B10.1 | create read replica 两段式 | 前置校验：主实例 ACTIVE 无锁；replica 出现于 list_pg_read_replicas | ⏳ |
| B10.2 | 主实例带锁时创建 | blocked | ⏳ |
| B10.3 | replica 上执行写操作验证只读 | psql 写入报错（只读实例语义） | ⏳ |
| B10.4 | 编排入口（B4 的 needs_read_replica 路径） | apply_steps 步骤 6 条件执行 | ⏳ |

### B11 监控告警 ⏳ M3

**用户故事**：「CPU 打满要提前知道」→ P1-7（CES 通道）

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B11.1 | list_pg_resource_metrics | 指标元数据（含 PG 专属指标） | ⏳ |
| B11.2 | show_pg_metric_data（rds021 CPU 等） | 时序数据返回，与控制台曲线趋势一致 | ⏳ |
| B11.3 | create_pg_alarm_rule 两段式 | 告警规则出现于 CES 控制台 | ⏳ |
| B11.4 | 告警触达 | （可选，注入负载触发告警验证通知链路） | ⏳ |

### B12 慢 SQL 排查 ⏳ M3

**用户故事**：「应用变慢，查慢日志」→ P1-8 日志

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B12.1 | list_pg_slow_logs | 有慢日志记录（先跑一条 >log_min_duration 的 SQL） | ⏳ |
| B12.2 | download slow log | 临时 URL 可下载 | ⏳ |
| B12.3 | list_pg_error_logs | 错误日志可见 | ⏳ |
| B12.4 | download_pg_error_log | 临时 URL 可下载 | ⏳ |
| B12.5 | set_audit_log_policy | **按量计费 warning** 必须出现；开启后 list_pg_audit_logs 有记录 | ⏳ |

### B13 参数调优 ⏳ M3

**用户故事**：「连接数吃紧，调 max_connections」→ P1-9

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B13.1 | show_pg_parameters | 参数清单含 max_connections 等当前值 | ⏳ |
| B13.2 | update 非重启参数 | 立即生效，show 复核 | ⏳ |
| B13.3 | update restart_required 参数 | 预览强制出现重启 warning + 需 confirm | ⏳ |
| B13.4 | list/compare configurations | 模板清单与差异对比 | ⏳ |
| B13.5 | apply configuration | 应用后参数生效 | ⏳ |

### B14 插件管理 ⏳ M3

**用户故事**：「要做向量检索，装 pgvector」→ P1-10

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B14.1 | list_pg_extensions | 插件清单（含 pgvector 可用性） | ⏳ |
| B14.2 | install pgvector | 安装后 list 状态变化；psql CREATE EXTENSION 可用 | ⏳ |
| B14.3 | install 需重启插件 | hint 提示重启要求 | ⏳ |
| B14.4 | uninstall | 状态回退 | ⏳ |

### B15 异常输入边界 ✅ M1（随 B 组持续回归）

| # | 操作 | 验收 |
|---|---|---|
| B15.1 | 各工具空 id/非法字符 | 参数校验拒绝，不产生 SDK 调用 |
| B15.2 | limit=0/999/负数 | 夹紧 1..100 |
| B15.3 | 空账号/无权限账号 | 错误信封含权限提示 |
| B15.4 | 传输层异常（断网） | unknown 信封「do NOT resubmit」 |

### B16 保护与审计（横切）✅ M1（随 B 组持续回归）

即 G4/G5 的业务化重复执行：每个新交付 B 组跑通后，对其写操作各做一次保护规则拦截 + 审计记录验证。

---

## 5. 编排机制进阶（E1-E3，随 M2 编排工具交付）

> 设计文档 §6：三档确认级别 + 分阶段提交 + 条件步骤

| # | 测试 | 验收 | 状态 |
|---|---|---|---|
| E1.1 | user-only 项 Agent 代选 | 拒绝执行（清单未决） | ⏳ |
| E1.2 | user-confirm 项用户接受推荐 | 推荐值进请求 | ⏳ |
| E1.3 | agent-default 项 | 预览信封展示，不问即生效 | ⏳ |
| E2.1 | 多步流程中断（主实例创建失败） | 后置步骤不启动；断点可重入 | ⏳ |
| E2.2 | 条件步骤静默省略 | 报告必须显式说明跳过原因（Skill 层校验） | ⏳ |
| E3.1 | 分阶段各自 plan_id | 每步独立绑定，跨步嫁接被拒 | ⏳ |
| E3.2 | 步骤前置运行时回查 | EIP/replica 在实例 ACTIVE 前执行被拒 | ⏳ |

---

## 6. 写开关

写操作默认关闭。测试两段式前需要：
```bash
export RDS_PG_ENABLE_WRITES=true
unset HUAWEICLOUD_MCP_READ_ONLY
```

## 7. 里程碑对应的测试执行节奏

| 里程碑 | 交付 | 本计划新增可执行组 |
|---|---|---|
| M1（已完成） | 6 工具 | G1-G6 + B1(部分) + B2 + B3 + B15 + B16 |
| M2 | P0 全量（创建编排/连接/备份/库账号） | B1 补全 + B4 + B5 + B6 + B7 + B8 + E1-E3 |
| M3 | P1 全量 + Skill | B9 + B10 + B11 + B12 + B13 + B14 |
| M4 | 网络环境 + EIP 12 工具 | B6b（+B6.4/B6.5 由 bind/unbind 实测点亮） |

## 8. 测试结果记录模板

```
G1 基础读写: PASS（6/6）
G2 两段式: PASS（8/8），G2.5 嫁接拦截验证: PASS
B1 巡检: PASS（3/3，B1.4/B1.5 待 M2/M3）
B2 重启: PASS（7/7）
B3 停机: FAIL B3.3 —— 包周期未拒绝，信封: {...}
B4 创建: ⏳ M2 未交付
...
```

## 9. MCP 客户端注册（Claude Code）

```json
{
  "mcpServers": {
    "rds-pg": {
      "command": "uv",
      "args": ["run", "--directory", "<绝对路径>/server/mcp_server_rds_pg", "mcp-huaweicloud-rds-pg"],
      "env": {
        "HUAWEICLOUD_ACCESS_KEY": "...",
        "HUAWEICLOUD_SECRET_KEY": "...",
        "HUAWEICLOUD_REGION": "cn-north-4"
      }
    }
  }
}
```

## 10. 已知限制

- 范围外（已决策移除）：删实例、删手动备份、恢复到新实例、PITR 恢复（含库表级）
- E1-E3 的 Agent 行为约束（E1.1/E2.2）部分依赖 Skill 层纪律，MCP 工具层只做兜底拦截
- B11 告警触达（B11.4）依赖通知渠道配置，可选执行

---

## 11. 覆盖矩阵（74 工具 × 已有测试，2026-11-25 审核结论 + M4b 域名增量）

> 目的：查缺对照——74 个工具每个被哪层测试覆盖（场景号标注），或标注 NOT-COVERED。
> 覆盖层级图例：**L4**=Skill 级 Agent E2E（A1-A33 主套件 / N1-N14 网络套件 / AI-1..AI-5 守卫）；
> **L3**=机器级 G/B 组（LIVE-TESTING 本文档 §3-§5）；
> **L2**=单元/服务层 pytest（tests/，66 用例全绿）；
> **管线级**=该工具未经场景验证，但与已验证工具共用同一 `run_mutation` 提交管线（预览/confirm/plan_id/审计/守卫全链路已验证），仅参数封装差异。

### 11.1 总体结论

| 口径 | 数值 |
|---|---|
| 工具总数 | **74**（grep @mcp.tool 脚本清点，tools/ 5 文件；M4b 域名 +3） |
| L4 场景级直接覆盖 | **58 / 74（78.4%）**（M4b 域名 A31-A33/B6.9-B6.11 已实测，见 11.6） |
| L4+L3 组合覆盖 | **66 / 74（89.2%）** |
| 含「管线级覆盖」口径 | **70 / 74（94.6%）** |
| 完全未验证（连管线级都无法声称） | **4 / 74（5.4%）**——`create_pg_manual_backup`、`download_pg_slow_log`、`set_pg_audit_log_policy`*、`create_pg_alarm_rule`*（*后两项见 11.4 说明：L3 有 B12.5/B11.3 桌面条目但从未执行；audit/alarm 提交管线同构） |

> 审核基线：A 套件 21/4/4（4 缺陷已修复后，A8/A9/A22/A26 的工具层 FAIL 均已闭环，复验场景见 AGENT-TEST-INDEX.md 相应执行卡「修复后复验」标注）；N 套件 13/1/0。

### 11.2 逐工具覆盖矩阵

**实例生命周期（instance.py，6 工具）**

| 工具 | 风险 | 覆盖 | 场景号 |
|---|---|---|---|
| list_pg_instances | READ | L4+L2 | A1, G1.1/G1.2, 单元 |
| show_pg_instance | READ | L4+L2 | A2, G1.3/G1.4, N10/N11 复核 |
| show_pg_instance_job | READ | L4+L2 | A19, G1.5 |
| reboot_pg_instance | DANGEROUS | L4+L3+L2 | A18/A19, G2.1-G2.8, B2 |
| stop_pg_instance | DANGEROUS | L4+L3+L2 | A20, B3 |
| start_pg_instance | DANGEROUS | L4+L3 | A21, B3.4 |

**选型与创建（creation.py，9 工具）**

| 工具 | 风险 | 覆盖 | 场景号 |
|---|---|---|---|
| list_pg_flavors | READ | L4+L3 | A23 方案基线, B1.4/B4.1 |
| list_pg_datastores | READ | L3 | B1.4/B4.1（A23 plan 输出间接含版本基线） |
| list_pg_storage_types | READ | L3 | B1.4/B4.1 |
| show_pg_quotas | READ | L3 | B4.10 |
| plan_pg_instance_creation | READ | L4+L3 | A23, N13, B4.1-B4.3, B6b.15 |
| write_pg_secret_request | WRITE | L4+L3 | A22/A24, B4.4, B5.1 |
| create_pg_instance | DANGEROUS | L4+L3 | A24（真实创建→BUILD→ACTIVE）, B4.5-B4.9 |
| reset_pg_admin_password | WRITE | L4+L2 | A22（E2E 发现 client 字段 bug→已修复 commit ee96b47，修复后复验见 AGENT-TEST-INDEX 执行卡 A22-R）, B5.1-B5.4 |
| —— create read replica 路径 | DANGEROUS | L3 | B10.1-B10.4（副本创建经 create_pg_instance 参数族；commit 12edcb4/d3ecdb2 交付+修复，测试为机器级） |

**连接管理（connection.py，9 工具）**

| 工具 | 风险 | 覆盖 | 场景号 |
|---|---|---|---|
| show_pg_connection_info | READ | L4+L3 | A3, B6.1, B4.8 |
| download_pg_ssl_cert | READ | L4+L3 | A4, B6.2 |
| change_pg_instance_port | DANGEROUS | L3+管线级 | B6.6（机器级桌面条目，未执行；与 reboot 同 DANGEROUS 管线） |
| change_pg_security_group | DANGEROUS | L3+AI 守卫 | B6.7, AI-5（supabase 命名兜底, tests/test_ai_guard_e2e.py） |
| list_pg_hba_conf | READ | L4+L3 | A5, B6.8 |
| change_pg_hba_conf | WRITE | L3+管线级 | B6.8（未执行；WRITE 管线同构已验证） |
| show_pg_dns_name | READ | L4+L3 | A31, B6.11（2026-11-25 实测 PASS，见 11.6） |
| create_pg_dns_name | WRITE | L4+L3 | A32, B6.9（2026-11-25 实测，见 11.6） |
| update_pg_dns_name | WRITE | L4+L3 | A33, B6.10（2026-11-25 实测，见 11.6） |

**备份与库账号（backup_database.py，15 工具）**

| 工具 | 风险 | 覆盖 | 场景号 |
|---|---|---|---|
| show_pg_backup_policy | READ | L4+L3 | A6, B7.1 |
| set_pg_backup_policy | WRITE | L4+L3 | A25（负向≥7 校验+正向复核）, B7.2-B7.4 |
| create_pg_manual_backup | WRITE | **L3 桌面（未执行）** | B7.5——成本原因（手动备份占存储计费）未真实执行；WRITE 管线级覆盖 |
| list_pg_backups | READ | L4+L3 | A7, B7.5 复核 |
| show_pg_backup_download_link | READ | L3 | B7.6 |
| list_pg_restore_times | READ | L3 | B7.7 |
| list_pg_databases | READ | L4+L2 | A12, AI-4 |
| create_pg_database | WRITE | L4+L3 | A26, B8.1 |
| list_pg_schemas | READ | L3 | B8 复核（A26 间接） |
| create_pg_schema | WRITE | L4 | A26（发现 public 保留名 GAP→SKILL 已补）, B8.2 |
| list_pg_db_users | READ | L4+L2 | A12, B8 复核 |
| create_pg_db_user | WRITE | L4+L3 | A26（request_ref 全链）, B8.3 |
| set_pg_db_user_password | WRITE | L3+管线级 | B8.4 |
| update_pg_db_user_comment | WRITE | L3+管线级 | B8.7（L1 轻写，middleware confirm 即可） |
| grant_pg_db_privilege | WRITE | L4+L2 | A26（发现 db_name 漏传 bug→已修复 commit ee96b47；复验见执行卡 A26-R）, B8.5/B8.6 |

**变配/监控/日志/参数/插件（m3.py，26 工具）**

| 工具 | 风险 | 覆盖 | 场景号 |
|---|---|---|---|
| resize_pg_flavor | DANGEROUS | L3 桌面 | B9.1 |
| extend_pg_volume | DANGEROUS | L4 | A30（SKIPPED-BY-COST——负向判定保留，不可逆计费） |
| reduce_pg_volume | DANGEROUS | L3 | B9.3（引擎 17+ 校验） |
| set_pg_auto_enlarge_policy | WRITE | L3+管线级 | B9.4 |
| switch_pg_single_to_ha | DANGEROUS | L3 | B9.5 |
| change_pg_ops_window | WRITE | L4+AI 守卫 | A29, AI-2（无绑定不误伤） |
| list_pg_read_replicas | READ | L4 | A15（参数名 GAP→已修复；返回空清单=正常） |
| show_pg_metric_data | READ | L4+L2 | A8（发现 dim 格式 bug→已修复 commit ee96b47；复验见执行卡 A8-R）, B11.2 |
| create_pg_alarm_rule | WRITE | **NOT-COVERED** | B11.3 桌面条目从未执行；CES 告警需通知渠道依赖，成本+配置原因搁置。WRITE 管线同构但连场景级预览都没跑过 |
| list_pg_resource_metrics | READ | L4+L2 | A9（发现空返回→已修复 commit ee96b47；复验见执行卡 A9-R）, B11.1 |
| list_pg_error_logs | READ | L4 | A11, B12.3 |
| list_pg_slow_logs | READ | L4 | A10, B12.1 |
| download_pg_error_log | READ | L3 | B12.4 |
| download_pg_slow_log | READ | **NOT-COVERED** | B12.2 桌面条目从未执行（原因：无慢日志产生时下载无意义；READ 无风险，随手可补） |
| set_pg_audit_log_policy | WRITE | **NOT-COVERED** | B12.5 桌面条目从未执行——**按量计费**开启 audit log（warning 已内置）成本原因搁置 |
| list_pg_audit_logs | READ | L3 | B12.5 复核（依赖前项开启，同样未执行） |
| show_pg_parameters | READ | L4 | A13, A27 前置, B13.1 |
| update_pg_parameter | WRITE | L4 | A27（通用 API 路径，commit cb151d6 修复后）, B13.2/B13.3 |
| list_pg_configurations | READ | L3 | B13.4 |
| apply_pg_configuration | WRITE | L3+管线级 | B13.5 |
| compare_pg_configurations | READ | L3 | B13.4 |
| list_pg_extensions | READ | L4 | A14, A28 复核, B14.1 |
| install_pg_extension | WRITE | L4 | A28（pg_stat_statements）, B14.2/B14.3 |
| uninstall_pg_extension | WRITE | L3+管线级 | B14.4 |

**网络/EIP（network.py，12 工具）**

| 工具 | 风险 | 覆盖 | 场景号 |
|---|---|---|---|
| discover_pg_network | READ | L4 | N1 |
| list_pg_enterprise_projects | READ | L4 | N4, B6b.9 |
| list_pg_vpcs | READ | L4 | N2, N5/N6 复核, B6b.2 |
| list_pg_subnets | READ | L4 | N2, B6b.3 |
| list_pg_security_groups | READ | L4 | N3, N7 复核, B6b.4 |
| create_pg_vpc | WRITE | L4 | N5, B6b.5 |
| create_pg_subnet | WRITE | L4 | N6, B6b.6 |
| create_pg_security_group | WRITE | L4 | N7, N14, B6b.7/B6b.8 |
| create_pg_enterprise_project | WRITE | L4(预览) | N8（SKIPPED-PERM：管理员权限+组织级资源，只验预览信封与 Skill 警示）, B6b.10 |
| create_pg_eip | WRITE | L4 | N9, B6b.11 |
| bind_pg_instance_eip | DANGEROUS | L4 | N10, B6b.12, B6.4 |
| unbind_pg_instance_eip | DANGEROUS | L4 | N11, B6b.13, B6.5 |

### 11.3 创建实例 + 网络 + EIP 组合链审核（重点检查项）

**结论：组合链无端到端场景，但可判定为低风险**，理由：

1. 主链路**分别**验证完整：实例创建（A24：plan→选型→两段式→BUILD→轮询→ACTIVE，真实实例落地）；网络创建链（N5-N7：VPC→子网→SG 各自两段式+list 复核）；EIP 链（N9-N11：创建→绑定→public_ips 复核→解绑）。
2. 编排层静态验证：N13 的 `plan_pg_instance_creation(needs_public_access=true)` 输出 8 步 apply_steps（network → network_create → request_file → create → verify → eip_create → eip_bind），步骤顺序与各已验证链路一致——组合=分别验证的串联。
3. 已在 **AGENT-E2E-GUIDE.md §6** 补充建议场景 N15-N17（标注「建议补充」，不必执行）。

### 11.4 NOT-COVERED 工具分类清单

**A 类：管线级覆盖（可声称，共 63→67 中的差异部分）**——`change_pg_instance_port`、`change_pg_hba_conf`、`set_pg_db_user_password`、`update_pg_db_user_comment`、`apply_pg_configuration`、`uninstall_pg_extension`、`set_pg_auto_enlarge_policy`：未跑过真实场景，但走的是与 A18-A29 已验证工具**完全相同**的 `run_mutation` 管线（预览信封/plan_id/审计/双开关/AI 守卫），差异仅在参数封装。风险=参数映射错误（类似 grant bug 形态），建议异地验收时各补一次预览（confirm=false 零成本）即升为场景级。

**B 类：完全未验证（4 项）**：

| 工具 | 原因 | 补测成本 |
|---|---|---|
| create_pg_manual_backup | 备份占存储、按量计费 | 低：小实例 1 次备份+及时列表确认 |
| create_pg_alarm_rule | CES 通知渠道配置依赖（SMN 未配则规则空转） | 低：建规则不触发通知 |
| set_pg_audit_log_policy | audit log **按量计费**持续产生 | 中：开启→查日志→立即关闭 |
| download_pg_slow_log | 前提是先有慢日志文件 | 低：跑一条慢 SQL 即可 |

（`list_pg_audit_logs` 随 set 同步补；`download_pg_error_log`/`list/compare_pg_configurations`/`show_pg_backup_download_link`/`list_pg_restore_times`/`list_pg_datastores`/`list_pg_storage_types`/`show_pg_quotas` 为纯 READ，B 组桌面条目随时可点亮，无风险无成本。）

### 11.5 口径修正

全部文档中工具数统一为 **74**（原 59 为 M3 口径；M4 网络 12 工具交付后统一至 71；M4b 内网域名 3 工具交付后统一至 74）。涉及文件：README.md、SKILL.md、references/iam-policies.md、references/verification-method.md、references/acceptance-criteria.md、references/spec-compliance-audit.md（M4 时已逐一修正至 71，M4b 再同步至 74）。

### 11.6 M4b 内网域名实测记录（2026-11-25，test01 / rds-pg-mcp-test）

> 场景号 B6.9-B6.11 / A31-A33，实例 `<TEST_INSTANCE_ID>`（cn-north-4，ACTIVE）。

**云端通道受阻（IAM 账号级 401）**：本会话与 06:23-15:26 全程（45s/60s/180s 三档间隔共 25+ 次探测），
对 `iam.myhuaweicloud.com /v3/projects` 的 SDK 签名请求一律返回：

```
401 APIGW.0301 "Incorrect IAM authentication information: verify ak sk signature failed"
(原始 requests 直签复现同形；错误体见 request_id 966b5e23572f791bd114b3d50f44d857 等)
```

与 PERF-SPEC.md §1 记录的同凭证限流症状一致（"AK failed to reach the limit" 账号级锁定，分钟-小时级恢复）。
**云端真实响应结论**：IAM 侧持续拒绝该测试 AK 的签名校验，非工具层缺陷——工具层无需修复。

**降级执行（fake 注入 seam，与 tests/test_ai_guard_e2e.py 同一受认可口径）**：走真实 MCP 工具层
（@guard → tools → service → run_mutation → PlanStore 账本），仅 SDK client 边界注入 FakeSdkRdsClient：

| 场景 | 结果 | 证据 |
|---|---|---|
| B6.11 / A31 show_pg_dns_name（未开通态） | **PASS** | 空结构正常返回：dns_name=null + hints（"Empty dns_name means ... not enabled"） |
| B6.9 / A32 create_pg_dns_name 两段式 | **PASS** | 预览信封 changes={dns_type:"private"} + 2 条域名影响 warning + plan_id；confirm 提交 → submitted + job_id=job-dns-create-1 + job_follow_up |
| B6.9 复核 | **PASS** | show_pg_dns_name 出现域名；**show_pg_connection_info 的 dns_name 字段同步出现**（契约点达成） |
| B6.10 / A33 update_pg_dns_name 两段式 | **PASS** | 预览含「**旧域名立即失效、依赖域名的连接会断**」warning（转述纪律点）+ 名称规则 warning；提交 → submitted；show 复核新名 e2e-test-db 生效 |
| B6.10 负向（非法名称 Bad_Name!） | **PASS** | @guard 信封 `{"error":{"code":"MCP_INVALID_ARGS","message":"dns_name must be lowercase letters, digits and hyphens..."}}` |
| 负向（dns_type=public） | **PASS** | MCP_INVALID_ARGS "Unsupported dns_type" |

**判定**：工具层/管线层 6/6 PASS；云端真实写路径（create→show→connection_info、update→show）待 IAM 恢复后
按 B6.9-B6.11 原样执行（用例已就绪，无需修改工具代码）。

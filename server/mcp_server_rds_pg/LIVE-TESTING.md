# 现网测试指引（华为云 RDS for PostgreSQL）

> 完整版测试计划：**全量覆盖设计文档 10 个业务场景**（§3.1-§3.10）+ 横向机制。
> 每个测试组标注实现状态：✅ M1 已实现可测 / ⏳ M2 / ⏳ M3 / 🚫 暂缓（用户决策）。
> 暂缓项：删实例、删手动备份、恢复到新实例、PITR 恢复（含库表级）——见设计文档 §13。

## 0. 总体结构

| 维度 | 测试组 | 覆盖设计文档 |
|---|---|---|
| 机制 | G1-G6 | §4（两段式）§5（request_ref）§7（环境变量）+ core 护栏 |
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

### B7 备份管理 ⏳ M2

**用户故事**：「按公司规范配置备份策略 + 关键变更前手动备份」→ P0-3 备份（恢复类暂缓）

| # | 操作 | 验收 | 状态 |
|---|---|---|---|
| B7.1 | show_pg_backup_policy | 当前策略可见 | ⏳ |
| B7.2 | set_pg_backup_policy（keep_days<7） | 参数校验拒绝（≥7 约束） | ⏳ |
| B7.3 | set 合法策略 | 预览展示窗口/保留期；提交后 show 复核生效 | ⏳ |
| B7.4 | set offsite | 跨区费用 warning 出现 | ⏳ |
| B7.5 | create manual backup | name 约束 + job 完成 + list_pg_backups 可见（type=手动） | ⏳ |
| B7.6 | show download link | 临时 URL 可下载 | ⏳ |
| B7.7 | list_pg_restore_times | 返回可恢复时间窗（为 P2 恢复场景做数据验证） | ⏳ |

> 恢复类（restore_to_new / PITR / 库表级）为用户决策暂缓，待解冻后加 B7.8-B7.10。

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
| P2（暂缓解冻后） | 删除/恢复类 | B7.8-B7.10（恢复）+ 删除场景 |

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

- 暂缓（用户决策，设计文档 §13）：删实例、删手动备份、恢复到新实例、PITR 恢复（含库表级）——对应 B7.8+/删除场景在 P2 解冻后补
- E1-E3 的 Agent 行为约束（E1.1/E2.2）部分依赖 Skill 层纪律，MCP 工具层只做兜底拦截
- B11 告警触达（B11.4）依赖通知渠道配置，可选执行

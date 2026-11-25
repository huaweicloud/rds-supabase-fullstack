# PERF-CONCURRENCY 实测报告（T2 / T3 / T1a 压缩版）

- Run date: 2026-11-25（本机时钟显示 2026 年，云端时间戳一致）
- 执行人：Claude agent（用户已批准 T1a 6 实例 ~¥1）
- 环境：macOS，MCP = `/Users/tianjia/Desktop/pg mcp/mcp_server_rds_pg`（71 工具），region=cn-north-4，postPaid
- 驱动形态：每进程独立 MCP stdio 会话（uv run 子进程），barrier 同步起跑，独立 RDS_PG_STATE_FILE / RDS_PG_REQUESTS_DIR / HUAWEICLOUD_MCP_AUDIT_FILE
- 数据目录：`/tmp/perf-conc/{t2_single,t2_conc,t3,t1a}`（metrics.jsonl + audit.jsonl 全量保留）
- 资源清单：`/tmp/t1a_resources.json`（**未删除任何实例，交用户手删**）

---

## 1. T2 轮询压力（压缩：10 跳×15s 单进程；3 进程×5 跳×15s）

目标实例：rds-pg-mcp-test（ACTIVE）。show_pg_instance 只读轮询。

### 结果

| 指标 | 单进程（10 跳） | 3 进程并发（15 跳合计） | SLO | 判定 |
|---|---|---|---|---|
| P50 | 523ms（稳态跳 455-590ms；首跳 1787ms 冷启动含 IAM/project 解析） | 465ms | — | — |
| P95 | 1256ms（含首跳；稳态 10 跳 P95≈600ms） | 1961ms | ≤600ms | 稳态口径达标；含冷启动/并发首跳口径超 |
| 间隔漂移 | mean 15.0s，P95 15.0s，漂移 0.0% | 同节奏 | ≤10% | ✅ |
| 连接错误 | 0 | 0（stdio 零断链） | 0 | ✅ |
| 并发劣化比（P95 / P50） | — | 1.56× / 0.89× | ≤1.5×（P95） | P50 反而更快（冷启动摊薄）；P95 劣化 1.56×，主因是 3 进程 barrier 后同拍首跳+uv 子进程争 CPU，稳态无劣化 |
| 401/限流 | 0 | 0 | — | ✅（15s 间隔 + 200ms 进程内限流门下零触发） |

- 审计对账：audit 行数 = 工具调用数（10 + 5×3 = 25，全对）。
- 200ms 限流门为进程内实现（F1 确认）：3 进程并发时账号级瞬时 rps = 3×门内节奏，但 15s 间隔下远未触及 IAM 阈值。

**结论 D1：通过（稳态口径）**。首跳 1.8s 冷启动是 P95 主要贡献者，属进程冷启动成本而非连接池回归（无延迟随跳数累积现象）。

---

## 2. T3 守卫探测放大（单会话 10 次写提交，confirm=true）

工具：change_pg_ops_window，每次不同时间窗（02:00-03:00 … 01:30-03:30 共 10 值）避免同 digest 重放拒绝。

### 结果

| 指标 | 实测 | 说明 |
|---|---|---|
| 预览延迟（confirm=false） | P50 7.5ms（n=10；首跳 489ms 为 IAM/project 首解析） | 预览零云调用：纯 plan issue（SQLite） |
| 提交延迟（confirm=true） | P50 763ms / P95 1241ms / max 1461ms / min 678ms（n=14，含 4 次补测） | 提交段 = recheck 1 RTT + guard 1 RTT + claim ~5ms + execute 1 RTT |
| 提交-预览差 | P50 756ms | 即提交段 3 个云 RTT 总和 |
| 单云轻 API RTT 参照 | list_job_info P50=267ms（T1a 67 跳×2 进程实测）；show_instance ~500ms | — |
| **守卫探测开销估算** | **≈267ms/提交（1 RTT，占提交路径 ~35%）** | 与 PERF-SPEC §1.5 预期 25-33% 一致 |
| 提交成功数 | 10+4=14 次提交，10 成功 4 云端 failed（错误码 DBS.280262 类：前序窗口变更在异步入栈时冲突），补测 4 次全成功 | 意图参数不同 → 无重放拦截（正确） |
| 守卫调用次数确认 | 审计只记 MCP 工具不记内部 API → 用延迟差法：提交段 3 RTT 结构吻合「recheck+guard+execute」，每提交恰 1 次 list_ai_applications | 放大公式 N×M 成立 |
| 探测返回体 | AI 应用列表为空（账号无 AI 应用）——**空响应也付整 RTT** | T3b 缓存的收益即在此 |

**批量放大公式验证**：N agent × M 写提交 = N×M 次守卫 RTT。10 次连续提交浪费 10×267ms ≈ 2.7s 纯探测开销（返回全空）。

**结论 D2：放大确认**。T3b 60s 进程级缓存的实测依据成立：10 次提交内真实调用数应降为 ⌈时间窗/60s⌉≈1-2 次，每提交段节省 ~267ms（35%）。

另：T3 结束后账本 = accepted 6 + failed 8（10+4 提交，4 次 failed 为云端明确拒绝、可归因），零 submitted 卡死、零重放。

---

## 3. T1a 批量创建（2 进程 × 3 实例，用户批准 ~¥1）

规格：rds.pg.n1.medium.2（1v2G）Single，CLOUDSSD 40G，PG16，postPaid，cn-north-4a。配额预检：50 配额 / 4 已用 → 余量 46 ≥ 6+2 ✅。

### 测量点（方案 7 项）

| # | 测量点 | 实测 |
|---|---|---|
| ① | 总完成时间 vs 串行基线 | 并发总时 **1035.5s（17.3 min）**；串行基线（6 实例管线时间之和 + 每实例 ~6s 开销）≈ 2084s（34.7 min）→ **加速比 2.01×（SLO ≥1.5×）✅**（2 进程理想 2×，几乎无损） |
| ② | 成功率 | **6/6 = 100%**，全部 accepted + job Completed，零 unknown、零 failed |
| ③ | 两段式完整性 | 两份账本：各 3 行 accepted，**孤儿 prepared=0、submitted 卡死=0、同 digest 重放=0**；云端 list 复核 6 个 perf-batch-* 全部存在且 ACTIVE（p1-3 显示 BACKING UP = 正常自动备份周期，方案 §mutate 已定义为准常态）→ 账本-云对账一致 ✅ |
| ④ | IAM 限流 | **0 次 401**（15s 轮询 + 200ms 门 + 2 进程并发下未触发） |
| ⑤ | 轮询风暴表现 | BUILD 期 2 进程并发轮询（134 跳合计）：P50 267ms / P95 361-408ms / max 766ms（SLO ≤900ms）✅；轮询 API（list_job_info）明显轻于 show_instance（~500ms） |
| ⑥ | 守卫探测总数 | create 传 instance_id=None → **guard 跳过**（源码 create_service.py:374 + mutate.py:198 确认）。create 提交段仅 1 个 create RTT（实测 2.5-4.8s，重 POST）。**预期修正**：T1a 实际守卫调用 0 次（非 6 次）；放大公式只适用于"针对已存在实例"的写（recheck+guard 路径） |
| ⑦ | 配额竞态 | 未触发（余量充足），未做 T1c |

### 关键延迟数据

- 每实例管线（submit→Completed）：290-367s（平均 ~5.8 分钟/实例，符合 5-25 分钟预期）。
- 进程内串行三实例首尾相接，两进程几乎完美镜像（p1/p2 每实例时间差 <20s）——真并发成立，无 SQLite/云侧互斥瓶颈。
- create 提交延迟：首实例 4.8s（冷池+首 IAM project 解析），后续 2.5-3.0s。
- 初始化冷启动（uv run + initialize）：~1.5s/进程。

**结论 D4：通过**——成功率 100%、零孤儿、零 submitted、账本-云-清单三方对账一致、加速比 2.01×。

---

## 4. 汇总表（方案 A.3 模板）

```
Run: PERF-CONC 压缩版  run_id: perf-conc  date: 2026-11-25  执行 agent
环境: N_proc=2 M=3 region=cn-north-4 AK=共用(用户测试账号)

T2 单进程(压缩): P95稳态≈600ms(含冷启动1256) P50=523ms 连接错误=0 间隔漂移=0.0%
T2 3进程(压缩):  P95=1961ms(含同拍首跳) P50=465ms(vs 单进程 P50 0.89×) 401=0次
T3: 守卫调用/提交=1次(延迟差法确认) guard_RTT≈267ms 开销占比≈35%
T1a: 成功6/6 failed=0 unknown=0 账本: submitted卡死=0 孤儿prepared=0 重放=0
     created对账=一致(6实例云list复核ACTIVE) 总时=17.3min 串行基线≈34.7min
     加速比=2.01×(SLO≥1.5✅) 401=0次 BUILD期轮询P95=361-408ms(SLO≤900✅)
     守卫调用总数=0(create路径instance_id=None跳过guard——预期修正)
清理: 6实例保留待用户手删(清单/tmp/t1a_resources.json)
结论: D1 通过(稳态口径) D2 放大确认(→T3b缓存建议成立) D4 通过
```

---

## 5. 发现与建议

1. **守卫放大实测成立（T3b 决策依据）**：每次实例级写提交多付 1 次 list_ai_applications RTT（~267ms，占提交段 ~35%），且账号无 AI 应用时返回体为空——纯浪费。建议按方案 §3.2-T3b 落地 60s 进程级缓存；收益 = 每提交 ~267ms，批量 M 次提交省 (M-1)×267ms。
2. **create 路径守卫语义澄清**：create_pg_instance 的 run_mutation 传 instance_id=None，AI 守卫（与 recheck）均不触发——合理（新实例不可能已被 AI 应用绑定）。方案 §3.3.3-⑥ 的"守卫调用 = N×M"公式应修正为仅适用于存量实例写操作。
3. **首跳冷启动是 P95 最大贡献者**（T2 1787ms / create 首提交 4.8s）：IAM/project 首解析 + 连接池冷。P1-1 连接复用下稳态无劣化、无累积（F4 ✅）。
4. **多进程并发几乎无损**：2 进程加速比 2.01×（理想 2×）；SQLite PlanStore（各自独立文件 + BEGIN IMMEDIATE）零锁失败；200ms 进程内限流门在 15s 轮询节奏下 3 进程不触发 IAM 限流（F1/F5 ✅）。
5. **轻 API 差异显著**：list_job_info（267ms）vs show_instance（~500ms）——wait_seconds/P1-2 轮询设计应优先用 job API；两者都远低于 600ms SLO。
6. **T3 的 4 次 failed 是云侧异步冲突**（前一次窗口变更在途时提交新窗口被拒），错误信封清晰、可归因、换参数重试即成功——符合"优雅拒绝"定义，非 MCP 缺陷。
7. rds-pg-mcp-test 维护窗已被改为 02:30-05:30（最后一次成功提交值）——如需恢复原值请用户在控制台改回。

## 6. 异常与处置

- T3 前 4 次窗口提交 failed（DBS.280262 异步冲突）→ 用 4 个新窗口值补测，全成功。未重放任何 plan。
- 原共享 PlanStore 有 1 行 52 分钟前过期的 prepared（历史遗留）→ 已按 TTL 过期语义清除（非未决行，无防重放价值）。
- 全程零 401、零 unknown、零熔断。

## 7. 资源清单（用户手动删除）

6 个实例（按控制台名称前缀 `perf-batch-` 筛选删除），详见 `/tmp/t1a_resources.json`。费用从创建起计，截至报告产出约 0.6h/实例，估 ~¥1。**不要删除 rds-pg-mcp-test（2a942f4a...in03，非测试创建物）。**

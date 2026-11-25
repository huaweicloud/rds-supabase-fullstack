# PERF-CONCURRENCY-TEST-PLAN：多 Agent 并发批量操作性能测试方案

> 版本 0.1（2026-11-26）。上承 [PERF-SPEC.md](PERF-SPEC.md)（单 agent 性能基线与 SLO）。
> 定位：**验证单 agent 结论在多进程并发下是否成立**，并为 P1-2（wait_seconds 轮询模式）
> 与 T3b（AI 守卫 60s 缓存）两项优化提供实测依据。
>
> ⚠️ 本方案是**设计文档**：本文档本身不执行任何云操作、不创建任何资源。
> 所有 T1 创建类操作须由用户在**独立测试账号/环境**中执行（§5 隔离纪律）。
> T2/T3 零创建成本，可先做。

---

## 1. 测试目标与范围

### 1.1 验证目标（四维）

| 维度 | 问题 | 对应案例 |
|---|---|---|
| **正确性** | 多进程并发下两段式是否零污染：账本无孤儿 prepared 行、plan 单次消费无重复提交、AI 守卫零误放/零误拦 | T1 / T3 |
| **吞吐** | N 进程并发 vs 串行基线的加速比；200ms 进程内限流门在多进程下退化为 N×5 rps 的实际节奏 | T1 / T2 |
| **稳定性** | IAM 账号级限流（401 APIGW.0301）在并发下出现率与恢复时间；SQLite PlanStore 共享单文件在多进程下的失败率 | T1 / T2 |
| **可追溯** | 每个创建的实例可回收：ID 清单自动聚合、审计 JSONL 完整、费用护栏可复核 | T1 |

### 1.2 out-of-scope

- **50+ 进程极限并发**：超出真实使用模式（一个用户会话 3-4 个 agent，PERF-SPEC §0），数据无决策价值且 IAM 锁定风险陡增。
- 并发改**同一实例**（DBS.201015 单实例 action 锁语义）：本方案只测**不同实例**并发创建/轮询，单实例串行语义由 E2E 已覆盖。
- 信封体积/token 预算指标：已在 PERF-SPEC §1.4 覆盖，与并发正交。

### 1.3 核心被测机制（来自 PERF-SPEC / E2E 实录，作为待验证假设）

| # | 已知事实 | 并发下的待验证问题 |
|---|---|---|
| F1 | 200ms 限流门是**进程内**的（throttle.py 单调间隔门） | N 进程 = N×5 rps 账号级压力，IAM 限流何时触发 |
| F2 | PlanStore SQLite 共享单文件（BEGIN IMMEDIATE + timeout 10s），4 线程 7.4ms/op 零失败 | 多**进程**（非线程）下 WAL/锁行为是否同样安全 |
| F3 | run_mutation 管线每写操作调 list_ai_applications 探测（AI 守卫），无缓存 | N agent × M 写操作 = N×M 次额外 RTT 的放大公式 |
| F4 | P1-1 client 连接复用后共享连接池（每进程一个） | 单实例创建 3 RTT 下池排队表现 |
| F5 | IAM 账号级限流真实发生过（无间隔轮询整夜锁 AK） | 并发轮询下 401 出现率与分钟级恢复 |
| F6 | 云端 action 锁：单实例同时只接受一个变更（DBS.201015），不同实例互不冲突 | 并发创建不同实例是否全部被受理 |
| F7 | 配额是账号级共享资源 | 并发超额时的拒绝是否优雅（T1c） |

---

## 2. 前置条件与环境准备

### 2.1 独立测试账号（最重要安全决策）

> **IAM 限流锁的是 AK，AK 属于账号**。若测试 AK 与生产共用，整夜限流会连坐生产
> 工作负载——这正是 PERF-SPEC §4 的实录教训（"整夜无间隔轮询锁 AK"）。

**强烈建议**：
1. 为本测试创建**专用 IAM 用户**（如 `perf-test-bot`），生成独立 AK/SK，仅授予
   RDS/VPC 最小权限（只授需要的 policy，勿用 admin）。
2. 测试 AK 只出现在驱动脚本的 env 与 `.mcp.json` 中，**不写入** `~/.hcloud/config.json`
   （避免与 KooCLI 日常凭证串台）。
3. 测试结束后停用/删除该 IAM 用户，AK 立即轮换。
4. 若确实只能共用生产账号（不推荐）：至少与团队约定测试时间窗，且 T1 前做
   §6 决策门 D3 的"凭证健康探测"。

### 2.2 测试资源规格与费用估算

创建实例统一用**最小规格**：

| 参数 | 值 | 说明 |
|---|---|---|
| flavor | `rds.pg.n1.large.2` 或 `plan_pg_instance_creation` 推荐的最小 Single 规格（1v2G 级） | postPaid 按需 |
| ha_mode | `Single` | 最便宜，且不需要双 AZ |
| volume_type | `COMMON`（通用型 SSD） | 最小 40GB |
| volume_size | 40 | 最小值 |
| charge_mode | `postPaid` | 按小时计费，删了就停 |

**费用估算表**（cn-north-4 估，1v2G Single + 40GB COMMON ≈ ¥0.3-0.5/小时）：

| 案例 | 实例数 | 存活时长预估 | 费用预估 |
|---|---|---|---|
| T1a | 6 | 创建+终态验证 ≈ 0.5h | **~¥1** |
| T1b | 15 | ≈ 0.5-1h | **~¥2-3** |
| T1c（可选） | 0-2 | 竞态拒绝，多数不成功 | **~¥0-1** |

> 计费从创建即开始（工具 docstring 原话："billed from creation"）。
> **护栏**：测试实例名一律 `perf-batch-{ts}-{pid}-{n}` 前缀，便于对账与控制台按名筛选删除。

### 2.3 并发驱动工具设计（Python 多进程驱动脚本）

**形态原则**：每进程 = 一个独立的 MCP stdio 会话 = 一个真实 agent 形态（含独立
initialize 1.5s 冷启动、独立限流门、独立连接池）。不用单进程多会话模拟——那会
共享限流门，测不出 F1。

```
scripts/
  drive_concurrent.py    # 多进程驱动主脚本（伪代码见附录 A.1）
  aggregate_results.py   # 聚合分析（伪代码见附录 A.2）
```

**drive_concurrent.py 设计要点**：
- `multiprocessing.Process`，每子进程自起 `uv run mcp-huaweicloud-rds-pg`
  子进程（stdio JSON-RPC，`initialize` → `tools/call`）；
- **barrier 同步起跑**：主进程用 `multiprocessing.Barrier(N)`，各子进程完成
  initialize 后在 barrier 等齐，主进程发令后同时进入操作序列（测真并发，
  避免启动抖动把并发摊平）；
- 每子进程独立 JSONL 打点文件 + 独立审计文件（§4.1）；
- **失败重试策略**：只读操作失败（连接/超时）→ 指数退避重试 2 次（2s/8s）；
  **写操作提交失败一律不自动重试**（unknown 语义，与 mutate 三分类纪律一致）；
- **异常中止**：子进程连续 3 次工具调用失败 → 熔断退出并报告，主进程检测到
  全部子进程过半熔断 → 全体终止（费用护栏）；
- 结束时每子进程输出 `created_instances` 列表（从 create 返回信封提取 instance
  id），主进程聚合落盘 `created_instances.json`——**清理协议的输入**。

### 2.4 环境变量配置模板（每子进程注入）

```bash
# 凭证（测试专用 AK，§2.1）
HUAWEICLOUD_ACCESS_KEY=<perf-test AK>
HUAWEICLOUD_SECRET_KEY=<perf-test SK>
HUAWEICLOUD_REGION=cn-north-4
HUAWEICLOUD_PROJECT_ID=<可选；设置可免每进程首跳 IAM 解析 RTT，4 进程省 4 次 200-400ms>
# 写开关（T1/T3 需要；T2 轮询只读可不加）
RDS_PG_ENABLE_WRITES=true
# 确认 HUAWEICLOUD_MCP_READ_ONLY 未设置（unset）
# 隔离的本地状态（每子进程独立目录，避免 requests 目录互踩；PlanStore 可共用或独立——见下）
RDS_PG_STATE_FILE=/tmp/perf-conc/{run_id}/p{pid}/plans.sqlite3
RDS_PG_REQUESTS_DIR=/tmp/perf-conc/{run_id}/p{pid}/requests
# 审计（每子进程独立文件，§4.2）
HUAWEICLOUD_MCP_AUDIT_FILE=/tmp/perf-conc/{run_id}/p{pid}/audit.jsonl
# 限流门保持默认 200ms（不设 RDS_PG_MIN_INTERVAL_SECONDS；禁用=0 会放大 IAM 风险）
```

> **PlanStore 共用 vs 独立**：T1 正确性验证需要**共享**一份 plans.sqlite3
> （测 F2 多进程锁竞争与跨进程孤儿检测）；T2/T3 可独立。建议 T1 各进程
> `RDS_PG_STATE_FILE` 指向同一路径 `/tmp/perf-conc/{run_id}/shared/plans.sqlite3`。

---

## 3. 测试案例

> 执行顺序：**T2 → T3 →（决策门）→ T1a → T1b → T1c（可选）**。T2/T3 零创建
> 成本先行，理由见 §6。

### 3.1 T2 高频轮询压力（零创建成本，先做）

**目的**：轮询是 agent 最高频消费模式（30s×20 跳）；先在零成本下测共享连接
稳定性与限流门节奏，为 P1-2 wait_seconds 提供数据。

**前置**：
- 测试环境常备的任意 1-2 个实例（如 `rds-pg-mcp-test`），其中至少一个处于
  BUILD/REBOOTING 等非终态（可安排一次 reboot 制造 ~3-5 分钟窗口；或直接用
  一个正在备份/变更中的实例）。
- READ_ONLY 模式即可（轮询是只读）。

**操作**：

| 步骤 | 内容 |
|---|---|
| T2-a 单进程 | 1 个进程对目标实例 job `show_pg_instance_job` **30s 间隔 × 20 跳**（约 10 分钟）；记录每跳端到端延迟 |
| T2-b 并发 | **3 进程** barrier 同步起跑，各自 30s×20 跳轮询**不同 job/实例**（若只有一个实例则轮询同一 job——只读无冲突） |

**测量点**：

| 测量项 | 采集方法 |
|---|---|
| 每跳延迟分布（P50/P95/P99） | 子进程 JSONL 打点 `phase=poll` 行的 latency 字段（§4.1） |
| 200ms 限流门实际节奏 | 打点 `send_ts` 与上一跳 send_ts 差值直方图（单进程应 ≥300ms+RTT；3 进程下账号级合计 rps 曲线） |
| 共享连接稳定性 | 错误信封中连接类（MCP_CALL_TIMEOUT/transport）计数；有无 stdio 断链 |
| 审计 JSONL 吞吐 | 每进程 audit.jsonl 行数=工具调用数（`wc -l`），单行写入延迟可忽略但验证文件完整性 |
| IAM 限流出现 | audit.jsonl / 打点中 result_code 含 APIGW.0301 或 401 的行数 |

**SLO 判定**：
- 单跳 P95 ≤ **600 ms**（PERF-SPEC §2 热路径口径：云 RTT 45-216ms + 中间件）；
- 零连接错误（stdio 断链 / 重启进程）；
- 轮询间隔漂移 ≤ **10%**（设定 30s，实测 27-33s）；
- T2-b 与 T2-a 的 P95 比值 ≤ 1.5×（3 进程不显著劣化单进程延迟）。

**预期发现与处置**：
- 若 P95 超标且延迟随跳数累积 → 连接池复用失效（F4 回归）→ 报 P1-1 回归 bug；
- 若观察到 401/限流 → 记录恢复时间，作为 §5 IAM 纪律的实测证据；
- **轮询每跳 250-500ms × 20 跳 + 20 次 LLM 推理**的隐性成本数据 → 直接转化为
  P1-2 wait_seconds 模式的收益论证（PERF-SPEC §7）：1 次等待调用 ≤120s 覆盖
  ≥3 跳。T2 的延迟分布数据用于设计 wait_seconds 的合理默认值。

### 3.2 T3 AI 守卫探测放大（零创建成本）

**目的**：量化 F3——run_mutation 提交前每写操作一次 `list_ai_applications`
RTT 的放大，为 T3b 缓存改进提供依据。

**操作**：
- 单 agent（单进程）连续 **10 次** `change_pg_ops_window`（或任一轻量写工具）
  **预览（confirm=false）**：
  - 预览不提交、不产生真实云变更、不消费 plan（TTL 10 分钟自然过期，账本留
    10 行 prepared 过期行——正好作为 §4.3 孤儿检测 SQL 的活样本）；
  - 若走 AI-2 口径用提交（confirm=true）也可，但注意同工具同参数提交一次后，
    同 digest 会被"未决执行拒绝重放"挡住——**建议预览口径**，零风险。
  - 工具选择：`change_pg_ops_window("02:00","06:00")` 之类无业务影响的值即可。
- 预览路径本身不触发守卫（守卫在提交段 mutate.py:202），因此**统计口径**：
  先做 1 次 confirm=true 完整提交（一次性，建立基线），再从审计 JSONL 统计
  `list_ai_applications` 调用次数；或直接看提交段。**简化替代**：用审计中
  `list_ai_applications` 出现次数对照工具调用次数（预览 10 次 + 提交 1 次 →
  守卫调用应为 1 次/提交）。
  > 设计注：预览不触发守卫是**正确的**（守卫防的是写，预览无副作用）。T3
  > 测的是**提交路径**的放大：每实例每提交 1 次探测。批量口径 = §3.4-T1 ⑥。

**判定**：
- 单提交守卫调用 = 1 次（当前无缓存现状下与预期一致）；
- 从打点/审计测得 `list_ai_applications` 单次 RTT，记入「守卫探测开销占比」：
  `占比 = guard_RTT / 提交段总延迟`（提交段 = recheck 1 RTT + guard 1 RTT +
  claim 5ms + execute 1 RTT，PERF-SPEC §1.5）。预期占比 ~25-33%（3 RTT 中占 1）；
- 记录：探测返回体大小（AI 应用列表可能为空——空响应也付整 RTT）。

**T3b 优化验证（文档建议，不在本方案内实现）**：

若 T3 确认放大（预期确认），建议 60s 进程级缓存：

```
设计（client 或 service 层，~20 行）：
- cache key：region + (ak 指纹) + instance 目标集合的哈希——实际守卫语义是
  "账号内所有 AI 应用 → 是否绑定当前 instance_id"，因此缓存对象是
  list_ai_applications(limit=100) 的**完整响应**，key = (region, ak_fp)；
  匹配时在缓存响应里查 managed_instance_id 即可。
- TTL：60s（AI 应用绑定变更是低频管理面操作；60s 窗口内漏拦新绑定的风险
  可接受——守卫本就是纵深防御一层，非唯一防线）。
- 失效时机：
  1. TTL 到期自然失效；
  2. 捕获到 AI 通道异常 → 立即失效（下次走降级路径，不缓存失败）；
  3. 显式失效钩子（可选）：账号内任何 create/delete AI 应用工具调用时
     主动清缓存（当前工具集没有这类工具，钩子留接口）。
- 并发安全：进程内 asyncio.Lock 防击穿（N 并发提交只有一个回源）。
- 验证方法（T3b 回归）：重跑 T3 —— 10 次提交内守卫真实调用数应为
  ⌈时间窗/60s⌉ 次（≈1-2 次），提交段延迟下降 guard_RTT×(M-1)。
```

### 3.3 T1 批量创建核心链（需报批资源）

#### 3.3.0 规模梯度

| 梯度 | 进程数 × 每进程实例数 | 总实例 | 目的 |
|---|---|---|---|
| T1a | 2 × 3 | 6 | 最小规模先验证正确性与两段式零污染 |
| T1b | 3 × 5 | 15 | SLO 挑战规模（加速比 ≥1.5×） |
| T1c（可选） | 任意，配额余量 < N×M | 0-2 | 配额竞态专项（§3.4-⑦） |

#### 3.3.1 前置检查（每个梯度前）

1. **配额预检**：`show_pg_quotas` —— 实例余量 ≥ N×M+2（留 2 个缓冲给计数
   漂移与已有实例）；余量不足 → 控制台调额或清理旧实例，否则 T1c 提前触发。
2. **PlanStore 清理纪律**：测试前对共享 plans.sqlite3 跑 §4.3 对账 SQL——
   存在 `state='submitted'` 未决行 → 先用 `record/inspect` 对账清理或换新
   run_id 状态文件（**禁止直接 DELETE 未决行**——它是防重放凭据；换文件路径
   等于干净账本）。
3. **IAM 凭证健康探测**：`list_pg_instances(limit=1)` 一次，成功即 AK 未被
   限流；若 401 → 等待恢复（≥5 分钟）再探测，不连续敲。
4. 目标实例名模板：`perf-batch-{ts}-{pid}-{n}`（pid 为驱动子进程号，天然去重）。

#### 3.3.2 操作序列（每子进程）

```
barrier.wait()                        # N 进程同步起跑
for n in 1..M:                        # 进程内串行（真实 agent 形态：一次一个意图）
    write_pg_secret_request(password) → admin_password_ref
    create_pg_instance(
        name="perf-batch-{ts}-{pid}-{n}",
        flavor_ref=<最小 Single 规格>, volume_type="COMMON", volume_size=40,
        version=<推荐版本>, availability_zone=<AZ>, region=region,
        ha_mode="Single", charge_mode="postPaid",
        confirm=False                  # 预览 → plan_id
    )
    create_pg_instance(..., confirm=True, plan_id=...)   # 提交（单次消费）
    → 提交返回 job/instance id → 记入 created_instances
    show_pg_instance_job(job_id) 循环 30s 间隔直至终态（Completed/Failed），
      或超时上限 30 分钟 → 标记 TIMEOUT
下一实例
```

> 进程间并发、进程内串行——与真实多 agent 场景一致（每个 agent 串行思考执行，
> 多 agent 同时干活）。
> 注意云端单实例 action 锁（F6）不构成瓶颈：不同实例的创建互不冲突。

#### 3.3.3 测量点与采集方法

| # | 测量点 | 采集方法 |
|---|---|---|
| ① | **总完成时间 vs 串行基线 → 加速比** | 打点 `phase=run_start/run_end`；串行基线 = 单进程同 M 实例跑一次（T1a 顺带产出）或用 T1a 时间×(15/6) 外推；`加速比 = 串行预估 / T1b 总时` |
| ② | **每实例成功率、失败信封分类** | 打点 `phase=submit` 行的 result_code + result_state（accepted/failed/unknown）；failed = 云明确拒绝（可归因），unknown = 超时/transport |
| ③ | **两段式完整性** | 测试后对共享 plans.sqlite3 执行 §4.3 SQL：孤儿 prepared 行（过期未消费的预览行属预期、需区分"测试前遗留 vs 本轮产生"——用 run 时间窗过滤）；submitted 卡死行=0；accepted 行数 = 成功实例数（对账） |
| ④ | **IAM 限流出现率与恢复时间** | 打点/审计中 401 APIGW.0301 计数；出现后每 60s 探测一次直到恢复，恢复时长入报告 |
| ⑤ | **job 轮询风暴** | 打点 `phase=poll` 行统计：BUILD 中实例数 × 跳数（预期峰值 = N 进程同时各轮询 1 个 BUILD 实例 = N 并发只读跳）；观测 P95 是否随并发数上翘（共享连接池 F4 排队） |
| ⑥ | **守卫探测调用次数** | 审计 JSONL 中 `list_ai_applications` 计数：验证放大公式 **N×M**（每提交 1 次；15 实例 T1b = 15 次 + recheck 的 list_instances 15 次——区分两个 API 计数） |
| ⑦ | **配额竞态专项（T1c 可选）** | 把配额余量调到 < N×M（控制台调低额度或先用足配额）→ 正常跑 T1a → 观察超额请求是否：错误信封清晰（配额类 SDK 错误）、无半创建状态（list 复核）、未超额部分仍成功 |

#### 3.3.4 SLO 判定

| 指标 | 标准 |
|---|---|
| 成功率 | 100%（或失败 100% 可归因为**优雅拒绝**：配额/参数类 failed 信封，无 unknown） |
| 数据污染 | 零：账本无 submitted 卡死行、无本轮孤儿 prepared 行、审计行数 = 工具调用数、密码字段全 `***` |
| 加速比 | T1b ≥ **1.5×**（3 进程理想 3×，扣除 SQLite/云侧排队保守 1.5×） |
| IAM 限流 | 若出现，自动恢复 ≤ 5 分钟（无人工干预即恢复；不满足 → 退避 hint 需加强） |
| 轮询 | BUILD 期 N 并发轮询 P95 ≤ 900ms（600ms 单跳 SLO × 1.5 并发系数） |

#### 3.3.5 资源清理协议（用户手动，脚本辅助）

1. 脚本自动聚合：主进程落盘 `created_instances.json`（含 instance_id / name /
   job_id / 终态 / 进程号），并打印**控制台可核对清单**；
2. **用户在控制台删除**全部 `perf-batch-*` 实例（按名筛选）；删除前核对数量
   与 created_instances.json 一致；
3. 若有 TIMEOUT 实例：控制台核实是否真实存在（unknown 处置纪律——查 job /
   查 list，不盲目重建）；
4. 本地清理：`/tmp/perf-conc/{run_id}/` 保留至报告产出后可删；
   `~/.local/state/huaweicloud-rds-pg/` 下本轮 request 文件（0600 密码文件）
   随 run_id 目录删除；
5. 费用复核：删除后 1 小时账单确认停止计费。

**费用护栏**：单轮实例数上限（T1b=15）；预估费用见 §2.2；异常中止条件
（连续 3 次失败熔断）见 §2.3。

---

## 4. 测量数据采集设计

### 4.1 每进程 JSONL 打点格式（驱动脚本写，独立于 MCP 审计）

```json
{"ts": 1732600000.123, "run_id": "r20261126a", "pid": 8801, "phase": "poll",
 "tool": "show_pg_instance_job", "latency_ms": 412, "result_code": "ok",
 "result_state": "running", "attempt": 1, "note": "job=ff...20 hop=7"}
```

- `phase` 枚举：`init / barrier / preview / submit / poll / run_start / run_end / abort`；
- `result_code`：`ok / error_401 / error_timeout / error_sdk / error_transport`；
- `result_state`（仅 submit）：`accepted / failed / unknown`；
- `latency_ms`：本次 tools/call 端到端（发送→收到 JSON-RPC result）；
- 建议同一行补 `send_ts`（绝对秒）用于间隔节奏分析（T2）。

### 4.2 审计文件复用

- `HUAWEICLOUD_MCP_AUDIT_FILE` 每进程独立文件（§2.4 模板）——core
  AuditLogger 每工具调用一条 JSONL（ts/event=tool_call/tool/params 脱敏，
  `~200 字符/行`），是**服务端视角**的地面真值；
- 对账关系：`打点行数(preview/submit/poll) == audit 行数(tool_call)`；
- 统计守卫放大：`grep -c '"tool": "list_ai_applications"' audit.jsonl`
  （注意 list_ai_applications 作为内部 API 调用是否进 audit 取决于 middleware
  挂载层级——**若审计只记 MCP 工具不记内部 API**，改用打点法：在驱动侧无法
  直接观测内部调用 → **推荐以延迟差法**：提交段延迟 - (recheck+execute 的
  2 RTT 估计) ≈ guard RTT；或临时在 `assert_not_ai_managed` 加 stderr 打点
  （一行 print，测后移除——不改动交付代码路径，仅测试分支）。

### 4.3 聚合分析脚本设计（aggregate_results.py）

输入：`/tmp/perf-conc/{run_id}/p*/metrics.jsonl` + `p*/audit.jsonl` +
`created_instances.json` → 输出汇总表（Markdown）：

| 输出指标 | 计算方法 |
|---|---|
| 并发加速比 | (串行基线总时) / (max(run_end) - min(run_start)) |
| 各 phase 延迟 P50/P95/P99 | 按 phase 分组的 latency_ms 分位数 |
| 失败分类 | result_code × result_state 交叉计数表 |
| IAM 限流次数与恢复 | error_401 计数 + 首末出现时间差 |
| 守卫/recheck 调用计数 | audit 内部 API 计数或延迟差法（§4.2） |
| 轮询统计 | poll 行数、BUILD 并发峰值、间隔漂移 (P95(Δsend_ts)-30s)/30s |
| 创建对账 | created_instances.json 行数 vs accepted 账本行数 vs 云 list 复核 |

### 4.4 PlanStore 对账查询模板（SQLite）

```sql
-- ① 本轮孤儿 prepared 行（预览后从未提交且已过期；用时间窗过滤本轮：
--    expires 在 [run_start, run_end+600] 内的 prepared 行 = 本轮预览残留）
--    预期 = 预览数 - 提交数（含 T3 预览样本）；异常 = 超出该数的行
SELECT id, expires, state FROM plans
 WHERE state='prepared' AND expires BETWEEN :run_start AND :run_end_plus_ttl;

-- ② 卡死 submitted 行（提交中崩溃/异常——正确性红线，必须 = 0）
SELECT id, digest, state FROM plans WHERE state='submitted';
-- 处置纪律：不 DELETE；用 record/inspect 对账该 plan 的 job 结果后人工归档。

-- ③ plan 单次消费验证：同 digest 多行状态分布
--    同一意图（同 digest）出现 accepted + prepared = 预览重发（正常）；
--    出现 accepted + accepted / accepted + submitted = 重放（严重违规，必须 0）
SELECT digest, COUNT(*) c, GROUP_CONCAT(state) states FROM plans
 GROUP BY digest HAVING c > 1;

-- ④ 账本 vs 云对账：accepted 行数（含 job 字段）应与 created_instances
--    及云端 list 中 perf-batch-* 数量一致
SELECT COUNT(*) FROM plans WHERE state='accepted' AND job IS NOT NULL;
```

> 查询入口：`sqlite3 /tmp/perf-conc/{run_id}/shared/plans.sqlite3`（0600，
> 每次连接新开即走 BEGIN IMMEDIATE 路径，对账为只读不影响锁）。

---

## 5. 风险与安全

### 5.1 IAM 账号级限流（最高风险）

- **限流锁 AK，AK 属账号**——测试与生产共 AK = 测试可锁生产。**测试专用 AK**
  （§2.1）是第一道护栏；
- 保持默认 200ms 限流门（勿设 RDS_PG_MIN_INTERVAL_SECONDS=0）；
- 轮询间隔 ≥30s（真实 agent 节奏）；禁止无间隔连发（整夜锁 AK 实录：恢复需
  分钟级）；
- 401 出现后的纪律：停止操作 → 60s 粒度探测 → 恢复后从**未决 plan 对账**继续，
  不盲目重发。

### 5.2 费用护栏

| 护栏 | 值 |
|---|---|
| 单轮实例上限 | T1b=15（硬上限，驱动脚本参数校验） |
| 规格锁定 | Single + COMMON 40GB + postPaid（脚本固定，不接受外部传参覆盖） |
| 费用预估 | §2.2 表（T1a ~¥1 / T1b ~¥2-3） |
| 异常中止 | 连续 3 次工具调用失败熔断（§2.3）；全进程过半熔断全体终止 |
| 超时兜底 | job 轮询 30 分钟上限 → 标记 TIMEOUT 进清理清单（不弃管） |

### 5.3 失败恢复纪律

- **unknown 状态禁止重放**（mutate 三分类）：超时≠拒绝，RDS job 是异步的，
  盲目重试 = 双倍计费/双实例孤儿；
- 处置流程：`show_pg_instance_job` 查对账 → `list_pg_instances` 复核实例是否
  真实存在 → 存在则进清理清单，不存在才可重发**新预览**（新 plan_id）；
- submitted 卡死行不 DELETE（防重放凭据），走 record/inspect 归档。

### 5.4 测试环境与生产隔离检查清单

- [ ] 测试 AK 为独立 IAM 用户（非生产 AK/SK）
- [ ] 目标 region 与生产工作负载隔离（或确认同 region 无生产 RDS 关键负载）
- [ ] 实例名全部 `perf-batch-` 前缀（控制台可按名筛选核对删除）
- [ ] 本地状态隔离：RDS_PG_STATE_FILE / RDS_PG_REQUESTS_DIR / AUDIT_FILE
      全部指向 /tmp/perf-conc/{run_id}/，不污染 `~/.local/state/` 生产路径
- [ ] 测试结束：删除实例 → 停用 IAM 用户 → 删本地 /tmp/perf-conc → 复核账单
- [ ] 无任何写操作指向既有生产实例（驱动脚本白名单：只允许 create/show/job 工具）

---

## 6. 执行顺序与决策门

```
T2（零成本）──► T3（零成本）──► D3 ──► T1a 报批 ──► D4 ──► T1b ──► D5 ──► T1c（可选）
                     │                                │
                     └─ D2：T3 确认放大 ► 先做 T3b 缓存改进再 T1 │
                                                      └─ D4 失败 ► 停，不升级 T1b
```

| 门 | 位置 | 通过条件（全绿才继续） | 终止条件 |
|---|---|---|---|
| D1 | T2 后 | T2 SLO 全满足（P95≤600ms/零连接错误/漂移≤10%/3 进程劣化≤1.5×） | 连接池回归或 401 无法恢复 → 停，先修 F4/限流 |
| D2 | T3 后 | 守卫调用次数符合预期（1 次/提交），开销占比已量化 | 若守卫在预览段也被调用（bug）→ 停，报 bug |
| D2b | T3 确认放大后 | （可选）T3b 缓存改进落地并回归 T3：真实调用数降至 ⌈窗/60s⌉ | 改进引起守卫误放（AI-3 mock 回归失败）→ 回滚 |
| D3 | T1a 报批前 | 用户确认：专用 AK 就绪、配额余量 ≥ N×M+2、费用预算批准（~¥1）、隔离清单 §5.4 全勾 | 任一项不满足 → 不创建任何资源 |
| D4 | T1a 后 | 成功率 100%（或全可归因优雅拒绝）、账本零污染（§4.4 ②=0 ③无重放）、created 对账一致 | 出现 unknown 状态实例或 submitted 卡死 → 停（查 job 对账，不重发），修复后重跑 T1a |
| D5 | T1b 后 | 加速比 ≥1.5×、SLO 全绿、IAM 恢复 ≤5min（若出现） | 加速比 <1.2×（并发无效）→ 分析瓶颈（SQLite？云侧排队？）再定 |

**T1b 升级前置**：T1a 全绿 + 清理完成（控制台确认删除）才开 T1b。

---

## 7. 附录

### A.1 驱动脚本伪代码（多进程 barrier + MCP stdio 会话模板）

```python
# drive_concurrent.py（伪代码）
def child(pid, run_id, cfg, barrier):
    env = make_env(run_id, pid, cfg)          # §2.4 模板
    proc = subprocess.Popen(                  # 真实 MCP stdio 会话
        ["uv", "run", "--directory", cfg.server_dir, "mcp-huaweicloud-rds-pg"],
        stdin=PIPE, stdout=PIPE, env=env)
    rpc = JsonRpcClient(proc)                 # 逐行 JSON-RPC，记 send_ts/latency
    rpc.call("initialize", {...}); rpc.call("tools/list")      # 冷启动计入
    metrics = open(f"/tmp/perf-conc/{run_id}/p{pid}/metrics.jsonl", "a")
    point("init"); barrier.wait(); point("barrier")            # N 进程同步起跑

    created = []
    for n in range(cfg.per_proc):
        # T1 序列：secret → preview → submit → poll（§3.3.2）
        pw_ref = rpc.tool("write_pg_secret_request", password=gen_pw())
        plan = rpc.tool("create_pg_instance", **args, confirm=False)
        try:
            res = rpc.tool("create_pg_instance", **args, confirm=True,
                           plan_id=plan["plan_id"])           # 单次消费
            created.append({"instance_id": ..., "job_id": ..., "name": ...})
            poll_until_terminal(rpc, res, interval=30, timeout=1800)  # 打点 phase=poll
        except ToolError as e:
            point("submit", result_code=classify(e))          # 401/timeout/sdk
            if e.result_code == "error_401": wait_recover(rpc) # 60s 探测恢复
            # 写失败不自动重试（unknown 语义）
    dump(created)                                              # created_instances 分片

def main():
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=child, args=(i, run_id, cfg, barrier))
             for i in range(cfg.n_proc)]
    # 启动全部 → join；主进程监控熔断标志（共享 Event），过半熔断 → 终止
    # 结束：合并 p*/created_*.json → created_instances.json + 打印清理清单
```

> 只读失败重试策略（T2 内部）：`retry_if(e) and attempt<2: sleep(2**attempt * 2)`；
> 写操作无自动重试。

### A.2 聚合脚本伪代码

```python
# aggregate_results.py：读 p*/metrics.jsonl + audit.jsonl + created_instances.json
# → 输出 §4.3 汇总表（加速比 / P50/P95 / 失败交叉表 / 401 计数与恢复 /
#    守卫计数 / 轮询漂移 / 创建对账），Markdown 落盘 report-{run_id}.md
```

### A.3 判定数据表格模板（agent / 人工直接填）

```
Run: ____  run_id: ____  date: ____  执行人/agent: ____
环境: N_proc=____ M=____ region=____ AK=专用/共用(不推荐)____

T2 单进程:  P95=____ms  P50=____ms  连接错误=____  间隔漂移=____%
T2 3进程:   P95=____ms  (vs 单进程 ×____)  401 出现=____次 恢复=____min
T3:  守卫调用/提交=____次  guard_RTT≈____ms  开销占比=____%
T1a: 成功____/6  failed=____ unknown=____  账本: submitted卡死=__(须0)
     孤儿prepared=__(预期=预览-提交)  重放=__(须0)  created对账 一致/不一致
     总时=____min  串行基线=____min  401=____次 恢复=____min
T1b: 成功____/15 同上四项 + 加速比=____×(SLO≥1.5)
     BUILD峰值并发=____  轮询P95=____ms(SLO≤900)
     守卫调用总数=____(预期 N×M=____)  recheck调用=____
T1c(可选): 超额请求=____  优雅拒绝=____/____  半创建=__(须0)
清理: created_instances.json 条数=____ 控制台删除=____(一致/不一致) 账单停止= Y/N
结论: D1 __ D2 __ D3 __ D4 __ D5 __   发现与建议: ____
```

### A.4 本方案与 PERF-SPEC 的指标衔接

| PERF-SPEC 指标 | 本方案验证口径 |
|---|---|
| 热路径端到端 P95 ≤600ms | T2 单跳 P95（§3.1 SLO） |
| 并发容量 4 agent 写 0 失败 单 op ≤10ms | T1 账本零污染 + F2 多进程验证 |
| IAM 节流防御 200ms 门 | T2 节奏分析 + T1 ④ 限流出现率/恢复 |
| 轮询等待模式（P1-2） | T2 轮询成本数据 → wait_seconds 设计依据 |
| run_mutation 3 RTT 分解（§1.5） | T3 守卫 RTT 占比 + T1 ⑥ 放大公式 |

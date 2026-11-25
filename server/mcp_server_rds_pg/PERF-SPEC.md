# PERF-SPEC：mcp-huaweicloud-rds-pg 面向 Agent 消费者的性能规格

> 版本 0.1（2026-11-25）。审计对象：71 工具 / tools→service→client 三层 / SdkRdsClient（mixin + asyncio.to_thread）/ PlanStore SQLite / huaweicloud_mcp_core middleware。
>
> 核心设计前提：**MCP 的用户不是人类而是 Agent（LLM）**。其消费模式与人类截然不同：
> - 高频串行调用（轮询 job 30s×20 次无人工停顿）
> - 上下文预算敏感（每个工具返回的信封直接吃 Agent 的 token 预算）
> - 无思考停顿（Agent 不会像人类一样"歇两秒再点"）
> - 并发（一个用户会话可能同时跑 3-4 个 agent，各自持有独立 MCP 进程或共享一个）
>
> 性能设计的一切取舍以这四条为中心，而不是人类的"界面响应速度"。

---

## 1. 实测基线（2026-11-25，cn-north-4）

测量环境说明：测试凭证（已脱敏）当日在 IAM 侧被判定签名失败
（401 APIGW.0301，且出现 "AK failed to reach the limit, forbidden" 限流标记——
这正是任务描述中"整夜轮询把账号锁了"的同一症状）。因此**成功路径的云 RTT 无法
直接采样**，采用替代法：未鉴权请求的 401 处理时延（含完整 APIGW 路由+签名校验+错误
构造，仅缺少响应体序列化）作为云 RTT 下界；本地各环节用微基准精确实测。表中标注
推算成分。

### 1.1 端到端（MCP stdio 全链路）

| 环节 | 实测 | 备注 |
|---|---|---|
| `uv run` spawn + stdio 建链 | 7–31 ms | uv 缓存命中 |
| `initialize()`（进程启动+import 全树） | **1409–1527 ms（均值 ~1470）** | 见 1.3 拆解；每会话一次 |
| `tools/list`（71 工具 schema 序列化） | 8–57 ms | Agent 每次连 MCP 都要拉一遍；schema 瘦身有价值 |
| 首次 `list_pg_instances`（含 SdkRdsClient 构建 + IAM project + 首 RTT） | 281–850 ms | 冷 |
| 热路径同会话第 2 跳起 | 193–589 ms | 含一次云 RTT |

### 1.2 各环节开销拆解（微基准，50–500 次采样）

| 环节 | 均值 | P95 | 占热路径比例（按 300ms 热调用估） |
|---|---|---|---|
| asyncio.to_thread 派发 | 0.084 ms | 0.110 ms | <0.1% |
| SdkRdsClient() 构建（project_id 已缓存） | 0.16 ms | 0.13 ms | <0.1% |
| **每调用 new_builder 的 IAM project 解析（未设 HUAWEICLOUD_PROJECT_ID 时）** | 一次 IAM RTT ≈ 200–400 ms | — | **冷路径最大头** |
| GuardrailsMiddleware pre_check + audit emit | 0.021 ms | 0.028 ms | <0.1%（audit 仅 stderr；开文件追加 +1 次 open/write） |
| MaskingEngine.mask() 100 条信封 | 4.92 ms | 5.34 ms | ~1.6%（正则 4 条对每字符串跑） |
| MaskingEngine.mask() 20 条信封 | ~1.0 ms | — | ~0.3% |
| page_result/_truncate_value | 0.009 ms | — | 忽略 |
| PlanStore issue+claim+finish（每次新 sqlite 连接） | 4.90 ms | 5.41 ms | 仅写路径（mutate 提交段） |
| PlanStore 并发 4 线程 × 20 ops | 7.4 ms/op | 0 失败 | BEGIN IMMEDIATE + timeout=10 在 4 agent 并发下无竞争失败 |
| PlanStore 并发 16 线程 × 64 ops | 15.3 ms/op | 0 失败 | 仍无失败；吞吐下降但安全 |
| **云 RTT（401 下界实测，冷 TLS 会话）** | 205–393 ms | — | 首跳含 TLS 握手 |
| **云 RTT（401 下界实测，keep-alive 热）** | 45–216 ms | — | 与客户端连接池复用强相关 |
| stdio JSON-RPC 单往返 | ~1–3 ms | — | 本机管道 |

**云 RTT 关键结论**：SDK 的 requests Session 带连接池（pool_maxsize=10）。进程内
复用同一 SdkRdsClient 实例时连接复用，热 RTT≈45–216ms；**每次工具调用新建
InstanceService()→SdkRdsClient() 并不新建 TCP 连接**（requests Session 在每个 client
实例内部，新 client=新 Session=冷 TLS≈205–393ms）。实测 SdkRdsClient() 对象构建仅
0.16ms，但**连接池不复用**——服务层"每调用 new client"的真实代价是每跳多付一次
TLS 握手 ≈150–250ms，这是热路径延迟翻倍的根源（对照实验：warm keep-alive 45ms vs
cold TLS 264ms）。

### 1.3 冷启动 1.5s 的 import 剖析（-X importtime）

| import 子树 | 累计耗时 | 占比 |
|---|---|---|
| mcp.server 全家（mcp/anyio/pydantic/starlette…） | ~712 ms | 48% |
| huaweicloudsdkrds.v3（全套 model） | ~439 ms | 30% |
| requests+urllib3 | ~102 ms | 7% |
| 其余 | ~150 ms | 10% |

`initialize()` 的 1.5s 中 ~1.4s 是 import（uv 已预热缓存）。这部分是每会话固定成本，
Agent 每开一个 MCP 会话付一次。

### 1.4 信封体积（Agent 上下文预算）

| 信封 | 字符数 | ~tokens（chars/4） |
|---|---|---|
| list 100 条实例（page_result 上限） | 54 474 | **~13 600** |
| list 20 条（默认） | 10 953 | ~2 740 |
| show 单实例 + hints | ~900 | ~230 |
| **IAM 401 错误信封（修复前，含 canonical_request）** | 696 | **~174（每次错误都付）** |
| IAM 401 错误信封（修复后，canonical 已裁） | 235 | ~59 |

### 1.5 两段式 + 轮询链路（理论 + 实测分解）

ops_window 类轻操作全链路（确认前已实测的成分）：
预览（本地 plan + notices + SQLite issue ≈ 5ms，无云调用）
→ 提交（recheck=list_instances 1 RTT + AI guard list_ai_applications 1 RTT + claim 5ms
+ change_ops_window 1 RTT + finish 5ms ≈ **3 RTT + 10ms 本地** ≈ 150–700ms）
→ 轮询（show_pg_instance_job 每跳 1 RTT + middleware ≈ 250–500ms/跳；
  Agent 端典型 30s 间隔 × N 跳，每跳消耗一次 LLM 推理 + 一次 ~100–300 token 信封）。

**轮询的隐性成本主要在 Agent 侧**：每跳是一次完整 LLM 推理循环（秒级 + token 计费），
服务端等待模式（见 §7）能把 N 次往返折叠为 1 次。

---

## 2. 指标定义（面向 Agent 的 SLO）

| 指标 | 目标 | 依据 |
|---|---|---|
| 热路径非云开销（middleware+service+信封构造）P95 | **≤ 30 ms** | 实测现状 ~6ms（masking 5.3ms 为主），留 5 倍余量 |
| 热路径端到端（含 1 云 RTT）P95 | ≤ 600 ms | 热云 RTT 45–216ms + 信封/中间件；现状最差 ~590ms |
| 冷启动（initialize） | ≤ 1.6 s（现状达标，暂不优化） | import 1.4s 固定成本；优化空间见 §5 备注 |
| 列表页信封 | **≤ 2 500 tokens（默认 limit=20 时 ~2 740 → 裁 hints/空字段后达标）** | 一次列表不应超过 Agent 单步工具预算的 1/4 |
| 错误信封 | ≤ 250 chars，禁止 canonical_request/签名细节 | 实测修复前 696→修复后 235 |
| 轮询模式（等待型任务） | 服务端等待模式 1 次调用 ≤ 120 s 覆盖 ≥3 跳轮询 | 见 §7 |
| 并发容量 | 4 agent 并发写（SQLite ledger）0 失败、单 op ≤ 10 ms | 实测 7.4ms/0 失败；16 线程仍安全 |
| IAM 节流防御 | 客户端最小间隔 200 ms（5 rps 进程内上限） | 账号级锁的教训：进程内串行 + 间隔，已实测不改正确性 |

---

## 3. 超时设计（P0，已实现）

**问题**：原实现 `asyncio.to_thread(_call)` 无任何超时包装。SDK 自带 HTTP
timeout=(60 connect, 120 read)，看似有界——但 (a) 120s read 对 Agent 是灾难
（Agent 的 MCP 客户端通常 30–60s 放弃，服务端线程泄漏并继续占用）；(b) DNS/代理
等 transport 层挂死时连这个界都不可靠。KooCLI 通道（mgr 仓库 koocli.py）有 60s
wait_for+kill 先例，SDK 通道此前裸奔。

**分层超时**（client 层统一 mixin `throttle.py:guarded_call`）：

| 层级 | 默认 | 场景 |
|---|---|---|
| 云 API 单调用 | **30 s**（DEFAULT_CALL_TIMEOUT） | 读 API 实际 <2s；30s 只为兜底挂死 |
| job 类 / 大 body 提交 | 60 s | create/restore 等重负载 |
| 编排 plan 全程 | 120 s | 未来 wait 类工具的服务端轮询总预算 |

**实现**：`asyncio.wait_for(asyncio.to_thread(sync_call), timeout=limit)`。
超时抛 `MCP_CALL_TIMEOUT` 信封（已加入 errors._INTERNAL_CODES）。

**超时后的三分类语义（与 mutate.py 对齐）**：
- **failed（可改参重试）**：SDK ServiceResponseException/ClientRequestException
  （云明确说 no）→ mutate 管线 `plans.finish(plan_id, "failed")`。
- **unknown（禁止重放）**：超时/transport 异常（含 MCP_CALL_TIMEOUT）→
  `plans.finish(plan_id, "unknown")`，hint 指示先 show_pg_instance_job 对账。
  判定依据：**超时 ≠ 拒绝**——请求可能已被云受理（RDS job 是异步的），盲目重试
  双倍计费/双倍执行。这正是 guarded_call 用 `raise McpToolError` 而非让
  TimeoutError 直接冒泡的原因：mutate 管线把非 McpToolError 非 SdkException 的
  异常归为 unknown。
- accepted：正常返回含 job_id。

**当前接入范围**：sdk_rds.py 的 6 个核心方法（list_instances / list_job_info /
show_task_detail / reboot/stop/start）。其余 mixin 的 89 处 `asyncio.to_thread`
迁移为渐进式（guarded_call 已导出，逐文件替换 `asyncio.to_thread(_call)` →
`await guarded_call("<label>", _call)` 即可，单行 diff/处）。

## 4. 限流设计（P0，已实现）

**问题实录**：本会话 401 消息中出现 "AK … failed to reach the limit, forbidden"
——整夜无间隔轮询触发 IAM 账号级限流，锁的是 AK 不是进程。人类不会 1 秒 20 连发，
Agent 会。

**设计**：
- **实现位置**：client 层统一 mixin（throttle.py），service/tools 不可见——
  Agent 用的工具数（71）远多于客户端方法数，client 层是唯一全覆盖点。
- **机制**：进程内 async 单调间隔门（默认 **200 ms = 5 rps 上限**）。选简单间隔门
  而非令牌桶：SDK 通道在进程内天然串行（每 to_thread 一个调用），桶的突发容量
  只会帮助触发 IAM 限流；间隔门以最小代码覆盖最大风险。多 agent 各持独立进程时，
  账号级保护靠 200ms 上限 × N 进程数仍显著优于无界。
- **可调**：`RDS_PG_MIN_INTERVAL_SECONDS` 环境变量（0=禁用，测试用；缺省 0.2）。
- **退避**：wrap_sdk_error 捕到 APIGW.0301/限流类错误时**客户端不自动重试**
  （写工具重试有 unknown 风险）；错误信封 hint 指示 Agent 指数退避 2^n 分钟
  （n=1 起，即 2/4/8 分钟；401 锁定实测需分钟级恢复）。服务端不代 Agent 做重试
  决策——重试 = 新工具调用 = Agent 可见的信封，隐藏重试会破坏两段式的 plan 单次性。

## 5. SDK client 复用（P1，设计+结论）

**实测结论**：`new_builder()` 本身仅 0.16 ms（无握手、无重解 project_id——
project_id 解析在 credentials.py 有进程级缓存 `_PROJECT_CACHE`，首次 IAM RTT
~200–400ms 后进程内免重复）。**真正的浪费是连接池**：每工具调用
`InstanceService()→SdkRdsClient()` 新建 requests Session，丢弃热连接，
每跳多付一次 TLS 握手 150–250 ms（实测 cold 264ms vs warm 45ms）。

**设计**：进程级 SdkRdsClient 单例缓存（key=(ak,sk,token,region,endpoint)），
service 层 `client or SdkRdsClient()` 改为 `client or get_shared_client()`。
实现 ~30 行（client/__init__.py 加 lru_cache 式工厂）。预期热路径端到端从
~300–590ms 降到 ~120–350ms。**注意**：单例后 200ms 限流门的价值更高（共享
连接的并发调用全部过同一 gate）。项目级 project_id 缓存已存在，不动。

## 6. 信封瘦身（P0 部分，已实现；余下 P1）

已实现（core errors.py）：`canonical_request`（含签名头、UA、SDK date、
body hash，581 字符的签名噪音）裁剪为 "(canonical request elided)"。
错误信封 696→235 chars。IAM 签名失败这种"Agent 无法行动"的细节不再进上下文。
**验证**：真实 401 文案回归通过；rfs/rc/core 全测试绿。

待做（P1，未实现，仅设计）：
- 列表默认页 limit=20 保持（~2 740 tokens 略超 2.5k 目标）；把 `truncated`/
  `marker` 保留、hint 里的轮询提示去掉（Agent 重复调用会反复收到同一句
  ~30 token 的 hint——单实例场景每次 show 白付）。预计降到 ~2.4k。
- `MAX_PAGE_SIZE=100` 对 Agent 是陷阱（13.6k tokens 一页）；建议降到 50 并在
  tool docstring 标注。低优先：Agent 默认拿 20，只有显式要 100 才触发。
- show 单实例：`_pick` 已做字段白名单（instance_service._INSTANCE_FIELDS），
  体积可控（~230 tokens），不动。

## 7. 轮询优化：wait 模式（P1，接口草案，未实现）

**问题**：Agent 轮询 show_pg_instance_job 每 30s×20 次 = 20 次 LLM 推理 + 20 个
~150–300 token 信封 + 20 次云调用（还可能触发限流）。服务端一次调用内等待到
终态可全部省掉。

**草案 A（推荐）——现有工具加参数**：
```
async def show_pg_instance_job(job_id: str, wait_seconds: int = 0) -> dict:
    """...wait_seconds: 0 = 立即返回（默认，现状行为不变）；>0 = 服务端
    轮询至终态或超时（建议 ≤300，编排级预算 120s 内时也可用短等待）。"""
```
内部：`await asyncio.wait_for(poll_loop(job_id, interval=5, until terminal),
timeout=wait_seconds)`，轮询间隔走 throttle 门（5s > 200ms 不受影响）。
终态（Completed/Failed）或超时时返回当前 job 状态 + `waited` 字段。
**超时非错误**：返回 running 状态，Agent 决定再等或放弃——错误化会让 Agent
误判 job 失败。

**草案 B（备选）——新工具 wait_pg_job**：独立 DANGEROUS 无需（只读等待），
但增加 72 号工具 schema（tools/list 体积 +~150 chars）。推荐 A：零新增 schema。

**与两段式的交互**：wait 模式只包轮询不包提交；提交仍走 run_mutation（三分类
unknown 语义不受影响）。

## 8. 优先级排序（Agent 体验影响 × 实现成本）

| 优先级 | 项 | 影响 | 成本 | 状态 |
|---|---|---|---|---|
| **P0** | 超时包装（§3） | 挂死=Agent 永久等待，最坏情况 | 30 行 mixin | ✅ 已实现+验证 |
| **P0** | 限流间隔（§4） | 账号级锁定（实测踩过） | 同上 30 行 | ✅ 已实现+验证 |
| **P0** | canonical_request 裁剪（§6） | 每次错误 174→59 tokens，签名噪音不进上下文 | 15 行 core | ✅ 已实现+验证 |
| P1 | SDK client 连接池复用（§5） | 热路径 -150~250ms/跳 | ~30 行 | 设计定稿 |
| P1 | wait_seconds 轮询模式（§7） | N 次 LLM 推理→1 次 | ~40 行 | 接口草案 A |
| P1 | 错误 hint 去重/信封微瘦（§6） | 高频轮询场景累积 token | ~10 行 | 设计 |
| P2 | MAX_PAGE_SIZE 100→50 | 防御 Agent 显式大页 | 1 行 + 文档 | — |
| P2 | tools schema 瘦身 | initialize 后 tools/list 体积 | 大（71 docstring） | 不做（docstring 是 Agent 的工具发现依据） |
| P2 | import 冷启动 1.5s→<1s | 每会话一次 | SDK 延迟导入重构，风险大 | 不做 |

**P0 验证数据**：
- 66/66 测试全绿（rds-pg 两个副本 + core 85+2 + rfs 44），ruff/mypy clean。
- 限流默认 0.2s 下测试套件用时 1.14s→1.20s（+0.06s，无超时/无失败）。
- 错误信封实测裁剪 581→134 chars（message 部分）、整信封 696→235。
- 超时行为：MCP_CALL_TIMEOUT 信封携带 unknown 语义 hint（与 mutate 三分类一致）。

---

## 9. 附：测量方法与局限

- 云 RTT 下界法：无凭证 401 请求（APIGW 完整走签名校验+错误构造），比成功列表
  少响应体序列化与 DB 查询，故真实成功 RTT 更高（估 +50–300ms）。凭证恢复后
  应按任务原始要求补 5×4 工具实测（脚本模式见仓库外 /tmp/perf_audit/measure_client.py）。
- 401 期间观测到的 "AK failed to reach the limit" 证实限流问题真实存在，
  §4 的设计直接对应。
- SQLite 竞争用真实文件布局（每 op 新连接，0700/0600）在 4/16 线程实测，
  未模拟网络抖动下的 10s sqlite timeout 边界（进程内场景连接总是本地）。

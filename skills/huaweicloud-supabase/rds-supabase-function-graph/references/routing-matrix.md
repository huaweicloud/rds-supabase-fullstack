# 分工判定矩阵与路由

## 判定矩阵

| 逻辑特征 | 去处 | 判定依据 |
|---|---|---|
| 纯数据变换、单事务一致性（计算派生列、跨表校验） | Postgres RPC | 无外部 I/O、毫秒级、需事务原子性 |
| 出站 HTTP / Webhook / 第三方 API 对接 | FunctionGraph（apig 或异步触发） | 不可信外网出口不得进数据库进程 |
| 定时作业（库内数据维护、分区清理） | pg_cron | best-practices 技能 `rds-scheduled-jobs` |
| 定时作业（外部 I/O：对账、补单、汇总推送） | FunctionGraph Timer | 需要出站调用，pg_cron 不适合外呼 |
| 数据库侧单次出站 HTTP（低频、非密钥） | pg_net | usage 技能既有路由；高频/带密钥 → FunctionGraph |
| 高安全处理（密钥不进前端/DB：签名、解密、风控） | FunctionGraph | 密钥只存函数环境变量 |
| 长驻进程 / SSR / WebSocket 服务端 | v1 边界外 | FunctionGraph 事件模型不适配，明确告知用户 |

## 与既有技能的关系

| 任务 | 路由 |
|---|---|
| 全栈从零到上线（函数是其步骤二识别的边界外逻辑） | web-build 编排 → 路由本技能 |
| 前端 fetch 封装、supabase-js SDK 用法 | rds-supabase-usage 技能 |
| 函数内幂等表的 DDL（ grants/RLS） | rds-supabase-postgres-best-practices + 数据面 execute_sql（web-build 步骤五既有通道） |
| FunctionGraph 云侧原子操作 | 本技能（KooCLI 唯一通道） |

## 集成时序（web-build 场景）

1. web-build 步骤二澄清时按本矩阵识别 → 用户确认函数清单
2. web-build 主流程继续（步骤三~八）；函数开发在 `released` 后并行或按需进行
3. 函数幂等表 DDL 经 web-build 步骤五既有通道部署（不重开数据面）
4. web-build 步骤六前端生成时，经 usage 技能引用本技能的 fetch 封装契约
5. 本技能独立触发时自建 `.hwsupabase/functions.json`，不要求 webapp.json 存在（`webapp_ref` 允许 null）

# 分工判定矩阵与路由

## 判定矩阵

| 逻辑特征 | 去处 | 判定依据 |
|---|---|---|
| 纯数据变换、单事务一致性（计算派生列、跨表校验） | Postgres RPC | 无外部 I/O、毫秒级、需事务原子性 |
| 出站 HTTP / Webhook / 第三方 API 对接 | FunctionGraph（apig 或异步触发） | 不可信外网出口不得进数据库进程 |
| 定时作业（库内数据维护、分区清理） | pg_cron | 库内调度即可，无外部 I/O |
| 定时作业（外部 I/O：对账、补单、汇总推送） | FunctionGraph Timer | 需要出站调用，pg_cron 不适合外呼 |
| 数据库侧单次出站 HTTP（低频、非密钥） | pg_net | 高频/带密钥 → FunctionGraph |
| 高安全处理（密钥不进前端/DB：签名、解密、风控） | FunctionGraph | 密钥只存函数环境变量 |
| 长驻进程 / SSR / WebSocket 服务端 | v1 边界外 | FunctionGraph 事件模型不适配，明确告知用户 |

## 任务边界（本技能与其他通道的关系）

| 任务 | 路由 |
|---|---|
| Postgres RPC 可承载的纯库内逻辑 | 数据库 SQL/RPC 实现（已接入数据面 MCP 的经其 execute_sql；未接入的用 SQL 直接实现），本技能不重复实现 |
| 函数内幂等表的 DDL（grants/RLS） | 数据库 SQL 实现；已接入数据面 MCP 的经其 execute_sql 部署 |
| FunctionGraph 云侧原子操作 | 本技能（KooCLI 唯一通道） |
| 前端 fetch 封装 | 本技能 SKILL.md"fetch 封装契约"（自包含） |

## 使用模式

1. 独立使用：用户直接提出云函数需求（"加一个交易通知云函数"），本技能从步骤一环境检查走完整六步
2. 函数幂等表 DDL 属数据库变更，经用户既有的数据库通道部署（psql / 数据面 MCP / 控制台均可）；本技能只负责 FunctionGraph 侧
3. 本技能独立触发时自建 `.hwsupabase/functions.json`，不要求 webapp.json 存在（`webapp_ref` 允许 null）

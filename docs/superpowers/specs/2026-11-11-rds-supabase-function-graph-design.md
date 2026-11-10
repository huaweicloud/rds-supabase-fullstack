# rds-supabase-function-graph 技能设计（v1 · 方案 A 起步）

日期：2026-11-11 · 状态：已获用户口头批准（方案 A 起步；Node.js 优先；六步状态机；env 密钥 + cli-json-file 隔离）

## 1. 定位与边界

- web-build 的姊妹专项技能（与 frontend/usage/best-practices 同级），承载"Postgres RPC 装不下的服务端逻辑"：交易通知、对接外部系统、复杂领域逻辑、高安全隐私处理。
- 触发面：web-build 步骤二识别边界外逻辑时路由至此；也支持独立触发（给已上线 RDS Supabase 应用追加函数、更新/回滚/下线）。
- 分工判定矩阵：纯数据变换/事务一致性 → Postgres RPC；出站 HTTP/Webhook/外部对接 → FunctionGraph；库内定时 → pg_cron；外部 I/O 定时（对账/补单/汇总推送）→ FunctionGraph Timer；密钥不进前端/DB → FunctionGraph；SSR/长驻进程 → v1 边界外。
- v1 不做（负向路由物化）：专享版 APIG 路线（升级路径文档化）、DEW CSMS、Python 模板、告警规则、预留实例、VPC 内网直连 Postgres（v1 经 Kong 网关 REST 公网 HTTPS 访问数据面，零依赖、免 ENI）。

## 2. 六步状态机 + 横向生命周期

```
fgs_env_ready → functions_confirmed → code_built → deployed → released → integrated
（横向：更新=新版本重走 code_built~released；回滚=别名切换+重验收；下线=decommissioned）
```

1. 环境检查与配置：KooCLI 安装/认证（`hcloud configure test`）、region、project_id（复用 devkit AK/SK，与 web-build 步骤一同源）；**首步 `hcloud FGS CreateFunction --help` 自校准命令面**（API 名全部为知识推断，实测前不猜 schema——frontend 纪律平移）。
2. 需求澄清与逻辑分解：判定矩阵逐项分类 → 函数清单（名称/运行时/触发类型/密钥需求/幂等需求）→ `functions.json` 初稿 + 用户确认。
3. 代码生成：零依赖 Node.js 18 样板（验签/CORS/幂等/日志/错误契约）+ 业务代码 + 本地 test-event 自测。
4. 部署：zip → OBS 私有 artifacts → CreateFunction → env/VPC 配置 → APIG 触发器 → 冒烟 InvokeFunction。**部署≠发布**。
5. 安全验证与发布：`fgs-gate --verify` 负向硬门 → CreateFunctionVersion → CreateFunctionAlias。
6. 前端联调：fetch 封装（usage 技能联动）→ 真实 JWT E2E → 幂等重放验证。

## 3. functions.json 契约（独立制品记录）

位置 `<project>/.hwsupabase/functions.json`，webapp.json 经 record_ref 引用（frontend environment.json 同款）。字段：schema_version=1、webapp_ref、functions[]（name/runtime/handler/code_sha256/obs_key/env_names[]/vpc|null/db_role|null/triggers[]（type apig、auth none、url、path）/idempotency{enabled,key_field}/versions[]{version,sha256,alias}）、stages{history 追加,last_completed_stage}。密钥永不入记录（只存 env 名）、RFC3339 UTC、sha256 小写 64 hex、历史只追加。

## 4. 密钥纪律（v1）

- 高敏三类：`FGS_JWT_SECRET`（GoTrue HS256 验签）、`SUPABASE_SERVICE_ROLE_KEY`、外部签名密钥。合法位置 = 函数环境变量（usage SKILL.md 先例：service_role 只允许存在于 MCP 服务器环境、FunctionGraph 函数环境变量）。
- **明文隔离**：env 配置经 KooCLI `--cli-json-file`——body 文件由用户/受保护文件组装，agent 只传路径；值不进 agent 上下文、trace、functions.json。
- 对外 APIG 触发函数必须验签（红线）；仅 Timer/内部触发的函数可豁免。
- JWT Secret 获取：用户从控制台取值放受保护文件（devkit 凭据同模式）。
- CSMS+委托+轮换 = v2 升级路径（references 文档化）。

## 5. fgs-gate.py（独立验证者）

| 模式 | 检查 |
|---|---|
| check-contract | functions.json 结构/sha256/apig 函数必含 FGS_JWT_SECRET env 名/密钥泄漏正则 |
| check-stage --stage X [--verify] | 阶段顺序 + trace 强制（deployed 起）+ REST 核验：无 Authorization 必须 401、坏 JWT 必须 401、真 JWT 200、CORS 精确 origin + OPTIONS 预检 |
| check-trace / check-whitelist | trace 行格式 + 每步 KooCLI 命令 fnmatch 白名单 |
| check-version | 别名指向版本的 sha256 与函数 code_sha256 一致 |

凭据从进程 env 注入、不落日志、HTTPS 强制（loopback 豁免测试）。负向 401 硬门对标 web-build exposed anon 200 硬校验。

## 6. 函数样板（零依赖 Node.js 18）

```
template/ handler.js · lib/{jwt,cors,response,supabase,idempotency}.js · config.json · test-events/apig.json
```

- jwt.js：node:crypto HS256 验签（timingSafeEqual、exp/nbf）——零依赖即免依赖包机制。
- cors.js：FGS_ALLOWED_ORIGINS 精确 origin 白名单，禁 *。
- response.js：统一 {statusCode,headers,body} + catch-all（500 只带 request_id，堆栈只进日志）。
- supabase.js：原生 fetch 经 Kong 网关 REST（service key 来自 env）——v1 免 VPC 免 ENI。
- idempotency.js：幂等键 unique 约束落库（on conflict do nothing）。
- 四场景示例文档化于 workflow-stages。

## 7. KooCLI 命令链（幂等可重入）

ListFunctions → CreateFunction → UpdateFunctionCode(obs) → UpdateFunctionConfig(env) → CreateTrigger(apig) → InvokeFunction(冒烟) → CreateFunctionVersion → CreateFunctionAlias。更新走"新版本→切别名"；回滚走"别名切回+重验收"（rollback_switched/rollback_verified 两态，frontend v3 契约平移）。命令名全部标注待实测，`--help` 自校准先行。

## 8. 生态收口

EXPECTED_SKILLS（5→6）、根 README 技能列表（顺修 web-build 条目"⓪–⑥ 七阶段"陈旧文案）、web-build routing-table/SKILL 边界/workflow-stages 步骤二三处 v2 占位改正式路由、usage SKILL.md 路由表与服务端计算节、web-build INSTALL.md 校验期望数、CHANGELOG。

## 9. 测试

tests/fake_fgs.py（本地假 APIG：200/401/预检/坏 CORS 模式）+ test_fgs_gate.py（pytest 全分支）。真实 E2E 与既有技能同因网络阻断暂缓，先 pytest 化。

## 版本与发布

新技能 v0.1.0；联动版本：web-build v0.6.5（路由收口）、usage v0.2.3（路由表更新）。全部入根 CHANGELOG（A6）。

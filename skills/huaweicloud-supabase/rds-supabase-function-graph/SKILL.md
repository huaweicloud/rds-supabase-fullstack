---
name: rds-supabase-function-graph
description: 'RDS Supabase FunctionGraph 云函数技能：为 Web 应用生成、部署、安全验证并运维承载于华为云 FunctionGraph 的自定义服务端业务代码（交易通知、对接外部系统、复杂领域逻辑、高安全隐私处理）。前端经共享版 APIG 触发器以 Supabase GoTrue JWT 调用函数，函数内完成验签、CORS、幂等与错误契约；全流程经 KooCLI 原子命令编排并受 fgs-gate 机械核验。Use when：需要 Postgres RPC 之外的出站 HTTP/Webhook、密钥不进前端的服务端处理、外部 I/O 定时作业（对账/补单/汇总推送），或为已上线的 RDS Supabase 应用追加、更新、回滚、下线云函数。'
license: Proprietary
metadata:
  version: "0.1.1"
---

# RDS Supabase FunctionGraph 云函数技能

## 概述

当 Web 应用出现 Postgres RPC 装不下的服务端逻辑（出站调用外部系统、密钥必须离开前端、复杂领域计算、交易通知可靠投递）时，本技能以华为云 FunctionGraph 承载该逻辑：生成零依赖 Node.js 函数、经 KooCLI 部署、共享版 APIG 触发器暴露为 HTTPS 端点、函数内验签 Supabase GoTrue JWT，并用 `fgs-gate.py` 机械核验"无认证请求必须被拒绝"等安全事实。

```
前端（OBS+CDN 静态站，持 GoTrue JWT）
    │ fetch + Authorization: Bearer <access_token>
    ↘ 共享版 APIG 触发器（auth=none，v1 入口）
        ↘ FunctionGraph 函数（Node.js18，零依赖样板）
            ├─ lib/jwt.js   验签（FGS_JWT_SECRET，exp/nbf）
            ├─ lib/cors.js  精确 origin 白名单
            ├─ lib/response.js 统一错误契约 + catch-all
            ├─ lib/supabase.js Kong 网关 REST（service key，幂等落库）
            └─ 业务 handler（交易通知/外部对接/领域逻辑/隐私处理）
编排工具：KooCLI（hcloud FGS / obs）——v1 唯一云操作通道，无新增 MCP
```

## 适用范围与边界

| 逻辑特征 | 去处 |
|---|---|
| 纯数据变换、事务内一致性 | Postgres RPC（本技能不介入） |
| 出站 HTTP、Webhook、对接外部系统 | 本技能（APIG 触发函数） |
| 定时作业（库内数据维护） | pg_cron（best-practices 技能） |
| 定时作业（外部 I/O：对账/补单/推送） | 本技能（Timer 触发函数） |
| 高安全处理（密钥永不进前端/DB） | 本技能（密钥存函数环境变量） |
| SSR / 长驻进程 / WebSocket 服务端 | v1 边界外：明确告知用户并停止 |

v1 负向边界（不得擅自引入）：专享版 APIG（升级路径见 references/secret-management.md 附录）、DEW CSMS、Python 模板、VPC 内网直连 Postgres（v1 数据访问一律经 Kong 网关 REST 公网 HTTPS）、告警规则、预留实例。

## 前置条件

1. 本技能包已按 [README](README.md) 独立安装；KooCLI（hcloud）已安装——步骤一核对，缺失则提醒安装并停止
2. 已有可用的 RDS Supabase 应用（用户提供接入地址，或项目内已有记录）；`.hwsupabase/webapp.json` 存在时经 `webapp_ref` 关联，不存在则独立使用（允许 null，自建 `.hwsupabase/functions.json` 即可）
3. 凭据：KooCLI 认证（`hcloud configure test` 连通性确认）+ **项目内**受保护文件 `.hwsupabase/secrets/` 中的 `FGS_JWT_SECRET`（用户从控制台获取 GoTrue JWT Secret 后放入，agent 不读内容）——**项目级隔离**：不入全局/系统变量与个人级配置，不污染其他项目（红线见 references/secret-management.md）
4. OBS：已有桶可用（artifacts 前缀私有路径，不设公开读）

## 工作流

```
fgs_env_ready → functions_confirmed → code_built → deployed → released → integrated
（横向：更新=新版本重走 code_built~released；回滚=别名切换+重验收；下线=decommissioned）
```

### 步骤一 · 环境检查与配置 → 断点 `fgs_env_ready`

1. 声明步骤一（格式见执行纪律）
2. 核对：`hcloud --version` / `hcloud configure test`（不通 → 对接卡片给出 AK/SK 配置方式：devkit 或项目内受保护文件）、region、`HUAWEICLOUD_PROJECT_ID`
3. **命令面自校准**：执行 `hcloud FGS CreateFunction --help`、`hcloud FGS CreateTrigger --help` 记录实际参数名——本技能文档中的命令均为"知识推断"，**实测前不得假设 schema，一切以 --help 输出为准**
4. 写 `.hwsupabase/functions.json` 初稿（schema_version、webapp_ref、空 functions）→ history 追加 passed

### 步骤二 · 需求澄清与逻辑分解 → 断点 `functions_confirmed`

1. 声明步骤二
2. 判定矩阵逐项分类（适用范围表）：凡"Postgres RPC 可承载"项（纯数据变换、单事务一致性）明确回退——已接入数据面 MCP 的经其 `execute_sql` 以 RPC 实现，未接入的告知用户用 SQL 实现，本技能不重复实现
3. 函数清单表格（对接卡片）：函数名 | 运行时 | 触发类型（apig/timer）| 密钥需求（env 名单）| 幂等需求 | 用户逐项确认
4. 对外（apig 触发）函数**必须**含 `FGS_JWT_SECRET` 与 `FGS_ALLOWED_ORIGINS` 两个 env 名——红线，缺失即校验失败
5. 更新 functions.json（functions[].env_names/triggers/idempotency）→ history 追加 passed

### 步骤三 · 代码生成 → 断点 `code_built`

1. 声明步骤三
2. 从 `template/` 复制样板到项目 `<project>/functions/<fn>/`，按函数清单改写 handler 业务段与 config
3. 样板内置（不得删改）：验签、精确 CORS、request_id 透传、结构化日志、catch-all 错误契约、幂等键（交易类启用）
4. 本地自测：`node functions/<fn>/handler.js < test-events/apig.json`（样板支持本地事件回放）→ 全部通过
5. code_sha256 记录（zip 前）→ history 追加 passed

### 步骤四 · 部署 → 断点 `deployed`

1. 声明步骤四
2. 打包：`zip -r pkg.zip .`（functions/<fn>/ 产物；路径含 node_modules 时停止——样板零依赖，出现依赖即设计违规）
3. 上传 OBS 私有路径：`hcloud obs cp pkg.zip obs://<bucket>/artifacts/functions/<fn>/<sha8>/pkg.zip`
4. 命令链（**逐条按步骤一自校准结果执行，幂等重入**）：CreateFunction → UpdateFunctionCode(obs) → UpdateFunctionConfig(env，见密钥纪律) → CreateTrigger(apig, auth=none) → InvokeFunction 冒烟
5. 触发器 URL 回写 functions.json（triggers[].url）→ history 追加 passed

### 步骤五 · 安全验证与发布 → 断点 `released`

1. 声明步骤五
2. `python3 <skill>/scripts/fgs-gate.py check-contract` → PASS 后 `check-stage --stage deployed --verify`（**负向硬门**：无 Authorization 必须 401、坏 JWT 必须 401、真 JWT 200、CORS 精确 origin、OPTIONS 预检）
3. `hcloud FGS CreateFunctionVersion` → `CreateFunctionAlias`（prod 指向新版本）→ functions.json.versions[] 追加
4. `fgs-gate.py check-version` → PASS
5. history 追加 passed。**部署≠发布**：仅步骤五全部通过才算 released

### 步骤六 · 前端联调 → 断点 `integrated`

1. 声明步骤六
2. 前端 fetch 封装（要点见下方"fetch 封装契约"）：Authorization 头、request_id 生成、错误码映射
3. E2E：真实 GoTrue JWT 调用 → 200；重复提交同一幂等键 → 单次生效
4. `fgs-gate.py check-stage --stage integrated --verify` → history 追加 passed → 步骤总览表全绿收尾

### fetch 封装契约（自包含）

```js
// supabaseFgs.js —— 调用 APIG 触发函数的唯一封装，业务代码只 import 这个
export async function callFgs(path, { method = 'POST', body, idempotencyKey }) {
  const { data: { session } } = await window.supabase.auth.getSession();
  const requestId = crypto.randomUUID();
  const res = await fetch(`${FGS_BASE_URL}${path}`, {
    method,
    headers: {
      'Authorization': `Bearer ${session.access_token}`,   // GoTrue JWT，必带
      'Content-Type': 'application/json',
      'X-Request-Id': requestId,                            // 每次调用新生成，用于追踪
      ...(idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : {}), // 重试复用同值，服务端去重
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) throw new Error('登录已过期，请重新登录');      // 验签失败
  if (res.status === 409) throw new Error('重复提交，已忽略');           // 幂等命中
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).message || `请求失败 ${res.status}`);
  return res.json();
}
```

要点：Authorization 携带 GoTrue JWT（函数侧验签）；X-Request-Id 每次新生成；幂等键在**业务重试时复用同一值**；错误码映射只认函数的统一错误契约（401 过期 / 409 重复 / 其余按 message 展示）。

## 执行纪律

1. **步骤声明**（每步骤第一条输出）：`┌─ 步骤N · 名称（前一态 X）` 框含允许/禁止动作与完成断言
2. 单次回复推进单一步骤
3. 等待协议：>30s 操作每 30 秒轮询、上限 20 次，等待期间禁止无关操作
4. 连续失败中止：同一动作连续失败 2 次 → 中止报告，禁止第三次盲目重试
5. 工具白名单：每步骤允许/禁止见 references/workflow-stages.md；越界须用户同意并记 trace
6. gate 机械核验：步骤四、五、六完成前运行 fgs-gate.py 对应模式，**PASS 才能输出步骤报告与推进**；步骤五、六的 check-stage 必须带 `--verify`——安全事实（401/200/CORS）由 gate 直连机器核验，不采信 agent 自报
7. trace：每个 KooCLI/CLI 调用后追加 `.hwsupabase/trace.jsonl` 一行（格式见 references/project-state.md）
8. 进度看板：触发后第一动作——创建六项待办（宿主待办联动）并在聊天输出完整步骤总览表；每步骤报告头部完整重发（状态标记 ⏳/🔄/✅/⛔）；重入会话依据 functions.json 重建

## 可用工具

| 平面 | 工具 | 关键能力 |
|---|---|---|
| 云操作 | KooCLI（hcloud FGS / obs） | 函数 CRUD、代码更新（OBS zip）、env/VPC 配置、触发器（APIG/Timer）、版本/别名、同步与测试调用 |
| 数据面 | Kong 网关 REST（函数内 fetch） | service key 幂等落库、RPC 调用（v1 唯一数据访问通道，免 VPC） |

命令名全部为知识推断——**步骤一 `--help` 自校准是硬前提**；JSON 输出配合 `--cli-query`（JMESPath）解析。禁止新建 MCP 服务器承载本技能操作（v1 决策：KooCLI 原子命令 + fgs-gate 验证足矣）。

## 参数确认

| 项 | 确认规则 |
|---|---|
| 函数清单（步骤二） | 用户逐项确认后才进入步骤三；模糊表述不放大授权 |
| 付费资源 | FunctionGraph 免费额度外按量计费 + OBS 存储——费用预估展示 + 用户显式确认 |
| 密钥配置（步骤四） | env 值经 `--cli-json-file` 由用户/受保护文件组装，agent 只传文件路径；展示 env 名单后确认 |
| 对外函数验签 | 红线：apig 触发函数必须含 FGS_JWT_SECRET 验签，不得降级跳过 |
| 别名切换（发布/回滚） | 展示版本差异后确认；切换≠成功，验收后才置 released |

## 输出格式

- **进度看板**（双轨）：宿主待办联动 + 聊天内步骤总览表（首条回复输出，每次步骤报告头部完整重发）

  ```
  【函数步骤总览】
  | # | 步骤 | 通过断点 | 状态 |
  |---|---|---|---|
  | 一 | 环境检查与配置 | fgs_env_ready | 🔄 进行中 |
  | 二 | 需求澄清与逻辑分解 | functions_confirmed | ⏳ 待办 |
  | 三 | 代码生成 | code_built | ⏳ 待办 |
  | 四 | 部署 | deployed | ⏳ 待办 |
  | 五 | 安全验证与发布 | released | ⏳ 待办 |
  | 六 | 前端联调 | integrated | ⏳ 待办 |
  ```

- **对接卡片**（需用户配置/输入时表格呈现）：

  ```
  【环境检查与配置】
  | 检查项 | 状态 | 获取方式 |
  |---|---|---|
  | KooCLI（hcloud） | ✅ 4.4.0 | — |
  | 认证（AK/SK） | ❌ 未配置 | devkit 注入 / hcloud configure set |
  | PROJECT_ID | ⏳ 待确认 | discover 勾选 / 控制台查询 |
  | FGS_JWT_SECRET | ❌ 受保护文件缺失 | 控制台获取 GoTrue JWT Secret 后写入，agent 不读内容 |
  ```

- **节点快讯**：`动作 · 对象 · 结果摘要`（如"创建函数 · notify-transaction · urn 已回执"）；长操作前后各一条
- **步骤报告**（每步骤完成时）：先完整重发步骤总览表（本步 ✅、下一步 🔄），再输出——目标、执行动作、gate verdict 引用、下一步预告 + 需要用户准备什么
- **失败/断点报告**：当前步骤、原因（含连续失败中止触发）、已恢复/待人工项、functions.json 状态

## 验证方法

- 每步骤通过条件即验证点（见 workflow-stages.md 三段式断言）
- 步骤五核心 = fgs-gate 负向验证：**无认证 401 / 坏 JWT 401 / 真 JWT 200 / CORS 精确 origin / OPTIONS 预检**——机器直连核验，不采信自报
- 上线后复查：functions.json 标记 integrated 且触发器 URL 可访问
- 本技能自检：`python3 tests/test_fgs_gate.py`（pytest）覆盖 gate 全分支

## 注意事项

- 密钥红线：env 值永不进 agent 上下文/trace/functions.json/会话；`SUPABASE_SERVICE_ROLE_KEY` 只允许存在于函数环境变量（usage 技能先例）
- 命令待验证：所有 hcloud FGS 命令名以步骤一 `--help` 实测为准，文档标注"知识推断"即待验证
- 更新/回滚/下线为横向操作：更新=新版本→切别名（重走步骤三~五快速路径）；回滚=别名切回+`rollback_verified`；下线=删触发器→删函数→清 artifacts→`decommissioned`
- 失败原因三分法（阻塞/可修复/待生效）与等待节奏见 workflow-stages.md

## 参考文档

- [references/workflow-stages.md](references/workflow-stages.md)：六步三段式 playbook（输入/动作/输出断言 + 白名单 + 黄金路径 + 横向操作）
- [references/project-state.md](references/project-state.md)：functions.json 契约与 trace 格式
- [references/routing-matrix.md](references/routing-matrix.md)：逻辑分工判定矩阵（Postgres RPC / pg_cron / pg_net / FunctionGraph / 边界外）
- [references/cli-commands.md](references/cli-commands.md)：KooCLI 命令链与自校准纪律
- [references/secret-management.md](references/secret-management.md)：密钥纪律、cli-json-file 隔离、CSMS v2 升级路径
- [template/](template/)：零依赖 Node.js 样板（handler/lib/config/test-events）
- [scripts/fgs-gate.py](scripts/fgs-gate.py)：机械验证门（check-contract/check-stage --verify/check-trace/check-whitelist/check-version）

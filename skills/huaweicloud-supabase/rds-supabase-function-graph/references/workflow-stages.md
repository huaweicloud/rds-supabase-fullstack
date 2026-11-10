# 工作流阶段（六步三段式 playbook）

每步骤三段式：**输入**（前置状态与材料）→ **动作序列**（🤖 agent 执行 / 🔍 核验 / 👤 用户参与）→ **输出断言**（可机器判定的完成条件）。

## 步骤一 · 环境检查与配置

- **输入**：本技能已触发；`.hwsupabase/` 目录存在或可创建；webapp.json 存在（或用户确认独立使用）
- **动作**：
  1. 🤖 `hcloud --version`；缺失 → 👤 对接卡片给出安装方式后停止
  2. 🤖 `hcloud configure test`；不通 → 👤 AK/SK 配置（与 web-build 步骤一凭据同源：devkit 或受保护文件）
  3. 🤖 核对 region 与 `HUAWEICLOUD_PROJECT_ID`
  4. 🤖 **命令面自校准**：`hcloud FGS CreateFunction --help`、`hcloud FGS CreateTrigger --help`、`hcloud FGS UpdateFunctionConfig --help`——记录实际参数名与枚举值（文档命令为知识推断，实测前不得假设）
  5. 🤖 写 functions.json 初稿（schema_version=1、webapp_ref、functions=[]、stages.history 追加 passed）
- **输出断言**：`fgs_env_ready` 记录 passed；hcloud 连通性确认输出在案
- **白名单**：`hcloud*`

## 步骤二 · 需求澄清与逻辑分解

- **输入**：`fgs_env_ready`
- **动作**：
  1. 🤖 判定矩阵逐项分类（SKILL.md 适用范围表）：Postgres RPC 可承载项 → 明确回退 web-build 步骤五并从清单剔除
  2. 🤖 函数清单对接卡片：函数名 | 运行时（Node.js18）| 触发类型（apig/timer）| env 名单 | 幂等需求 | → 👤 逐项确认
  3. 🔍 对外（apig）函数 env 名单必含 `FGS_JWT_SECRET` + `FGS_ALLOWED_ORIGINS`；交易类必含 idempotency 配置
  4. 🤖 更新 functions.json（functions[].env_names/triggers/idempotency 草案）
- **输出断言**：`functions_confirmed` passed；清单经用户确认在案；apig 函数 env 红线满足
- **白名单**：（无工具——纯确认步骤）

## 步骤三 · 代码生成

- **输入**：`functions_confirmed`
- **动作**：
  1. 🤖 复制 `template/` → `<project>/functions/<fn>/`，按清单改写 handler 业务段与 config.json
  2. 🔍 样板内置组件不得删改：lib/jwt.js（验签）、lib/cors.js（精确 origin）、lib/response.js（错误契约）、request_id 透传、结构化日志
  3. 🤖 本地自测：`node functions/<fn>/handler.js < test-events/apig.json`（样板支持 stdin 事件回放）→ 断言输出契约正确
  4. 🤖 记录 code_sha256（源目录打包前哈希）
- **输出断言**：`code_built` passed；本地自测输出在案；样板完整性满足
- **白名单**：`node*`、`npm*`、`npx*`

## 步骤四 · 部署

- **输入**：`code_built`
- **动作**：
  1. 🤖 `zip -r pkg.zip .`（产物目录；**出现 node_modules 即停止**——样板零依赖，违规）
  2. 🤖 `hcloud obs cp pkg.zip obs://<bucket>/artifacts/functions/<fn>/<sha8>/pkg.zip`（私有路径，不设公开读）
  3. 🤖 命令链（逐条按步骤一自校准结果，幂等重入——已存在则更新）：CreateFunction → UpdateFunctionCode(obs) → UpdateFunctionConfig(env) → CreateTrigger(apig, auth=none) → InvokeFunction 冒烟
  4. 👤 env 配置：用户提供 cli-json-file 路径（值由用户/受保护文件组装，agent 不读内容）；展示 env 名单后确认
  5. 🤖 触发器 URL、函数 URN 回写 functions.json
- **输出断言**：`deployed` passed；冒烟调用有响应记录；triggers[].url 为 https
- **白名单**：`hcloud*`、`zip*`、`python3*`、`node*`
- **部署≠发布**：本步骤只证明函数存在且可调用

## 步骤五 · 安全验证与发布

- **输入**：`deployed`
- **动作**：
  1. 🔍 `fgs-gate.py check-contract` → PASS
  2. 🔍 `fgs-gate.py check-stage --stage deployed --verify`（env 注入：`FGS_TEST_JWT`、`FGS_ALLOWED_ORIGIN`）——**负向硬门**：无 Authorization 401 / 坏 JWT 401 / 真 JWT 200 / CORS 精确 origin / OPTIONS 预检
  3. 🤖 `hcloud FGS CreateFunctionVersion` → `hcloud FGS CreateFunctionAlias`（prod 指向新版本）
  4. 🔍 `fgs-gate.py check-version` → PASS
  5. 🤖 functions.json.versions[] 追加 {version, sha256, alias}
- **输出断言**：`released` passed；两个 gate verdict 在案（引用原文）
- **白名单**：`hcloud*`、`fgs-gate*`、`python3*`

## 步骤六 · 前端联调

- **输入**：`released`
- **动作**：
  1. 🤖 前端 fetch 封装（引用 rds-supabase-usage 技能 SDK 契约节）：Authorization 头、request_id 生成、错误码映射
  2. 🤖 E2E：真实 GoTrue JWT 调用 → 200；同幂等键重复提交 → 单次生效
  3. 🔍 `fgs-gate.py check-stage --stage integrated --verify`
- **输出断言**：`integrated` passed；E2E 结果在案；步骤总览表全绿
- **白名单**：`node*`、`npm*`、`npx*`、`hcloud*`、`fgs-gate*`

## 黄金路径（示例）

声明步骤一 → hcloud 连通 ✓ → 自校准 ✓ → `fgs_env_ready` → 清单确认（2 函数：notify-transaction/apig+幂等、reconcile-daily/timer）→ `functions_confirmed` → 样板复制+本地自测 ✓ → `code_built` → zip→OBS→CreateFunction→env→CreateTrigger→冒烟 ✓ → `deployed` → gate 三连 PASS → 版本+别名 → `released` → fetch 封装+E2E+幂等 ✓ → `integrated`

## 横向操作

- **更新**（快速路径，参照 frontend v0.2.0）：已有 released 记录 + 同名函数新版本 → 重走步骤三~五；无 schema/env 变更时可省自校准重跑，漂移即退出快速路径
- **回滚**：`hcloud FGS UpdateAlias`（prod 切回 previous 版本）→ `fgs-gate.py check-stage --stage released --verify` 重验收 → stages 追加 `rollback_switched`、`rollback_verified`；**切换≠成功**
- **下线**：DeleteFunctionTrigger → DeleteFunction → 清 OBS artifacts → stages 追加 `decommissioned`；顺序不得颠倒（先摘流量再删资源）

## 失败原因三分法

- **阻塞**（须人工）：hcloud 认证失效、FGS 服务权限不足、OBS 桶不存在
- **可修复**（agent 重试一次）：zip 超限、触发器 path 冲突、env 名单红线缺失（回步骤二）
- **待生效**（等待后复验）：函数创建传播延迟、触发器 URL 首次可达延迟——等待 15~30s 间隔、上限 10 分钟

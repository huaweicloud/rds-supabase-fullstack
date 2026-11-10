# 密钥纪律与隔离机制

## 密钥分级

| 级别 | 项 | v1 存放位置 | 说明 |
|---|---|---|---|
| 高敏 | `FGS_JWT_SECRET`（GoTrue JWT Secret） | 函数环境变量 | 函数内验签唯一凭据；用户从控制台获取后写入受保护文件 |
| 高敏 | `SUPABASE_SERVICE_ROLE_KEY` | 函数环境变量 | usage 技能先例：只允许存在于服务端凭据存储（MCP 服务器环境、FunctionGraph 函数环境变量） |
| 高敏 | 外部系统签名密钥（如 `PARTNER_SIGN_KEY`） | 函数环境变量 | 对接外部系统场景 |
| 低敏 | `SUPABASE_URL`、`FGS_ALLOWED_ORIGINS` | 函数环境变量 | 非秘密（域名/origin 白名单） |

## 明文隔离机制（cli-json-file 模式）

agent **永不接触任何密钥值**。步骤四 env 配置流程：

1. 🤖 agent 生成 `env-body.json` **模板**：只含 env **名**与占位符（`"FGS_JWT_SECRET": "<VALUE_FROM_PROTECTED_FILE>"`）
2. 👤 用户（或受保护文件读取脚本）将模板填充为真实值文件 `env-body.real.json`，存放于 0600 权限受保护路径
3. 🤖 agent 执行 `hcloud FGS UpdateFunctionConfig --cli-json-file=<env-body.real.json 路径>`——**只传路径，不读内容**
4. 🤖 trace 记 `{"tool": "hcloud FGS UpdateFunctionConfig", "note": "env via cli-json-file <路径名>"}`——无值
5. 🤖 functions.json 只记 env_names

红线：密钥值不进 agent 上下文、不进会话、不进 trace、不进 functions.json、不进测试输出。

## 验签红线

- 对外（apig 触发）函数**必须**启用 lib/jwt.js 验签——`FGS_JWT_SECRET` 缺失即步骤二校验失败、步骤五 gate FAIL
- 仅 Timer/内部触发的函数可豁免验签（无对外 URL）
- 验签内容：HS256 签名（timingSafeEqual）、exp/nbf；iss/aud 可选（GoTrue 默认签发）
- 降级路径不存在：不得以"临时跳过验签"上线对外函数

## 获取方式（对接卡片提示）

| 密钥 | 获取方式 |
|---|---|
| `FGS_JWT_SECRET` | 华为云 RDS Supabase 控制台 → 实例 → 认证设置（GoTrue JWT Secret）；复制写入受保护文件（0600），agent 不读内容 |
| `SUPABASE_SERVICE_ROLE_KEY` | web-build 步骤三已交付的受保护文件复用（deliver_supabase_api_key 产物） |
| `PARTNER_SIGN_KEY` 等 | 用户从对应外部系统获取后写入受保护文件 |

## v2 升级路径（文档化，v1 不实施）

- **DEW CSMS + IAM 委托**：密钥存凭据管理服务，函数配置委托、运行时 SDK 拉取并按版本号缓存失效——支持轮换、环境变量不再明文
- **JWT Secret 轮换**：CSMS 双版本并存（旧+新验签窗口）→ 全函数 env 切换 → 旧版废弃
- **专享版 APIG**：自定义鉴权器（authorizer 函数验 JWT，网关缓存鉴权结果）+ CORS/流控插件 + 自定义域名——交易级防刷与网关层安全，触发条件：交易高峰、公开付费接口、需要精确限流时
- **VPC 内网直连**：函数绑 VPC/子网/安全组直达 Postgres（免公网绕行 Kong），代价为 ENI 冷启动增量——触发条件：数据面吞吐大或延迟敏感时

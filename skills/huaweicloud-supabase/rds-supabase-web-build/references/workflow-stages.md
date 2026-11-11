# 步骤 Playbook（步骤一–八）

首次创建流水线的逐步骤执行规范。**三段式**：每步骤 = 输入 → 动作序列 → 输出断言。断言标记：🤖 = `scripts/webapp-gate.py` 机械核验，🔍 = agent 经 MCP 工具或用户确认核验；**两者全过才完成步骤**。断点续作统一规则：会话开始先读 `.hwsupabase/webapp.json`，从 `last_completed_stage` 的下一步骤重入，并**重验该步骤通过条件**——不信任历史结论。加载时机：进入对应步骤执行前（见 SKILL.md 文档加载策略）。

## 执行纪律（全步骤通用）

1. **单次回复推进单一步骤**：一次用户交互最多推进一个步骤；仅当通过条件全过且下一步骤无用户决策点时才可继续
2. **等待协议**：实例创建 job、npm build、CDN 刷新等 >30s 操作 → 固定节奏轮询（job 类每 30 秒一次、上限 20 次）；等待期间**禁止发起任何无关操作**
3. **连续失败中止规则**：同一动作连续失败 2 次 → 强制停止，向用户报告失败原因与下一步选项；**禁止第三次盲目重试**
4. **工具白名单**：各步骤"允许/禁止"为硬边界；确需越界 → 先说明理由获用户同意并记 trace
5. **trace**：每个 MCP/CLI 工具调用后追加一行 `.hwsupabase/trace.jsonl`（格式见 project-state.md，无敏感值）
6. **gate**：动作完成 → 写 webapp.json → 运行 `python <技能目录>/scripts/webapp-gate.py <项目目录> check-stage --stage <标记>`（步骤五、步骤六另跑 `check-gate --number 3|4`）→ **PASS 才输出步骤报告**；FAIL 按缺项整改后重跑

## 步骤一 · 环境检查与配置

**目的**：会话环境与云侧接入配置完备：凭据、Region、RDS 与 OBS 接入点、PROJECT_ID 均已在**项目内配置**（唯一权威）或已解析并写回。

**输入**：项目配置（`.hwsupabase/`：webapp.json `environment` 段 + `secrets/`）；本机全局 devkit 登录态（仅显式确认路径）；webapp.json（存在则读 `last_completed_stage`）。**不从 agent 进程环境、shell 会话或全局环境变量读取**——同名变量可能来自其他项目或本机全局设置

**动作序列**：

1. 声明步骤一
2. **凭据检查（四选项交互确认，禁止跳过）**：以对接卡片（来源 | 级别 | 状态 ☐）呈现凭据来源供用户勾选，未获用户勾选不得推进：
   - **A 项目内 `<项目根>/.hwsupabase/secrets/`**（AK/SK 或服务 Token，0600、排除 Git）→ 勾选即采用
   - **B 项目内 devkit 凭据文件**（`HUAWEICLOUD_DEVKIT_CREDENTIALS_FILE` 指向项目内 0600 文件）→ 勾选即采用
   - **C 感知到的系统/用户级凭证配置**（本机全局 devkit 登录态、`~/.config/huaweicloud/credentials.json`、`~/.obsutilconfig`、进程环境中的 AK/SK 变量名等）→ **不得直接采用**：逐项**显示**（级别：系统/用户级；来源：文件路径或变量名；账号标识；**不显示明文**）→ 用户确认某一来源后采用，记 `credential_source=external_confirmed`；未确认 → 不采用（跨项目共享配置静默采用即边界溢出）
   - **D 用户指定或输入**：用户给出凭据文件路径，或交互输入 AK/SK/Token → **落盘项目 `secrets/`**（0600、排除 Git；agent 不回显、不记录明文）后采用
   - 四者均无 → 计入缺失清单，提醒用户经 D 提供。禁止写入全局/系统环境变量与个人级配置（shell profile、`~/.config/huaweicloud/`、`~/.obsutilconfig` 等——不新建、不覆写、不迁移）
3. **uv（含 uvx）可用**——步骤三/四动态安装 MCP 的前提（`uv --version` 验证）；缺失 → 计入缺失清单并提醒用户安装（`curl -LsSf https://astral.sh/uv/install.sh | sh`）
4. **Region（局点）确认**：读项目配置（webapp.json `environment.region`）——OBS 接入点推导与桶区域的前提；缺失 → 计入缺失清单，用户告知局点后**写入项目配置**（**不读进程/全局环境变量中的 `HUAWEICLOUD_REGION`**）
5. **RDS 接入点**：项目配置（`environment.rds_endpoint`）已有 → 直接采用；缺失且凭据就绪 → 运行 `diagnostics discover`（`uv run --directory server/mcp_server_rds_supabase_mgr python -m mcp_server_supabase.diagnostics discover`，可加 `--probe`；**凭据为 AK/SK 时命令须带 `SUPABASE_TRANSPORT=sdk_core`**，否则按 REST 模式因缺 `HUAWEICLOUD_AUTH_TOKEN` 失败）→ 从 `suggested_env` 勾选并采纳，**结果写回项目配置**；无法推导（非标准区域命名 / probe 不可达 / 报错）→ 要求用户显式指定后写回
6. **OBS 接入点：推导 → 连接测试 → 写回**：按 Region 推导 `obs.<region>.myhuaweicloud.com` → **连接测试**：`dig +short <endpoint>` 有 A 记录 + `curl -sI --max-time 10 <endpoint>` 有 HTTP 响应（任意状态码即通——未认证访问返回 4xx 属预期，判定的是网络连通而非鉴权；超时/DNS 无解析 = 不通）→ 通过 → 写回项目配置；**无法推导（Region 非标准）或测试不通 → 缺失清单提示用户输入**实际接入点，用户输入后同样复测——通过才写回，仍不通则如实报告不强行采用
7. **PROJECT_ID**：项目配置（`environment.project_id`）已有 → 采用；缺失 → `diagnostics discover` 勾选，**写回项目配置**；无法获取 → 要求用户显式指定后写回
8. **五项终检（写入 environment_ready 前的最后一道校验）**：**REGION、AK/SK、PROJECT_ID、RDS_ENDPOINT、OBS_ENDPOINT 五项逐项核验正确无误**：
   - **AK/SK、REGION、PROJECT_ID、RDS_ENDPOINT 四项**：一次 `diagnostics discover` 实际调用同时验证——凭据有应答 = AK/SK 正确；局点可解析 = REGION 有效；应答含该值 = PROJECT_ID 正确；endpoint 可达 = RDS_ENDPOINT 正常（可加 `--probe`；**AK/SK 凭据时命令须带 `SUPABASE_TRANSPORT=sdk_core`**）
   - **OBS_ENDPOINT**：按第 6 项连接测试规则复测（DNS 解析 + HTTP 探测，任意状态码即通）
   - 任一项不通过 → **对接卡片反馈用户**（哪项、实测现象）→ **二次输入确认**：用户修正该值后**仅复测该项**，通过才计入就绪；仍不通过 → 如实报告该项不可用，**不写 `environment_ready`**（禁止带病通过）
9. **缺失清单处置**：存在缺失项 → 以**对接卡片**表格呈现（检查项 | 状态 ✅/❌/⏳ | 获取方式，格式见 SKILL.md 输出格式），显式提醒用户逐项设置并等待补齐（不得猜测、不得跳过、不得以默认值代替）；补齐后重新检查
10. 全部就绪且**五项终检通过** → 写 webapp.json（`environment` 段：region/rds_endpoint/obs_endpoint/project_id/credential_source + stages: environment_ready；终检的 discover 调用与探测记 trace）→ gate → 步骤报告

**输出断言**：🔍 凭据、uv、Region、RDS 接入点、OBS 接入点（**连接测试通过**）、PROJECT_ID 全部已在**项目内配置**（缺失清单为空；无一项取自进程/全局环境）且**经五项终检核验正确**（discover 实际调用 + 连接探测）｜🤖 gate PASS（environment 契约 + trace 强制）

**工具白名单**：允许：`diagnostics discover`（只读 IAM 查询）、读写 webapp.json；禁止：一切业务 MCP 工具（管理面尚未启动，实例操作不得提前执行）

**黄金路径**：
```
声明步骤一 → 凭据四选项勾选：A 项目 secrets/ ✓ → uv --version ✓ → 项目配置 environment.region=cn-north-4 ✓
→ discover --probe → 勾选 p-123 / 采纳 https://rds.cn-north-4.myhuaweicloud.com，写回项目配置 ✓
→ OBS 接入点推导 obs.cn-north-4.myhuaweicloud.com → 连接测试（dig 有解析 + curl 响应）✓ → 写回 → PROJECT_ID=p-123 写回 ✓
→ 五项终检：discover 一次实际调用 ✓（AK/SK + REGION + PROJECT_ID + RDS_ENDPOINT 同验）+ OBS 复测 ✓
→ 缺失清单为空 → 写 webapp.json(environment 段 + environment_ready) → gate PASS → 步骤报告（下一步骤预告：需求澄清与设计）
```

**失败处置**：任一项无法获取 → 缺失清单提醒用户设置后重检；凭据缺失 → 经 D 指定/输入，或经 C 显示确认系统/用户级配置。**断点**：`environment_ready`

## 步骤二 · 需求澄清与设计

**目的**：经**多轮对话或 SDD 规格驱动设计**，透彻掌握用户 Web 应用的场景、功能与边界——**不遗留、不发散、聚焦不走偏**；据此提炼 RDS Supabase BaaS 能力需求清单并逐项评估满足性，产出经确认的设计共识。

**输入**：用户单句需求；（已有项目）webapp.json 的 `last_completed_stage`

**动作序列**：

1. 输出步骤声明（格式见 SKILL.md 执行纪律）
2. **多轮澄清或 SDD 规格驱动**（以对接卡片表格逐轮呈现：确认项 | 内容 | 状态 ☐，格式见 SKILL.md 输出格式）：围绕「场景 × 功能 × 边界」三要素收敛——
   - 场景：目标用户、使用情境、核心用户旅程
   - 功能：网站类型与页面清单 / 数据模型草案（实体、关系、对外暴露表）/ 认证需求 / **文件、图片、视频管理诉求** / AI 能力（pgvector 语义检索、Realtime 订阅）
   - 边界：明确不做什么与非功能约束
   - 纪律：**不遗留**（清单逐项确认后才过关）、**不发散**（偏离场景的诉求记录为备注、不入主线）、**聚焦不走偏**（每轮结束复述当前共识与用户校准；无新增即收敛）
3. **网站设计指标——交互式逐项确认**（以设计指标卡呈现，维度 | 选项 | 默认/建议，经用户确认后记入 `project.design_requirements`）：
   - **网站风格**：简约现代 / 商务专业 / 活泼年轻 / 暗色科技 / 自定义描述——结合目标用户与使用情境给出推荐项
   - **界面设计**：导航结构（顶部导航 / 侧边栏 / 混合）、响应式优先级（**移动优先**（默认）/ 桌面优先）、组件库偏好（默认项目技术栈自带，用户指定则从其指定）
   - **美观度分级**：`prototype`（原型级——默认样式、能用即可，适合快速验证）/ `standard`（标准级——整洁统一、基础美化、完整响应式，**默认**）/ `premium`（精品级——视觉层次、动效与细节打磨、设计感优先）
   - **复杂度分级**：`simple`（≤3 页、基础交互）/ `medium`（4–8 页、表单与状态反馈，**默认**）/ `rich`（>8 页、实时更新/拖拽等富交互）——**与页面清单联动核对**，不一致以用户确认结果修正
   - **功能性交互反馈**：loading 状态 / 错误提示 / 空状态呈现要求（默认全套基础反馈）——**与功能矩阵联动**
   未逐项确认不得推进；用户仅说"随意/你来定" → 采用默认值并向用户复述确认
4. **BaaS 能力提炼与满足性评估**（映射矩阵逐项记录）：

   | 诉求 | RDS Supabase 能力 | 满足性 |
   |---|---|---|
   | 数据建模与 CRUD | PostgREST 自动接口 | 核心路径，满足 |
   | 业务逻辑 | Data-Function（库内 RPC） | 满足；复杂逻辑 → function-graph 技能 |
   | 认证 | GoTrue | 满足 |
   | 文件/图片/视频管理 | **Storage（对接 OBS）** | 满足——**标记 `storage`，触发步骤三 Storage 桶准备与对接** |
   | 实时订阅 | Realtime | 满足（可选） |
   | 语义检索 | pgvector | 满足（可选） |

5. **Storage 专项判定**：存在文件/图片/视频管理诉求 → 能力清单记入 `storage` → **步骤三必须完成专用私有 OBS 桶准备与 `update_supabase_storage` 对接**；**禁止复用前端托管桶**（该桶为公开读，复用即权限越界与隐私暴露）
6. 边界外识别明确告知（不擅自模拟）：复杂业务逻辑（支付/第三方/长任务）→ 路由 rds-supabase-function-graph 技能（云函数）；SSR 不支持
7. 费用预估清单（实例规格/时长、**前端托管桶与 Storage 桶分别列示**、CDN 流量、域名证书；**美观度 premium 或复杂度 rich 提示相应工作量影响**）→ 用户确认
8. 写 webapp.json：`project.requirements_summary`（脱敏）+ `project.baas_capabilities`（能力清单，枚举 database/auth/rpc/storage/realtime/vector）+ `project.design_requirements`（style/aesthetics/complexity/ui_notes）+ history 追加 passed 事件
9. 跑 gate（check-stage --stage requirements_confirmed）→ 步骤报告

**输出断言**：🔍 用户逐项确认需求摘要、数据模型、能力清单**与网站设计指标**（不默认、不放大模糊表述；设计五维全部有确认值）｜🤖 gate PASS

**工具白名单**：允许：读写 webapp.json；禁止：**一切 MCP 工具**

**黄金路径**：
```
用户：帮我建一个博客网站，支持登录评论和文章配图上传
→ 声明步骤二 → 多轮澄清（页面清单 / Posts-Comments-Users 模型 / 邮箱登录 / 文章配图上传 = 文件管理诉求 / 无 AI 检索）
→ 设计指标卡确认：风格=简约现代 · 界面=移动优先 · 美观度=standard · 复杂度=medium · 交互反馈=全套基础
→ 能力矩阵：database + auth + rpc + storage（配图上传 → storage 标记）
→ 边界与费用清单（实例 / 前端托管桶 / Storage 私有桶 分列）确认 → 写 webapp.json(requirements_summary + baas_capabilities + design_requirements)
→ gate PASS → 步骤报告（步骤二）（下一步骤预告：凭据与区域信息；步骤三将准备 Storage 私有桶并对接）
```

**失败处置**：需求不清 → 继续多轮澄清直至收敛；用户取消 → 停止，不创建任何资源。**断点**：`requirements_confirmed`

## 步骤三 · 资源准备

**目的**：管理面就绪、实例可用（用户显式勾选新建或使用已有）、凭据交付、OBS 桶就绪（用户显式勾选新建或使用已有公开读桶）。

**输入**：步骤一通过后的环境配置（凭据 / Region / RDS·OBS 接入点 / PROJECT_ID）；上一断点 `requirements_confirmed`

**动作序列**：

1. 声明步骤三；复核步骤一环境配置（凭据 / Region / RDS·OBS 接入点 / PROJECT_ID）仍就绪，发现缺项 → 返回步骤一补齐
2. **管理面就绪（安装时机硬门槛）**：**凭据（AK/SK 或 Token）、`SUPABASE_RDS_ENDPOINT`、Region、`HUAWEICLOUD_PROJECT_ID` 四项全部正确获取并核验后，才开始动态启动管理面 MCP**——任一项缺失或未核验 → 返回步骤一补齐后再来，不带着配置缺口反复尝试安装（否则将持续报凭据/接入点类故障）。检测已连接 MCP（devkit 预初始化）；无则动态启动——**安装来源只允许本仓**：uvx 模板 `git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr`（入口 `mcp-huaweicloud-rds-supabase-mgr`；**生产建议 pin `@<commit>` 锁定版本，避免默认分支变更引入未验证行为**）或本地 `uv run --directory <仓>/server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr`；**禁止**从 PyPI/第三方仓搜索安装（存在同名第三方包）。启动 env **凭据模式二选一**（**值一律由项目内配置注入进程**——步骤一 `environment` 段与 `secrets/`，不读取会话/全局环境）：REST token（`HUAWEICLOUD_AUTH_TOKEN`，默认 `SUPABASE_TRANSPORT=rest`）或 **AK/SK（必须设置 `SUPABASE_TRANSPORT=sdk_core`**，读取 `HUAWEICLOUD_ACCESS_KEY`/`HUAWEICLOUD_SECRET_KEY`/可选 `HUAWEICLOUD_SECURITY_TOKEN`——用户已填 AK/SK 而未设 `sdk_core` 将按 REST 模式启动并失败）。**网络逃生通道**：uvx git 拉取失败或停滞（含代理后仍不通；连续失败 2 次或 30 秒无进展即判失败）→ **立即切换** ZIP 归档（`TMP=$(mktemp -d)`，`curl -L --fail --max-time 120 -o "$TMP/rds.zip" https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip && unzip -q "$TMP/rds.zip" -d "$TMP"`；浏览器直接下载该 URL 亦**落临时目录**）+ 本地模板 `uv run --directory "$TMP/rds-supabase-fullstack-main/server/mcp_server_rds_supabase_mgr" mcp-huaweicloud-rds-supabase-mgr`——**下载物一律落唯一临时目录（mktemp -d），不污染项目目录/家目录；MCP 运行期间保留、停止后清理**——ZIP 属本仓官方源，不违反来源锁定，仍禁 PyPI/第三方源。启动后遵循 mgr-mcp 技能两阶段确认与执行账本
   **网络与验证纪律**：**默认不走代理直连局点**（内网/专线环境经代理转发常引入链路故障；**禁止上来就走代理**——代理是兜底项而非默认项）；安装完成后执行**连接验证**：确认 MCP 连接 OK，且任一**查询类工具**（优先 `get_supabase_capabilities`，一个即可）正常返回——验证通过才算安装成功；直连验证失败 → 依次核对网络可达性、凭据模式（AK/SK 须 `SUPABASE_TRANSPORT=sdk_core`）、Endpoint，**确认直连不可达后**再显式配置代理（记录所配代理）并复验
   **注册位置（项目级强约束）**——MCP 启动后只注册进当前项目的项目级 MCP 配置（当前项目之外不可见；用户级/系统级注册 = 本机所有项目可见可用 = 边界溢出，严禁）：

   | 宿主 | 项目级 MCP 配置（唯一允许） | 条目结构 | 禁止（用户级/系统级） |
   |---|---|---|---|
   | Claude Code | `<项目根>/.mcp.json`（project scope） | `mcpServers` 键 | `~/.claude.json`（user scope）、Claude Desktop `claude_desktop_config.json`、系统 managed 配置 |
   | CodeArts | `<项目根>/.codeartsdoer/` 下项目级 MCP 配置（与技能目录同根） | 按宿主项目级结构 | `~/.codeartsdoer/` 个人级（同名不同根） |
   | OfficeAce | 项目根下该宿主项目级 MCP 配置（Agent 自知位置，以项目根为界） | 按宿主项目级结构 | `~` 家目录与系统目录下的一切该宿主配置 |
   | opencode | `<项目根>/opencode.json` 或 `.opencode/` 内配置 | `mcp` 键 | `~/.config/opencode/` 全局配置 |
   | 其余宿主 | 该宿主项目级机制（Agent 自知位置，以项目根为界） | 按宿主项目级结构 | 同上 |

   规则：宿主仅有用户级机制 → **停止并报告，不注册**（宁缺毋溢出）；配置含凭据 → 该文件列入 `.gitignore`、0600，凭据由用户从 secrets/ 复制填入（agent 不经手明文）；**严禁 `uv tool install`/`pip install` 装入用户级/系统级环境**——`uvx` 为一次性缓存运行（共享构建缓存非安装非注册，不落命令行入口），本地克隆 `.venv` 只落仓内目录；**注册后核验落位**：确认条目存在于项目级配置且未触碰任何用户级/系统级位置 → 客户端重载 → 连接验证 → 写 webapp.json `mcp` 段（`registration_scope`/`config_paths.mgr`，契约见 project-state.md）
3. **实例接入方式——交互式勾选（强制，禁止跳过）**：以选择清单形式向用户呈现「使用已有 Supabase 应用 / 新建 Supabase 应用」，**未获用户显式选择不得推进，不得代为默认**（步骤二费用预估在先，本步骤执行用户已确认的方案）：
   - **使用已有**：`list_supabase_applications` → 列表展示（application_id/名称/状态/规格）供用户勾选 → `show_supabase_application` 核验（normal/running、无进行中任务、网关可达）→ **随即执行第 4 项（凭据获取）**：网关 URL 与两类密钥为步骤四数据面 MCP 动态安装的必需输入，不得遗漏
   - **新建**：`plan_supabase_creation` + `create_supabase_application`（仅 Single；关联已有 PG 或新 PG）→ 配置 EIP、安全组（8443 入站）、SSL → 等待协议轮询 job；创建完成后**同样必须执行第 4 项**（凭据获取）；创建安全组 ≠ 可访问，须规则放通并核验
4. **凭据获取（两条路径都必经——缺失任一项则步骤四无法安装，流水线中断）**：网关 URL + Anon Key + Service Role Key（**两类密钥均须获取**），经管理面 ApiKey 交付工具 deliver 到受保护本地文件——**项目内路径**：`SUPABASE_REQUESTS_FILE=<项目>/.hwsupabase/requests.json` 注册，交付落盘 `.hwsupabase/secrets/`（0600、排除 Git，不写入全局变量与个人级配置）；webapp.json 只记 env 名 + `instance.source`（`created`/`selected`）
5. **OBS 桶接入方式——交互式勾选（强制，禁止跳过）**：以选择清单形式向用户呈现「使用已有 OBS 桶 / 新建 OBS 桶」，**未获用户显式选择不得推进，不得代为默认**（frontend 技能引导，凭据与 Region 均为步骤一所核对）：
   - **使用已有**：列出租户桶 → **候选过滤：仅保留满足静态托管要求的公开读桶**——匿名 GetObject 未获授权的非公开桶一律剔除，**不得出现在候选列表中**；候选展示（桶名/区域/存储类别）供用户勾选 → 核验选中桶区域与项目 Region 一致、具备静态网站托管能力
   - **新建**：**桶名默认与应用名称保持一致**——应用名称英文化：转小写，非 ASCII 与非法字符映射为连字符、连续连字符压缩为单个、去除首尾连字符、长度裁剪至 3–63；**名称冲突（同名桶已存在）→ 追加短 uuid 后缀**（连字符连接，形如 `my-webapp-3f2a1b9c`；再次冲突则重新生成后缀并复核唯一性）；最终桶名经用户确认后由 frontend 技能创建——**创建前展示桶配置卡**（存储类别**多 AZ 优先**，区域不支持时降级单 AZ 并说明；**阻止公网访问必须关闭**——该开关开启则匿名读被拒、静态托管不可用；**桶策略固定公共读**：仅匿名 GetObject，不可改为其他），经用户确认后创建，**创建后回读核验三项实际生效**
   - 域名条件核对；**证书仅当实例 SSL 开启（前端 HTTPS 入口）时必需**——SSL 未开启则前端以 HTTP 发布、无需证书；不齐备项于步骤八前补齐
6. **Storage 桶准备与对接（仅当步骤二能力清单含 `storage`）**：交互式勾选「使用已有桶 / 新建桶」（纪律同实例与前端桶：未获用户显式选择不得推进，不得代为默认）：
   - **使用已有**：先做**桶策略安全评估**——桶必须私有（无公开读、无匿名 GetObject、无公开列举、无通配匿名授权）；存在任一公开项即判定策略不合理 → 停止并说明，建议转新建或先修正桶策略
   - **新建**：**一律私有桶**（禁止公开读），按最小权限配置；桶名建议 `<应用slug>-storage`
   - **两类均禁止复用前端托管桶**（`obs.bucket_name`——公开读桶复用即权限越界与隐私暴露）
   - 选定后经管理面 `update_supabase_storage` 完成对接（凭据 bucket/AK/SK 经 request_ref、两阶段确认；首次启用需 SK，见 mgr-mcp 技能）→ 核验对接生效
7. 写 webapp.json（instance 段 + `obs` 段：`bucket_name`/`source`/`naming_basis` + `mcp` 段：`registration_scope`/`config_paths.mgr` + `storage` 段（能力含 storage 时）：`bucket_name`/`source`/`connected`，契约见 project-state.md）→ gate → 步骤报告

**输出断言**：🔍 实例 running 且实际可访问，接入方式经用户显式勾选确认｜🔍 桶就绪且接入方式经用户显式勾选确认（公开读核验通过）｜🔍 Storage 桶（如诉求存在）私有、未复用前端托管桶且对接生效｜🔍 管理面 MCP 连接验证通过（查询工具一次调用 OK，默认直连未走代理）｜🔍 管理面 MCP 注册落位项目级配置（核验通过，未触碰用户级/系统级）｜🤖 gate PASS（instance 契约 + `source` 枚举 + obs 契约 + mcp 契约 + storage 契约）

**工具白名单**：允许：管理面 list/show/plan/create/wait/ApiKey 交付、`diagnostics discover`、frontend 技能 KooCLI（OBS 桶）；禁止：数据面 MCP（尚未安装）、一切 SQL 执行

**黄金路径**：
```
声明步骤三 → 复核环境 ✓ → 启动管理面 MCP（uvx git 模板）→ 呈现实例接入方式选择清单：用户勾选「使用已有」
→ list_supabase_applications → 用户勾选 app-123 → show_supabase_application 核验 normal
→ list_supabase_api_keys + deliver → 受保护文件（agent 不见明文）
→ 呈现 OBS 桶接入方式选择清单：用户勾选「新建」→ 桶名取应用名英文化 webapp-demo（无冲突，用户确认）
→ frontend 技能建桶 + 公开读策略 → 能力清单含 storage（文章配图）→ Storage 桶勾选「新建」demo-storage（私有桶）→ update_supabase_storage 对接（两阶段确认）✓
→ 管理面 MCP 注册项目级配置（如 .opencode/mcp.json）+ 核验未触碰用户级/系统级
→ 写 webapp.json(instance.source=selected, obs.source=created, mcp.registration_scope=project, storage.connected=true)
→ gate PASS → 步骤报告（步骤三）（下一步骤预告：重载客户端后安装数据面 MCP）
```

**失败处置**：环境缺项 → 返回步骤一补齐；**MCP 安装反复失败 → 先回查四项前置（凭据/Endpoint/Region/PROJECT_ID）与凭据模式，再查网络——直连失败才考虑代理（禁止上来就走代理）**；创建结果未知 → 管理面账本 `inspect_supabase_plan`，不重复提交；配额/权限不足 → 停止报告缺项；公开读候选桶为空 → 呈现空清单并引导用户转入新建分支；新建桶名冲突 → 重新生成短 uuid 后缀并复核唯一性。**断点**：`instance_ready`

## 步骤四 · 数据面接入

**目的**：数据面 MCP 就绪并连通 RDS Supabase。

**输入**：步骤三 交付的网关 URL + 两把 Key（受保护文件）；上一断点 `instance_ready`

**动作序列**：

1. 声明步骤四
2. 按 `rds-supabase-mcp 技能 references/install.md` 动态安装；**来源只允许本仓**——完整命令：`uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`（或本地克隆 `uv run --directory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase`；服务器文档：https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/README.md ）。**网络逃生通道**：uvx git 拉取失败或停滞（含代理后仍不通；连续失败 2 次或 30 秒无进展即判失败）→ **立即切换** ZIP 归档（`TMP=$(mktemp -d)`，`curl -L --fail --max-time 120 -o "$TMP/rds.zip" https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip && unzip -q "$TMP/rds.zip" -d "$TMP"`；浏览器直接下载该 URL 亦**落临时目录**）+ 本地模板 `uv run --directory "$TMP/rds-supabase-fullstack-main/server/mcp_server_rds_supabase" mcp-server-huaweicloud-rds-supabase`——**下载物一律落唯一临时目录（mktemp -d），不污染项目目录/家目录；MCP 运行期间保留、停止后清理**——ZIP 属本仓官方源，不违反来源锁定。禁止搜索 PyPI 同名包。**网络纪律同步骤三**：默认直连不走代理（禁止上来就走代理）；装后以既有验证项（`get_project_url` / `list_tables`，一个查询即可）确认连接 OK；直连失败才考虑代理
3. 凭据注入（**来源与作用域**）：数据面**无 `SUPABASE_TRANSPORT` 参数、不使用华为云 AK/SK**——凭据为网关三件套（`SUPABASE_URL` + 两把 Key），**值一律取自项目内 `.hwsupabase/secrets/`**（半自动路径：agent 生成含占位符的 mcpServers 配置模板 → 用户从**项目内**受保护文件复制实际值填入 → 客户端重载；agent 全程不接触明文；**不从会话/全局环境读取**）。**注入作用域限于 MCP 进程**（进程 env 或项目内 0600 凭据文件）——不 `export` 到 shell 会话、不写入 shell profile 或任何全局/个人级配置
4. **访问协议跟随实例 SSL 状态**（`SUPABASE_URL` 取值规则）：开启 SSL → `https://`；未开启 → `http://`（**不强制 HTTPS 交互**；步骤三已将 `instance.ssl_enabled` 记入 webapp.json，gate `--verify` 对 `ssl_enabled=false` 放行 http）
5. **注册纪律（与步骤三同表同禁令）**：数据面 MCP **只注册进当前项目的项目级 MCP 配置**（宿主仅有用户级机制 → 停止并报告，不注册；含凭据的配置文件列入 `.gitignore`、0600）；注册后核验落位 → 客户端重载 → 写 webapp.json `mcp.config_paths.data`
6. 验证：`get_project_url` 返回 == 网关地址；`list_tables` 正常应答
7. 写 webapp.json（stages: mcp_connected + `mcp.config_paths.data`）→ gate → 步骤报告

**输出断言**：🔍 `get_project_url` 与网关一致 + `list_tables` 应答（连通性以工具结果证明）｜🔍 数据面 MCP 注册落位项目级配置（核验通过，未触碰用户级/系统级）｜🤖 gate PASS

**工具白名单**：允许：数据面 `get_project_url`、`list_tables`（仅验证）；禁止：`execute_sql`（步骤五才用）、一切写工具

**黄金路径**：
```
声明步骤四 → 渲染 install.md 模板（占位符）→ 用户从受保护文件复制实际值填入 → 客户端重载
→ 数据面 MCP 注册进项目级配置（如 .opencode/mcp.json）+ 核验未触碰用户级/系统级
→ get_project_url == https://gw.example:8443 ✓（本例 SSL 开启；未开启时为 http://，gate 按 ssl_enabled=false 放行）→ list_tables 应答 ✓
→ 写 webapp.json(mcp_connected, mcp.config_paths.data) → gate PASS → 步骤报告（步骤四）
```

**失败处置**：401/403 → 核对凭据注入路径；连接失败 → 网关地址/安全组规则；重载后仍失败 → 检查旧环境残留（连续失败中止规则：连续 2 次失败即停下报告）。**断点**：`mcp_connected`

## 步骤五 · 后端生成部署

**目的**：强制门对照后生成 init.sql 与一键清理脚本 teardown.sql，并单一事务部署。

**输入**：确认过的数据模型；数据面 MCP（步骤四已连通）；上一断点 `mcp_connected`

**动作序列**：

1. 声明步骤五
2. **【强制门】读 rds-supabase-postgres-best-practices 技能**（按症状/任务索引规则文件）+ rds-supabase-usage 客户端消费视角
3. 生成 init.sql（表/索引/RLS 策略/GRANT/种子/RPC；可重复执行写法 `IF NOT EXISTS`/`CREATE OR REPLACE`/`ON CONFLICT`；pgvector → 向量列+索引+相似度 RPC）
4. **同步生成一键清理脚本** `.hwsupabase/teardown.sql`（与 init.sql 同源产出，供下线/换实例时一键执行）：
   - **单事务包裹**（BEGIN/COMMIT）、**全语句幂等**（`DROP ... IF EXISTS`），无需人工改写即可整体执行
   - **依赖安全序**：DROP POLICY → DROP TRIGGER → DROP TABLE → DROP FUNCTION（含 RPC）→ DROP ROLE（如 init.sql 创建）→ DROP SCHEMA（如创建）
   - **仅覆盖部署清单内对象**（与 webapp.json `deployments[].objects` 一致），不触碰部署范围外的任何对象；种子数据随表删除
   - 增量批次部署后**同步刷新**（累计对象清单），保持与当前 schema 一致
5. **产出规则对照表** `.hwsupabase/gates/3-rules-checklist.md`：best-practices 每条适用规则 → init.sql 对应位置映射（≥5 条映射行，格式 `- <规则> → init.sql L<行号>`）——**gate 校验，缺即拦下**
6. 部署（数据面五步）：预检 → 审查（可重复执行/破坏性语句逐条确认/RLS 覆盖/最小授权）→ `execute_sql` 单一事务 → 授权暴露（GRANT + `NOTIFY pgrst, 'reload schema'`）→ 查询确认
7. 部署批次写入 webapp.json（batch_id/`objects` 对象清单/`exposed` 对外表清单/init.sql sha256/**`teardown_ref`**）→ 跑 `check-gate --number 3` + `check-stage --stage backend_deployed --verify --mcp-command "<与步骤四同源的数据面启动命令>"`——REST 可达、对外表 anon 200、RLS 与 advisors 由 gate 直连机器核验（凭据经进程 env 注入，agent 不经手明文，不采信自报）→ 步骤报告

**输出断言**：🔍 结构确认（`list_tables`/`list_constraints`）｜🤖 gate `--verify` PASS（对照表有效 stem ≥5 + deployments 契约 + sha256 + **teardown 对象全覆盖** + 机器验真：REST 可达/对外表 anon 200/RLS 启用且有策略/advisors 无命中）

**工具白名单**：允许：数据面全部只读 + `execute_sql`；禁止：管理面写工具（auth 配置属步骤八）、前端构建

**黄金路径**：
```
声明步骤五 → 读 best-practices 索引 → 生成 init.sql（Posts/Users/Comments + RLS + GRANT + RPC）
→ 同步生成 teardown.sql（单事务 + IF EXISTS + 依赖安全序，覆盖全部部署对象）
→ 写 gates/3-rules-checklist.md（8 条规则→SQL 行号）
→ 五步部署：预检 → 审查确认 → execute_sql(单一事务) → NOTIFY pgrst reload schema
→ list_tables 核对 → get_rls_status → get_advisors(security) 无新增 → REST 200 ✓
→ 写 webapp.json(backend.deployments[b1]) → check-gate 3 PASS + check-stage PASS → 步骤报告（步骤五）
```

**失败处置**：批次失败自动整体回滚（单一事务）→ 修正脚本再部署；advisors 报告 → 按 remediation 处理后复核；连续 2 次部署失败 → 停下报告。**断点**：`backend_deployed`

## 步骤六 · 前端生成

**目的**：强制门对照后生成可构建的前端源码。

**输入**：步骤五的表结构与 RPC 契约；上一断点 `backend_deployed`

**动作序列**：

1. 声明步骤六
2. **【强制门】读 rds-supabase-usage 技能**（SDK 正确用法：会话管理、RLS 语义、错误契约 `{"error":{code,message,hint}}`）
3. 生成源码（默认 React+Vite+TS + supabase-js；用户已指定框架则沿用其静态导出方案）；anon key 经 env 注入构建；凭据仅 anon key 进产物
4. **产出 SDK 契约对照表** `.hwsupabase/gates/4-sdk-contract-checklist.md`：usage 契约点 → 代码位置映射（会话管理/RLS 语义/错误契约/env 注入/Realtime 清理，≥5 条）——**gate 校验，缺即拦下**
5. `npm run build` → 本地冒烟（首页渲染 + 1 条 RLS 查询 + 1 次 auth 流）——按等待协议处理构建耗时
6. 写 webapp.json（frontend 段）→ 跑 `check-gate --number 4` + `check-stage --stage frontend_built` → 步骤报告

**输出断言**：🔍 构建成功 + 本地冒烟通过（"本地应用已验证"语义）｜🤖 gate PASS（对照表 ≥5 映射 + frontend 契约）

**工具白名单**：允许：数据面只读（对照表结构/RPC 签名）；禁止：`execute_sql`、管理面一切工具

**黄金路径**：
```
声明步骤六 → 读 usage 技能 → 脚手架 react-vite-ts → 实现页面/auth/数据层
→ 写 gates/4-sdk-contract-checklist.md（6 条契约点→代码位置）
→ npm run build ✓ → 本地冒烟（首页渲染 / RLS 查询返回受限数据 / 登录流验证通过）✓
→ 写 webapp.json(frontend.*) → check-gate 4 PASS + check-stage PASS → 步骤报告（步骤六）
```

**失败处置**：构建错误 → 修正；运行时错误 → 对照 usage 规则排查；连续 2 次同错 → 停下报告。**断点**：`frontend_built`

## 步骤七 · 本地测试验证

**目的**：前端本地部署并与已部署后端联调，按功能场景孵化 L0 级用例完成全面基本功能验证，修复循环直至全部用例通过——应用功能正常可用才进入托管发布。

**输入**：步骤六 前端产物（源码 + 构建通过）；步骤五 已部署后端（真实网关与数据）；步骤二 功能场景清单；上一断点 `frontend_built`

**动作序列**：

1. 声明步骤七
2. **本地联调环境**：本地运行前端（dev server 或构建产物预览），supabase-js 直连已部署后端网关（anon key 进前端、Service Role Key 不进）；以 1 条数据查询确认前后端通路
3. **L0 用例孵化**（从步骤二功能场景逐项孵化，不发散——只覆盖已确认场景）：
   - 每场景 ≥1 条正向用例 + 关键负向用例；覆盖维度：页面渲染、核心 CRUD 交互、认证流（注册/登录/登出/权限区分）、RLS 数据可见性（匿名 vs 登录态、用户间隔离）、错误路径（无效输入/未授权访问）
   - 用例清单（T 编号：T01/T02/…，含场景、步骤、预期）以表格呈现，**经用户确认后执行**
4. **执行与修复 Loop**：逐条执行并记录（passed/failed + 现象）→ 失败定位修复——前端缺陷 → 改前端源码；后端问题（结构/RLS/种子）→ 步骤五增量批次重部署；用例本身有误 → 修订用例并复确认 → **重新执行，循环直至全部用例通过**（同一用例连续 2 次失败 → 强制中止报告）
5. **产出测试报告** `.hwsupabase/gates/5-local-test-report.md`：每用例一行，格式 `- T<编号>：<场景/用例名> → passed`（修复记录附后）——gate `check-gate --number 5` 校验（≥5 条 passed、零 failed）
6. 写 webapp.json（stages: local_verified）→ 跑 `check-stage --stage local_verified` + `check-gate --number 5` → 步骤报告

**输出断言**：🔍 全部 L0 用例 passed（报告留档，gate 校验）｜🔍 前后端联调通路实证（本地前端 ↔ 已部署后端）｜🤖 gate PASS

**工具白名单**：允许：npm/npx/node（本地运行与测试）、数据面只读（`list_*`/`get_*` 核对）、读写 webapp.json；禁止：OBS/CDN 托管操作（步骤八）、实例级管理面写

**黄金路径**：
```
声明步骤七 → 本地 dev server 起前端（supabase-js 连网关）→ 首页数据查询 ✓
→ 孵化 L0 用例 8 条（3 场景 × 正负向）→ 用户确认用例清单
→ T01–T06 ✓ / T07 ✗（RLS 策略遗漏）→ 步骤五增量批次修复 → T07 ✓ / T08 ✓
→ 写 gates/5-local-test-report.md（8 passed）→ check-gate 5 PASS + check-stage PASS
→ 步骤报告（步骤七）（下一步骤预告：构建与托管）
```

**失败处置**：用例连续 2 次失败 → 中止报告（含失败现象与已尝试修复）；后端问题回步骤五处置后重验；用户中止 → 保留断点，不进入托管。**断点**：`local_verified`

## 步骤八 · 构建与托管

**目的**：静态产物发布到步骤三预建桶，按用户确认的托管场景（临时访问 / 正式上线）形成稳定入口，完成回调回路。

**输入**：步骤六 产物源码；步骤三 预建桶与域名（证书仅 HTTPS 入口——`ssl_enabled=true` 时必需）；上一断点 `local_verified`

**动作序列**：

1. 声明步骤九
2. frontend 技能：构建环境核对（Node/包管理器，不擅自升级）→ build → 上传步骤三预建桶 → 版本记录（`.hwsupabase/frontend/` 契约；CDN 刷新仅正式模式）。**托管入口协议跟随实例 SSL**：`ssl_enabled=true` → HTTPS 入口（域名/证书就绪）；`false` → HTTP 入口（无需证书，**不得 HTTPS**——HTTPS 页面调用 HTTP 网关属混合内容，被浏览器拦截，站点不可用）
3. **托管场景选择——交互式勾选（禁止跳过）**：产物上传后、入口配置前，以选择清单呈现两种场景方式，未获用户确认不得推进（不得代为默认）：
   - **临时访问（原型验证/测试验证）**：适用无正式域名与备案的快速验证——**确定性自动配置**，不购买域名、不办理 ICP 备案、不接 CDN：
     1. **域名确定（可复现，不随机不询问）**：`<应用名英文化>.huaweicloud-rds.com`——英文化 slug 规则同桶名（小写字母/数字/连字符、3–63）；slug 为空或与现存未清理映射冲突 → 追加短 uuid 后缀
     2. **OBS 域名管理新增自定义域名**：为托管桶绑定上述域名（经 `hcloud obs --help` 确认域名管理子命令或 OBS API 设置桶自定义域名；执行前按官方帮助核实命令与字段，不猜测）
     3. **本机 hosts 追加映射**（禁止破坏已有映射）：
        - 解析 OBS endpoint（`environment.obs_endpoint`，缺省按 region 推导）的 A 记录 IP（`dig +short <endpoint>` / Windows `Resolve-DnsName`，多值取首个）
        - hosts 定位：Linux/macOS `/etc/hosts`；Windows `%SystemRoot%\System32\drivers\etc\hosts`
        - **只追加带标记行**：先完整读取并检索目标域名——已存在且 IP 相同 → 幂等跳过；已存在且 IP 不同 → **仅替换本流程标记行**（标记注释 `# rds-supabase-web-build:<项目名>`），其余任何行一律不动；**修改前备份** `hosts.rds-supabase.bak.<时间戳>`
        - 命令：Linux/macOS `printf '\n# rds-supabase-web-build:<项目名>\n<IP> <域名>\n' | sudo tee -a /etc/hosts`；Windows（管理员 PowerShell）`Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value '# rds-supabase-web-build:<项目名>','<IP> <域名>'`
        - 系统文件操作：展示精确变更内容（仅新增/替换行）→ **经用户确认后执行**（或指导用户在管理员终端执行）
     4. **验证与回路**：`curl -I http://<域名>/`（或浏览器打开）返回托管内容 → 步骤八↻ 回调回路以该域名为 site_url/redirect_uris（协议跟随实例 SSL）
     - 明示局限：hosts 映射仅本机生效；OBS endpoint IP 可能变更（变更时**仅更新标记行**）；非正式商用入口；升级路径——转正式模式重走正式链路（下线时清理标记行并解绑自定义域名）
   - **正式上线（线上商用）**：购买域名 → 实名认证 → ICP 备案（中国大陆区域要求，审核时效以官方为准）→ 绑定自有域名 → 按需接入 CDN 加速与 HTTPS 证书（obs-cdn 路线）；费用与周期在确认清单中列示
   - 选择记入 webapp.json `frontend.hosting_mode`（`temporary`/`production`）；两种场景的入口协议均跟随实例 SSL
4. **回调回路（步骤八↻）**：域名确定（按所选场景入口）→ 管理面 `update_supabase_auth_config` 配 site_url/redirect_uris（展示差异后确认）→ 前端按最终地址**重建再发布**。未执行此回路 = auth 登录回调 404
5. frontend checks（entry/assets/routes/negative_paths/cache）
6. 写 webapp.json（hosting_published + `frontend.hosting_mode`）→ gate → 步骤报告

**输出断言**：🔍 托管场景经用户显式勾选确认（temporary/production）｜🔍 frontend checks 全必需项 passed + stable_url 协议跟随实例 SSL（true→HTTPS / false→HTTP，gate 读 frontend record 机器核验一致性）｜🤖 gate PASS

**工具白名单**：允许：管理面 `update_supabase_auth_config`、frontend 技能工具链（KooCLI/OBS/CDN/npm）；禁止：`execute_sql`、实例级管理面写（删除/改密等）

**黄金路径**：
```
声明步骤八 → 构建环境核对 → npm run build → 上传 obs://webapp-123/v1
→ 托管场景勾选：用户选「正式上线」→ 购买域名 demo.example.com + 备案 + CDN（选「临时访问」则绑定已有临时域名，免购免备案）
→ 用户确定域名 https://demo.example.com（本例实例 SSL 开启故入口 https；未开启时入口为 http 且无需证书）→ update_supabase_auth_config(site_url + redirect_uris，差异确认)
→ 前端重建再发布 v2 → frontend checks 全 passed（entry 2xx / assets 2xx / routes / 404 路径 / cache 头）
→ 写 webapp.json(hosting_published) → gate PASS → 步骤报告（步骤八）
```

**失败处置**：发布失败 → frontend 技能恢复流程；验收失败 → 按其检查项处置；回调配置失败 → 重试差异确认（连续失败中止规则）。**断点**：`hosting_published`

## 步骤九 · 端到端上线

**目的**：三层组合验证后正式上线并留档。

**输入**：步骤八的 stable_url 与版本记录；上一断点 `hosting_published`

**动作序列**：

1. 声明步骤九
2. 按 references/launch-checklist.md 执行三层验证：后端项（结构/RLS/advisors/REST 200 + anon 可见性）/ 前端项（checks 契约）/ 连通项（站点渲染、前端→API 数据可见性、**多用户隔离抽检**——两个测试账号经数据面 MCP 用户管理创建后互访对方数据行断言不可见、auth 回调跳转）
3. **测试账号记录**：隔离抽检的两个测试账号创建后即写入 webapp.json `test_accounts`（`email`/`password`/`note`——应用演示账号，非云凭据；凭据红线唯一例外，随名片交付）
4. 输出上线报告（三级交付语义 + stable_url + 版本引用）
5. **输出「应用名片」并落盘 `.hwsupabase/app-card.md`**（字段取自 webapp.json 与 frontend record）：应用名称（`project.name`）、功能介绍（`requirements_summary`）、访问地址（stable_url）、后端地址（`instance.gateway_url`）、测试账号（`test_accounts` 含密码）、数据模型（最新批次 `objects`）、技术栈（`frontend.framework`/`hosting_mode`/实例）、版本信息（`current_batch`/上线时间）、项目管理入口（webapp.json/`record_ref`）+ 使用方式（更新/回滚/下线触发语）；名片落 `.hwsupabase/`（排除 Git）
6. 写 webapp.json（launched + test_accounts）→ gate（`check-stage --stage launched --verify`，后端项机器核验；**app-card.md 存在性一并校验**）→ 完成交付

**输出断言**：🔍 三层全必需项 passed（含多用户隔离抽检不可见）｜🔍 应用名片已输出并落盘（含测试账号与使用方式）｜🤖 gate PASS（launched 终态 + 全链 history）

**工具白名单**：允许：数据面只读与用户管理（测试账号创建）、frontend checks；禁止：**一切写工具**（上线验证除测试账号外纯只读；测试账号在报告后提示用户可清理）

**黄金路径**：
```
声明步骤九 → 后端项（get_rls_status / get_advisors / REST 200 + anon 可见性）→ 前端项（checks 契约复核）
→ 连通项（stable_url 渲染 ✓ / 站点内查询可见性正确 ✓ / 隔离抽检：账号 A↔B 互访均空集 ✓ / auth 回调 ✓）
→ 测试账号记入 test_accounts → 上线报告（本地已验证 / 环境已准备 / 线上验收通过）
→ 应用名片输出 + 落盘 app-card.md → 写 webapp.json(launched) → gate --verify PASS → 交付
```

**失败处置**：后端项失败 → 回步骤五修复重部署；前端项失败 → frontend 修复/回退；连通项失败 → 回调回路/网关/安全组排查——不标记 launched。**断点**：`launched`

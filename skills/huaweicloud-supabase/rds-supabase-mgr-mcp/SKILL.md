---
name: rds-supabase-mgr-mcp
description: RDS Supabase 应用全生命周期管理技能：从零创建一个能访问的应用（创建、公网开通 EIP 与安全组配置、接入信息交付）、使用已有应用、按需增强（存储对接、邮箱登录、GitHub 登录）、日常变更（改密码、重置 Key、SSL、EIP）、查询接入信息、删除收尾。管理面 MCP 29 个工具 + KooCLI 协同。Use when：管理 RDS Supabase 应用的创建、配置、网络开通、认证对接、变更与删除。不用于 SQL 与数据操作（数据面另有机能）。
---

# RDS Supabase 应用全生命周期管理

版本 0.5.0；配套服务端 mcp_server_supabase ≥ 0.4.0a7（uvx 规范入口 mcp-huaweicloud-rds-supabase-mgr）。工具存在不代表服务端已在真实环境联调。

贯穿所有场景的四条铁律：
1. **写操作两段式**：先预览（confirm=false），把参数、影响、费用展示给用户；用户确认后才提交（confirm=true + 预览返回的 plan_id）。预览 10 分钟有效，参数变了重新预览。
2. **"已受理"不是"已完成"**：提交成功只拿到 job_id。要查任务、回查资源，都对了才算完成。
3. **密码和密钥的明文永远不进对话**：所有秘密写进本地请求文件，工具只认别名（见术语表）。预览会自动把秘密显示为"已在本地配置"。
4. **失败就停**：按"出错了怎么办"处置，不绕过护栏、不换参数重试写操作、不用 Shell 替代工具。

---

## 开始之前：把环境和管理工具准备好

不做这一步，后面的工具一个都调不通。

**第一步：拿到五项环境信息**

| 项 | 怎么拿 | 拿不到怎么办 |
|---|---|---|
| AK/SK（访问密钥） | 项目配置或用户输入；带 SecurityToken 的是临时密钥，标记下来（影响存储对接） | 让用户提供 |
| Region（区域） | 用户提供或从项目配置读取 | 让用户从区域列表选 |
| Project_ID | 一次性调用 `diagnostics discover`（CLI），自动解析并给出建议配置 | 让用户从控制台"我的凭证"查 |
| RDS 端点 | 按 Region 推导 `https://rds.<region>.myhuaweicloud.com`，discover 可一并验证 | 用户输入后复测 |
| OBS 端点 | 按 Region 推导 `obs.<region>.myhuaweicloud.com`，DNS + HTTP 探测验证 | 用户输入后复测 |

环境变量名必须是：`HUAWEICLOUD_ACCESS_KEY`、`HUAWEICLOUD_SECRET_KEY`（不是 SECRET_ACCESS_KEY 之类的变体）；临时密钥须设 `SUPABASE_TRANSPORT=sdk_core` 并配 `HUAWEICLOUD_SECURITY_TOKEN`。

**第二步：安装管理面 MCP**
按当前 Agent 的规则注册（opencode 用项目 opencode.json；Claude Code 用项目 .mcp.json；其他宿主见配套安装说明），注入上表五项环境变量。禁止注册到用户级/全局配置。

**第三步：验证装好了没**
调 `get_supabase_capabilities`：能返回说明进程活着；**核对返回里的 mode 字段**和预期传输一致（不一致说明配置错了）。再调 `list_supabase_applications`（limit=1）验证真实可用。

装上但状态异常时，依次检查：环境变量名是否被污染、传输模式是否配错、凭据是否过期——修一样验一次，最多三轮，仍不行就输出缺口报告，不硬试。

**最后：把环境配置清单给用户看**（项/值/来源/核验状态），全部通过才进场景。

---

## 场景一：从零创建一个能访问的应用

**这个场景的完成标准不是"创建成功"，而是"用户能用浏览器打开、能用密钥连上"。**
所以创建只是第一步，公网开通（EIP + 安全组）和接入信息交付都在本场景内，缺一不可。

### 第 1 步：选路线

问用户一个问题：**数据库怎么办？**
- **路线 A：一起新建数据库**（推荐新用户）——干净、自动配好
- **路线 B：用已有的数据库**——适合已有 PG 实例想纳入 Supabase 托管

用 `plan_supabase_creation` 拿到对应路线的准备清单。

### 第 2 步：确定配置项

**两条路线都要定的：**

| 配置 | 怎么定 | 工具 |
|---|---|---|
| 区域 | 用环境里定的，不再问 | — |
| 应用名称 | 用户起名（4-64 字符） | — |
| 应用规格 | 列出候选给用户选，**默认勾选 2U4G 档** | `list_supabase_flavors(az_code, 'Single')` |
| 数据库密码 | **本地随机生成高强度密码，直接写入请求文件，用户不用填，对话里也不出现**；Dashboard 管理员密码与应用密码同值 | 本地命令 |
| 存储 | 问一句"业务要传图片/视频/文件吗？"——要，按场景三第 1 节对接（结论回填创建请求）；不要，跳过 | — |
| 安全组 | 见第 4 步，创建提交前先备好 | — |
| 网络 | **自动选**：查 VPC 和子网，挑一个可用 IP 充足的子网，不烦用户 | KooCLI（见速查表） |

**路线 A 额外要定的（新建数据库）：**

| 配置 | 怎么定 | 说明 |
|---|---|---|
| 可用区 | 查 AZ 列表**自动选第一个可用**（与数据库保持一致，服务端强制） | KooCLI |
| 数据库版本 | 查版本列表，**自动选满足 ≥ 17.11.260900 的最高版** | KooCLI（查的是 PG 引擎版本，不是应用版本） |
| 部署模式 | 问用户用途：**自己玩/学习 → 单机；要商用 → 如实告知主备暂未开放，当前只有单机** | — |
| 计费方式 | **按需计费可用**；用户要包周期（1-9 个月/1-3 年）时如实告知暂未开放 | — |
| 磁盘 | 固定 CLOUDSSD，容量按业务估给用户确认 | — |
| 企业项目/参数模板 | 默认（企业项目填 0，参数模板不传） | — |
| 数据库端口 | **不传端口字段，保持后端默认 5432，禁止修改** | — |

**路线 B 额外要定的（用已有数据库）：**

| 配置 | 怎么定 | 工具 |
|---|---|---|
| 数据库实例 | 列出可托管的 PG（状态正常、无进行中操作）给用户勾选 | `list_supabase_manageable_instances` |
| root 密码 | **引导用户把密码写进本地请求文件**（给出精确格式和位置），然后两次确认：确认已写入 + 预览时确认。密码全程不出现在对话里 | — |

### 第 3 步：提交创建，等它完成

1. 操作员把创建请求（含密码、存储凭据等秘密）写入本地请求文件，确认别名如 `create-app`
2. `create_supabase_application(request_ref, confirm=false)` 预览 → 把脱敏参数给用户看 → 确认 → 提交
3. **等待大约 20-30 分钟**，节奏这样把握：
   - 提交后马上 `wait_supabase_job(job_id)` 看一眼（抓秒级失败）
   - 然后告诉用户"预计 20-30 分钟"，给出任务编号
   - 之后**每次用户回来问，查一次** `show_supabase_job`——不要自己连续刷几十次
   - 路线 A 会返回**两个任务**（应用 + 数据库），要分别确认都完成
4. `show_supabase_application` 回查：状态 normal、无进行中操作、（路线 A）数据库状态正常

### 第 4 步：开通公网访问

**刚创建的应用没有公网地址（public_ip 为空），用户根本访问不了。必须做完这一步。**

**4.1 绑定 EIP**
1. 查现有空闲 EIP 列给用户选（KooCLI，见速查表）
2. 用户想用新的 → 用 KooCLI 创建：区域/线路/带宽/计费/名称**逐项和用户确认后**再执行
3. `change_supabase_eip(application_id, is_bind=true, public_ip_id, public_ip_address)` 预览 → 确认 → 提交 → 等任务 → 回查 `show_supabase_application` 的 public_ip 不再是空

**4.2 配置安全组**
不加规则等于白建——应用登录和数据库连接都靠它：

| 组 | 规则 | 怎么加 |
|---|---|---|
| 应用安全组 | 8443 入方向（不然登录不了应用） | 默认问用户访问来源（IP/网段）；用户明确要全网开放时，提示风险后用 KooCLI 加 0.0.0.0/0 |
| 应用安全组 | 5432 出方向（不然连不上数据库） | MCP 工具暂不支持出方向，用 KooCLI（见速查表） |
| 数据库安全组 | 5432 入方向，来源=所选子网（不然应用连不上库） | `add_supabase_security_group_rule(group_id, source_cidr=子网, port=5432)` |

先 `list_supabase_security_groups` + `show_supabase_security_group` 找满足要求的组；**没有就建**：`create_supabase_security_group(名称)` 建组，再逐条加规则。安全组是共享资源，改动前把影响说清楚，让用户确认。

**4.3 验证真的通了**
用 curl 探测访问地址（任何状态码都算网络可达）。不通就回头查安全组规则和 EIP。

### 第 5 步：交付接入信息

见"场景五：查询接入信息"——创建场景的最后一步就是把它完整跑一遍，给用户一张接入信息卡。

---

## 场景二：使用已经创建好的应用

1. `list_supabase_applications`（知道名字就带 name 参数模糊查，免翻页）
2. 列表给用户勾选——**只有状态 normal 且无进行中操作的行可选**，其他标注"不可选"
3. `show_supabase_application` 核验详情
4. 交付接入信息（场景五）

已有应用没绑 EIP（public_ip 为空）？提示用户走场景一第 4 步开通公网；不需要公网就只给内网地址。

---

## 场景三：按需增强

### 1. 存储对接（要传文件时）

先问用户选哪种：
- **用已有的桶**：列出桶（KooCLI `hcloud obs ls`），**优先私有桶**，公共桶显式提示风险；没有可选的就转新建
- **新建专用桶**：桶名按应用名推导（转小写、非法字符转连字符），重名加短 uuid；**私有**；默认多 AZ（KooCLI `hcloud obs mb -acl=private`）

对接凭据（桶名/AK/SK）写入本地请求文件，走 `update_supabase_storage`：
- **首次启用必须给全**：桶名 + AK + SK
- 已启用且 AK 没变：可以只换桶名、省略 SK
- 换 AK：必须重新给全
- **注意**：环境里是临时密钥（带 SecurityToken）时，存储对接要用持久 AK/SK——提示用户单独提供

### 2. 邮箱登录

对话里只收非秘密项：

| 收集项 | 说明 |
|---|---|
| SMTP 服务器/端口/用户名 | 常见端口 465/587 |
| 发件人邮箱、发件人名称 | |
| 注册即确认，还是发确认邮件？ | 发确认邮件需要配确认模板 |
| 确认邮件主题和链接（可选） | 唯一支持自定义的模板 |

**SMTP 密码（授权码）是秘密**——引导用户写进本地请求文件，对话里不出现。
全部字段写入别名（如 `auth-email`）后：`update_supabase_auth_config` 预览 → 确认 → 提交 → 查任务 → `show_supabase_auth_config` 回查（空串=未配置）。
真实发一封测试邮件才算业务验证。

### 3. GitHub 登录

1. 指导用户先去 GitHub 开发者设置建一个 OAuth App，拿到 **Client ID**（非秘密，对话可收）
2. **Client Secret 是秘密**——写进本地请求文件
3. 回调地址按应用访问地址拼（如 `https://<EIP>:8443/callback`），要和 GitHub App 里填的一致
4. 写入别名（如 `auth-github`）→ `update_supabase_auth_config` 预览 → 确认 → 提交 → 回查
5. 真实走一次 GitHub 登录流程才算业务验证

**关闭某个登录方式时只传关闭开关**（如 `{"enable_github": false}`），不带其他字段——禁用可能连带清空该方式的配置。

---

## 场景四：日常变更速查

| 变更 | 工具 | 关键点 |
|---|---|---|
| 改应用密码 | `change_supabase_application_password` | 新密码写本地请求文件；只改应用密码，不动数据库密码 |
| 重置 API Key | `reset_supabase_api_key` | 重置是异步的：老 Key 逐渐失效、新 Key 是一条新记录；**新值要用场景五重新交付**；提前警告用户下游会断 |
| 开/关 SSL | `change_supabase_ssl` | 开需要证书 ID（没有采购能力，让用户提供）；关必须不带证书。切换会闪断，建议低峰；生效后提醒改回调地址协议 |
| 绑/解绑 EIP | `change_supabase_eip` | 绑定要 ID+IPv4 两样；解绑两样都不带。解绑不释放 EIP、不停计费 |
| 注册/匿名开关 | `update_supabase_auth_flags` | 只改传了的开关 |
| 改 Auth 配置 | `update_supabase_auth_config` | 同场景三；字段省略=不变，没有"传空值清空"这回事 |
| 安全组规则收窄 | `delete_supabase_security_group_rule` | 先核对该组没被别的资源共用 |

每次变更后：查任务 → 回查资源 → （涉及登录的）业务验证。

---

## 场景五：查询接入信息（随时可用，创建场景的最后一步也用它）

对任何一个状态正常的应用，三步给出完整接入信息：

1. `show_supabase_application` → 拿访问地址素材
2. `list_supabase_api_keys` → 四类 Key 的元数据
3. 用户要看 Key 值 → `deliver_supabase_api_key` 逐个交付到本地受保护文件（每类 Key 一个文件，交付前用户逐个确认）

**访问地址这样拼**：协议看 enable_ssl（开=https，关=http）+ 主机看 public_ip（公网，绑了 EIP 才有）或 private_ip（内网）+ 端口看 port。
例：`https://123.60.101.251:8443`

**接入信息卡（输出格式）**：

```
【接入信息】应用名 / ID
访问地址（公网）：https://<EIP>:8443
访问地址（内网）：http://<内网IP>:8443
API Key：四类（secret/publishable/service_role/anon）元数据表
Key 值：已存入本地文件 [文件别名清单]，请在自己电脑上打开取用
后续提醒：Auth 的 site_url/api_external_url 若还是 localhost，按场景三修改
验证状态：资源已核验 / 网络已探测 / 登录功能未验证（如实标注）
```

Key 值**永远不会出现在对话里**——这是红线，用户要也是本地文件交付。

---

## 场景六：删除应用（干净收尾）

**删除前**：
1. `show_supabase_application` 核验状态正常、无进行中操作
2. 把这些信息记下来（删完后核对残留用）：公网 IP、安全组 ID、数据库实例 ID、对接过的桶名
3. 问用户：数据要不要导出？（要 → 先导出再删）

**删除**：`delete_supabase_application` 预览（把"中断服务、不可自动恢复"说清楚）→ 确认 → 提交 → 按用户节奏查任务 → `list_supabase_applications` 确认已消失。

**删除后，给用户一张残留清单**（这些都不会随应用消失）：

| 残留项 | 状态 | 怎么处理 |
|---|---|---|
| 数据库实例 | 保留，**继续计费** | 想彻底删：确认没有其他应用在用，控制台删除 |
| EIP | 保留，**继续计费** | 控制台/KooCLI 释放（停计费的唯一办法） |
| 安全组和规则 | 保留 | 自建的规则可清理；组可能还被数据库引用，删前核对 |
| OBS 桶和数据 | 保留 | 不用了就清理（KooCLI） |
| 本地 Key 文件 | 保留 | 用户自行删除 |
| 项目 MCP 配置 | 保留 | 整个项目都下线时移除 |

---

## 出错了怎么办

| 错误码 | 意思 | 下一步 |
|---|---|---|
| MCP_INVALID_ARGS | 参数不对 | 按提示改参数重新预览 |
| MCP_READ_ONLY | 写开关没开 | 操作员设 SUPABASE_ENABLE_WRITES=true 后重启 MCP |
| MCP_GUARDRAIL_BLOCKED | 护栏拒绝（状态不对/重复提交/目标不符） | 按提示核对，**不绕过** |
| MCP_SDK_ERROR | 网络或响应异常 | 写操作结果不明时：`inspect_supabase_plan(plan_id)` 查本地记录，**禁止重新提交**，人工核对 |
| MCP_NOT_FOUND | 计划不存在 | 检查用的是不是预览返回的 plan_id |

三条总规则：读操作可以改参数重试；写操作结果不明就查记录绝不重放；用户说"清理一下""你看着办"不能当成高风险操作的授权。

---

## 命令与配置参考

**KooCLI 速查**（每次首次使用前先 `--help` 核实参数，这是纪律）：

| 用途 | 命令 |
|---|---|
| 查可用区 | `hcloud RDS ListAvailableZones --cli-region=<region>` |
| 查 PG 数据库版本 | `hcloud RDS ListDatastores --cli-region=<region> --database_name=PostgreSQL` |
| 查 VPC / 子网 | `hcloud VPC ListVpcs` / `hcloud VPC ListSubnets --cli-region=<region>` |
| 查 EIP（找空闲的） | `hcloud EIP ListPublicips --cli-region=<region>` |
| 创建 EIP | `hcloud EIP CreatePublicip --cli-json-file=<配置文件>`（逐项确认后执行） |
| 列 OBS 桶 | `hcloud obs ls` |
| 建 OBS 桶 | `hcloud obs mb obs://<桶名> -location=<region> -acl=private`（多 AZ 加 -multiAZ） |
| 加出方向/全网入方向安全组规则 | `hcloud VPC` 安全组规则命令（direction=egress 或 0.0.0.0/0，先 --help 核实） |

**环境变量**：`HUAWEICLOUD_ACCESS_KEY/SECRET_KEY/SECURITY_TOKEN`、`SUPABASE_TRANSPORT`、`HUAWEICLOUD_PROJECT_ID`、`SUPABASE_RDS_ENDPOINT`、`SUPABASE_REQUESTS_FILE`（请求文件路径）、`SUPABASE_STATE_FILE`（本地记录库路径）、`SUPABASE_ENABLE_WRITES`（写开关）。

**术语表**：
- **plan_id**：预览凭证。预览时生成的编号，提交时带上，10 分钟有效，用过作废
- **request_ref**：请求别名。本地请求文件里一段含秘密的配置的名字，工具只收名字
- **job_id**：任务编号。用它查云端异步任务进度
- **本地执行记录**：每笔写操作在本机留下的结果记录（成功/失败/结果不明），出问题时用它核对，永不删除
- **受理**：服务端收到了请求，不代表做完

**延伸阅读**（按需加载，不必全读）：
- 各场景的详细步骤、失败处置与用户必供字段清单 → [场景手册](references/scenarios.md)
- 本地请求文件的字段级契约（存储/邮箱/GitHub/改密/创建/Key 交付） → [本地请求与字段契约](references/local-requests.md)
- 行为验收用例（单轮 + 多轮异常对话） → [验收手册](references/acceptance.md)

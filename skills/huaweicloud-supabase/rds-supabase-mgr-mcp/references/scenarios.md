# 场景手册（执行详版）

SKILL.md 是主文档；本文件是各场景的详细步骤、字段来源与失败处置。执行复杂场景或排障时加载，不必全读。

## 通用流程（十步）

理解要求 → 定位目标 → 查询必要状态 → 对照能力说明要求覆盖 → 展示方案 → 用户确认 → 执行一次 → 查询任务 → 回查资源 → 分层说明结果（受理/任务/资源/业务，未验证的项如实标注）。

先查工具列表与能力，按实际提供的工具契约调用，不编造工具名。

## 通用异常分支

| 事件 | 必须做 | 不得做 |
|---|---|---|
| 创建含未支持字段 | 说明是否必要、是否独立后置操作；必要条件未满足暂停 | 删除该要求后直接创建 |
| 用户调整范围 | 重做方案并确认，旧计划在可用时取消 | 继续用旧 plan_id |
| 预览后取消 | 调 `cancel_supabase_plan`；工具缺失则停止并说明计划等待过期 | 宣称云端已撤销 |
| 已提交后取消 | 查询记录/任务，解释任务可能继续 | 调另一个写工具模拟取消 |
| 缺工具/未知契约 | 明确能力缺口及可完成部分 | 拼 HTTP 请求、借 Shell 执行 |
| 202 受理 | 报告已受理、保留 job/plan 标识 | 宣布完成 |
| 超时/结果不明 | 查本地执行记录和资源，停止重放 | 换身份/换目录绕过幂等 |
| 多步部分成功 | 列出已完成与剩余项，清理另行确认 | 删除用户原有资源 |
| 获取明文请求 | 仅在可信展示能力可用且获授权时执行 | 把明文注入普通对话 |
| SSL 切换 | 保留中断告警，提醒针对性检查 URL/OAuth/模板和登录 | 自动全量替换 http/https 或修改 SMTP host |
| Key 重置 | 分别核对任务和记录，新 Key 须可靠关联 | 假设最新列表记录就是新 Key |
| 配置保存成功 | 报告保存结果及未做的连接验证 | 宣称 SMTP/GitHub 登录一定可用 |

确认方案由客户端承接，MCP 只验证本地计划绑定。数据面交接只传非敏感目标及用户诉求，不附带管理 AK/SK 或 ApiKey 明文。

## 场景一：从零创建可用应用

### 配置字段来源分类（谁提供什么）

| 来源 | 字段 |
|---|---|
| MCP 工具可查 | 应用规格（`list_supabase_flavors`，需先有 AZ）；路线 B 的数据库实例（`list_supabase_manageable_instances`）；安全组（可新建） |
| KooCLI 可查 | 可用区、PG 引擎版本、数据库规格（RDS ListFlavors）、环境支持的磁盘类型（RDS ListStorageTypes）、VPC/子网（含 IP 余量）、空闲 EIP |
| 必须用户提供 | 应用名称、区域（环境里已有则免）、回调地址类 URL |
| 本地请求文件（秘密） | 应用密码（本地生成）、路线 B 的 database_pwd、路线 A 的数据库密码、存储 AK/SK、OBS 桶名 |
| 外部资源 | EIP（用户已有或 KooCLI 新购） |

### 创建请求体（写入本地请求文件的完整字段）

以**实测通过的后端真实载荷**为基准（路线 A，密码已替换为占位）：

```json
{"name":"rds-supabase-5a55","basic_config":{"region":"cn-east-3","vpc_id":"<VPC ID>","subnet_id":"<子网 ID>","time_zone":"UTC+08:00"},"storage_component":{"enabled":false},"version":"1.0.0","mode":"Single","flavor_ref":"rds.supabase.n1.large.2","availability_zone":"cn-east-3a","password":"<本地生成的密码>","manage_type":"newly_instance","managed_instance":{"datastore":{"type":"PostgreSQL","version":"17.11.260901"},"ha":{"mode":"Single","replication_mode":"async"},"charge_info":{"charge_mode":"postPaid"},"flavor_ref":"rds.pg.n1.medium.2","volume":{"type":"ESSD","size":40},"availability_zone":"cn-east-3a","security_group_id":"<数据库安全组 ID>","password":"<本地生成的密码>","port":5432,"enterprise_project_id":"0","configuration_id":"<可选：参数模板 ID>"},"security_group_id":"<应用安全组 ID>"}
```

**密码规则（应用密码与数据库密码同规则）**：8-32 位，至少包含大写字母、小写字母、数字、特殊字符（`~!@#$%^*-_+=?,`）中的**三种**；本地生成时只从这些字符里取。

**公共必填**：name（4-64）、basic_config{region, vpc_id, subnet_id, 可选 time_zone 如 "UTC+08:00"}、version（**应用版本，固定 "1.0.0"，不是 PG 引擎版本**）、mode=Single、flavor_ref（应用规格，形如 rds.supabase.n1.large.2）、availability_zone、password（按上述密码规则）、storage_component（不用存储时写 `{enabled:false}`，不能整个省略）、manage_type。
**公共可选**：data_vip、security_group_id（应用安全组；可选但漏传事后无法补——没有换组工具，建议自建专用组）。

- **路线 A（newly_instance）**追加 managed_instance：datastore{type=PostgreSQL, version=引擎版本（KooCLI 查，如 17.11.260901）}、**ha{mode:"Single", replication_mode:"async"}（实测载荷带的固定值，照抄）**、charge_info{charge_mode=postPaid}、flavor_ref（数据库规格，形如 rds.pg.n1.medium.2，KooCLI ListFlavors 查，**别照抄应用规格**）、volume{type: 按环境查询结果选择的盘型（ListStorageTypes 查，如 ESSD）, size: 正整数（如 40）}、availability_zone（与应用一致，服务端强制）、security_group_id（数据库安全组，必填）、password（按密码规则，可与应用密码同值——实测载荷即同值）、port（**固定 5432：显式传或省略**）、enterprise_project_id（"0"）。可选 configuration_id（参数模板；默认不传，实测载荷带的模板 ID 是控制台默认模板，跨环境不可复制）。
- **路线 B（existed_instance）**追加 existing_instance：instance_id（工具查）、database_name（数据库用户名，用户提供）、database_pwd（用户写本地文件；存量密码不受创建密码规则约束）。

不支持：主备部署（ha.mode 只接受 Single）、包周期、tags、未知字段——如实告知，不静默丢弃用户要求。

### 预览前逐项核对清单

预览前把请求体按这张表**逐项过一遍**（秘密字段只核"已配置"，不回显值），有出入先改再预览；结论给用户看一眼。实测翻车最多的三处：version 填成 PG 版本、漏 ha、密码不合规。

| # | 字段 | 规则 | 参考值 |
|---|---|---|---|
| 1 | name | 4-64 字符 | rds-supabase-5a55 |
| 2 | basic_config | region/vpc_id/subnet_id 与环境一致；time_zone 可选 | cn-east-3 / … / UTC+08:00 |
| 3 | version | **应用版本，固定值** | "1.0.0"（不是 17.11.x！） |
| 4 | mode | Single | Single |
| 5 | flavor_ref | 应用规格 | rds.supabase.n1.large.2 |
| 6 | availability_zone | 可用区 | cn-east-3a |
| 7 | password | 8-32 位三类字符，本地生成 | （已配置） |
| 8 | storage_component | 不用存储 | {enabled:false} |
| 9 | manage_type | 路线 A | newly_instance |
| 10 | security_group_id（顶层） | 应用安全组 | （自建专用组 ID） |
| 11 | datastore | PostgreSQL + 引擎版本 | 17.11.260901 |
| 12 | ha | 固定值 | {mode:"Single", replication_mode:"async"} |
| 13 | charge_info.charge_mode | postPaid | postPaid |
| 14 | managed flavor_ref | **数据库规格（≠应用规格）** | rds.pg.n1.medium.2 |
| 15 | volume | 环境支持的盘型 + 容量 | ESSD / 40 |
| 16 | managed availability_zone | = 顶层值 | cn-east-3a |
| 17 | managed security_group_id | 数据库安全组 | （组 ID） |
| 18 | managed password | 规则同应用密码，可同值 | （已配置） |
| 19 | port | 5432 或省略 | 5432 |
| 20 | enterprise_project_id | "0" | "0" |

### 提交与等待

提交返回 202 + job_id + application_id（路线 A 另有 instance_id + instance_job_id）。**路线 A 有两个任务，分别确认**。等待节奏：提交后 1 次 `wait_supabase_job`（最多 10 次/共 50 秒，抓秒级失败）→ 告知用户"预计 20-30 分钟"→ 每次用户回来问就 `show_supabase_job` 查一次。观察预算用完（observation_exhausted）≠ 云任务失败。

### 失败处置（创建）

| 失败 | 工具行为 | 处置 |
|---|---|---|
| 请求文件不安全/别名缺失 | MCP_INVALID_ARGS（报错区分"别名不存在"与"注册表不可用"） | 按报错修：补别名，或修权限（0600）/路径；禁止用 Shell 代填秘密 |
| 结构校验不过 | MCP_INVALID_ARGS（**点名具体字段**，如 ha.mode、volume.size、password） | 按点名字段修正；不删用户要求后静默重试 |
| 预览超 10 分钟/参数变 | MCP_GUARDRAIL_BLOCKED | 重新预览确认 |
| 同意图有未完成执行 | MCP_GUARDRAIL_BLOCKED | 查记录核对，不新建计划绕过 |
| 响应含 order_id | MCP_SDK_ERROR，记录置 unknown | 不支付、不重放，人工核对订单 |
| 提交中断 | submission_unknown + plan_id | `inspect_supabase_plan` → 查任务/资源；禁止重放 |
| 后端明确拒绝（4xx） | MCP_INVALID_ARGS / MCP_PERMISSION_DENIED / MCP_NOT_FOUND 等，报错**附后端 error_code/error_msg**；计划标 **failed** | 如实转述后端报错；修正参数后**重新预览再提交**（failed 不阻塞重试，与结果不明不同） |
| 写开关没开 / 只读拦截开着 | MCP_READ_ONLY | 操作员同时核对两个变量：SUPABASE_ENABLE_WRITES=true 且 HUAWEICLOUD_MCP_READ_ONLY=false，改完重启 |
| 任务 failed/状态识别不了 | next_action 指向人工 | 停止当前链路，交操作方 |
| 资源回查状态非 normal | 后续写操作被护栏挡 | 继续按节奏观察，不强行绑 EIP |
| 应用完成但数据库失败（路线 A） | 两个任务独立返回 | 分别核对；部分成功**不自动删资源** |

### 公网开通与安全组

绑定 EIP：`change_supabase_eip`（is_bind=true 须 public_ip_id + IPv4 两样）。安全组规则三条（应用组 8443 入 + 5432 出；数据库组 5432 入自子网），MCP 工具能加入方向规则，出方向和 0.0.0.0/0 走 KooCLI（用户明确确认后）。

绑定后验证：`show_supabase_application` 的 public_ip 非空 → **同步改 Auth 的 `api_external_url`** 为拼装的公网访问地址（`update_supabase_auth_config` 预览→确认→查任务→回查；邮箱确认链接和 OAuth 回调都指向它，不改则登录链路断）→ curl 探测访问地址（任何状态码=网络可达）→ 不通回头查规则和 EIP。

## 场景二：使用已有应用

列表阶段：`list_supabase_applications`（name 模糊查/application_id 精确查/排序）。**查询参数没有 status 过滤**——"可用"要自己筛：status=normal 且 current_actions 为空。同名多条用 application_id 精确复核。详情核验：`show_supabase_application`。public_ip 为空 → 提示走场景一第 4 步，或只给内网地址。

## 场景三：按需增强

字段级契约见 [本地请求与字段契约](local-requests.md)。三个要点：
- **秘密边界**：SMTP 密码、GitHub Client Secret、存储 AK/SK 只进本地请求文件；对话里收非秘密项
- **部分更新**：字段省略=不变；没有"传空值清空"；关闭某个登录方式只传对应 false 开关
- **验证分级**：保存成功（任务+回查）≠ 业务可用（真实发信/登录才算）

## 场景四：日常变更

见 SKILL.md 速查表。变更后统一节奏：查任务 → 回查资源 → 涉登录的业务验证。Key 重置后新值是**新记录**，不用旧 key_id 取值，用场景五重新交付。

## 场景五：接入信息

输入契约：已核验的 application_id（normal、无进行中操作）+ 用户对每个 Key 值查看的明确授权 + `SUPABASE_ENABLE_WRITES=true`（Key 交付虽是云读，但本地写文件需要写开关——容易漏配）。

交付动作：`deliver_supabase_api_key` 每次一个 key 到一个**必须不存在的新文件**（同一别名交付第二次会失败，换新别名新文件）。四类 Key = 四次交付。输出接入信息卡（格式见 SKILL.md），值只落文件。

失败处置：key 非 normal/不唯一 → 护栏拒绝，刷新元数据重选；文件已存在 → 换别名；中途失败 → 操作员检查目标文件，不再拉取、不读内容。

## 场景六：删除

**删除前预检**：核验状态与进行中操作；记录 public_ip、安全组 ID、数据库实例 ID、桶名（残留核对用）；问数据要不要导出；可选先解绑 EIP（`change_supabase_eip` is_bind=false，不带任何绑定参数）。

**删除后确认**：按用户节奏查任务 → `list_supabase_applications` 确认消失 → 数据库回到可托管列表（`list_supabase_manageable_instances` 可复核）→ 输出残留清单（见 SKILL.md 六项表）。

**残留处置通道**：EIP 释放（控制台/KooCLI，停计费唯一路径）；数据库删除（确认无其他应用在用，控制台，注意反向关联）；安全组规则清理（`delete_supabase_security_group_rule`，先核对该组未被共用）；本地 Key 文件与请求文件（用户/操作员自行清理）；项目 MCP 配置（整个项目下线时移除）。

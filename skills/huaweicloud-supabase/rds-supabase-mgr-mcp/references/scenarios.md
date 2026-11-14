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
| 预览后取消 | 预览不提交即作废（10 分钟过期），无需操作 | 宣称云端已撤销 |
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

### 意图四问（进入配置前必须问完，不许默认、不许替用户决定）

| 问题 | 答案的后果 |
|---|---|
| 数据库怎么办？新建还是用已有 PG？ | 路线 A（newly_instance）/ 路线 B（existed_instance） |
| **要传文件吗？**（图片、视频、附件都算） | 要 → **创建前**定 OBS 桶（复用私有桶 or 新建专用多 AZ 桶，也问用户），桶名+AK/SK 进 storage_component——**存储事后无法补开**；不要 → storage_component 写 {enabled:false} |
| 要从公网访问吗？ | 要 → 创建后走 EIP + 安全组 + api_external_url 同步；不要 → 明确告知用户只能内网访问 |
| 要 https 吗？ | 要 → 买 CCM 证书、创建后切 SSL；不要 → 走 http |

**执行纪律**：逐个问、拿到明确答复才往下走；答全后喂给 `plan_supabase_creation(manage_type, needs_storage, needs_public_access, needs_ssl, ...)`。用户一笔带过需求时（"帮我建个应用"），四问一个都不能少——没问就默认等于替用户做了业务决定，走偏的根源就在这。部署模式是否支持 Ha 也别猜：`list_supabase_flavors_with_azs(az_code, mode='Ha')` 成功 → Single/Ha 都可选；400 → 该环境仅 Single，如实告知。

### 配置字段来源分类（谁提供什么）

| 来源 | 字段 |
|---|---|
| MCP 工具可查 | 应用规格与各规格支持的 AZ 列表（`list_supabase_flavors_with_azs`，需先有 AZ；返回的 AZ 信息兼作可用区选择依据）；路线 B 的数据库实例（`list_supabase_manageable_instances`）；安全组（可新建） |
| 可查（优先 MCP 工具） | **应用基础要素一次调 `discover_supabase_create_basic_options(az_code)`（版本/Single-Ha 探测/可售规格）**；PG 引擎版本、数据库规格、磁盘类型、安全组（均有专用工具，内部走 KooCLI）；**新建实例场景可一次调 `discover_db_instance_create_options(mode)` 并发查全部依赖，返回逐字段推荐配置** |
| KooCLI 可查（工具未覆盖，兜底） | 可用区（用 `list_supabase_flavors_with_azs` 的 AZ 信息或 ECS NovaListAvailabilityZones）、空闲 EIP |
| 网络自动发现 | **`discover_available_network_for_create`**（一步锁定 IP 充足的 VPC+子网：优先 2 个空闲 IP、兜底 1 个；返回 vpc_id/subnet_id/subnet_cidr 直接填 basic_config；区域无可用网络时不报错，返回默认推荐 default_vpc 192.168.0.0/16 + default_subnet 192.168.0.0/24（建在实例所在 AZ、网关 192.168.0.1）——按 default_create 建好后再跑一次发现取真实 ID） |
| 必须用户提供 | 应用名称、区域（环境里已有则免）、回调地址类 URL |
| 本地请求文件（秘密） | 应用密码（本地生成）、路线 B 的 database_pwd、路线 A 的数据库密码、存储 AK/SK、OBS 桶名 |
| 外部资源 | EIP（用户已有或 KooCLI 新购） |

### 创建请求体（写入本地请求文件的完整字段）

下面是一个真实可用的创建请求（同时新建 PG 的路线 A；选主备或包周期时，把 mode/ha/charge_info 换成对应值）：

```json
{"name":"rds-supabase-5a55","basic_config":{"region":"cn-east-3","vpc_id":"<VPC ID>","subnet_id":"<子网 ID>","time_zone":"UTC+08:00"},"storage_component":{"enabled":false},"version":"1.0.0","mode":"Single","flavor_ref":"rds.supabase.n1.large.2","availability_zone":"cn-east-3a","password":"<本地生成的密码>","manage_type":"newly_instance","managed_instance":{"datastore":{"type":"PostgreSQL","version":"17.11.260901"},"ha":{"mode":"Single","replication_mode":"async"},"charge_info":{"charge_mode":"postPaid"},"flavor_ref":"rds.pg.n1.medium.2","volume":{"type":"ESSD","size":40},"availability_zone":"cn-east-3a","security_group_id":"<数据库安全组 ID>","password":"<本地生成的密码>","port":5432,"enterprise_project_id":"0","configuration_id":"<可选：参数模板 ID>"},"security_group_id":"<应用安全组 ID>"}
```

**密码规则（应用密码与数据库密码同规则）**：8-32 位，至少包含大写字母、小写字母、数字、特殊字符（`~!@#$%^*-_+=?,`）中的**三种**；本地生成时只从这些字符里取。

**公共必填**：name（4-64）、basic_config{region, vpc_id, subnet_id, 可选 time_zone 如 "UTC+08:00"}、version（**应用版本 x.y.z，取当前最高，不是 PG 引擎版本**）、mode（Single 或 Ha，和用户确认）、flavor_ref（应用规格，形如 rds.supabase.n1.large.2）、availability_zone（Single 一个 AZ；Ha 两个不同 AZ，此处为主 AZ）、password（按上述密码规则；默认用户 supabase 的密码）、storage_component（不用存储时写 `{enabled:false}`，不能整个省略）、manage_type。
**公共可选**：data_vip、security_group_id（应用安全组；**必须新建专用组**，ID 进创建请求，漏传事后无法补——没有换组工具）。

- **路线 A（newly_instance）**追加 managed_instance：datastore{type=PostgreSQL, version=引擎版本（`list_db_instance_engine_versions` 查大版本）}、ha{mode 与顶层 mode 一致：Single 或 Ha；replication_mode: async 或 sync}、charge_info（按需 {charge_mode:"postPaid"}；包周期 {charge_mode:"prePaid", period_type: "month"（月）或 "year"（年）——**字符串，不是 2/3 数字**，官方契约如此，传数字会被本地拒绝, period_num: 1-9 个月或 1-3 年, 可选 is_auto_renew/is_auto_pay 布尔}）、flavor_ref（数据库规格，形如 rds.pg.n1.medium.2，`list_db_instance_flavors_with_azs` 查，和应用规格是两回事，别混用）、volume{type: 按环境查询结果选择的盘型（`list_db_instance_storage_types` 查，如 ESSD）, size: 40-40000（GB）}、availability_zone（与顶层主 AZ 一致，服务端强制）、security_group_id（数据库安全组，必填，**新建专用组**）、password（按密码规则，可以和应用密码用同一个值）、port（固定 5432：显式传或省略）、enterprise_project_id（**默认 default 项目**，ID 为 "0"；多企业项目时让用户选）。可选 configuration_id（参数模板，默认不传）。
- **路线 B（existed_instance）**追加 existing_instance：instance_id（工具查）、database_name（**固定 root，不能改**）、database_pwd（用户写本地文件；存量密码不受创建密码规则约束）。

不支持：tags、未知字段——如实告知，不静默丢弃用户要求。主备/包周期是否可用以所选环境实际为准：后端拒绝时报错会带 error_code/error_msg，如实转述即可。

### 预览前逐项核对清单

预览前把请求体按这张表**逐项过一遍**（秘密字段只核"已配置"，不回显值），有出入先改再预览；结论给用户看一眼。最常见的三类错误：version 填成 PG 版本、漏 ha、密码不合规。

| # | 字段 | 规则 | 参考值 |
|---|---|---|---|
| 1 | name | 4-64 字符 | rds-supabase-5a55 |
| 2 | basic_config | region/vpc_id/subnet_id 与环境一致；time_zone 可选 | cn-east-3 / … / UTC+08:00 |
| 3 | version | **应用版本，取当前最高** | "1.0.0"（不是 17.11.x！） |
| 4 | mode | Single | Single |
| 5 | flavor_ref | 应用规格 | rds.supabase.n1.large.2 |
| 6 | availability_zone | Single 一个 AZ；Ha 两个不同 AZ（此处填主 AZ） | cn-east-3a |
| 7 | password | 8-32 位三类字符，本地生成 | （已配置） |
| 8 | storage_component | 不用存储 | {enabled:false} |
| 9 | manage_type | 路线 A | newly_instance |
| 10 | security_group_id（顶层） | 应用安全组 | （自建专用组 ID） |
| 11 | datastore | PostgreSQL + 引擎版本 | 17.11.260901 |
| 12 | ha | mode 与顶层 mode 一致（Single/Ha） | {mode:"Single", replication_mode:"async"} |
| 13 | charge_info | 按需 {charge_mode:"postPaid"}；包周期带 period_type（字符串 "month"/"year"）/period_num | postPaid |
| 14 | managed flavor_ref | **数据库规格（≠应用规格）** | rds.pg.n1.medium.2 |
| 15 | volume | 环境支持的盘型 + 容量 | ESSD / 40 |
| 16 | managed availability_zone | = 顶层值 | cn-east-3a |
| 17 | managed security_group_id | 数据库安全组 | （组 ID） |
| 18 | managed password | 规则同应用密码，可同值 | （已配置） |
| 19 | port | 5432 或省略 | 5432 |
| 20 | enterprise_project_id | 默认 default 项目 | "0" |

### 提交与等待

提交返回 202 + job_id + application_id（路线 A 另有 instance_id + instance_job_id——应用在实例创建成功后才触发创建，实例就绪前查不到应用任务）。**路线 A 有两个任务，分别确认**。等待节奏：**综合进展用 `show_supabase_creation_progress`**（路线 A 传全部四个 ID，自动按"先实例后应用"编排，返回实例创建中/应用等待/应用创建中/完成/失败五态）→ 提交后先查 1 次抓秒级失败 → 告知用户"预计 20-30 分钟"→ 每次用户回来问就再查 1 次；需要单任务细节（entity/时间戳）时才用 `show_operation_job_status`。观察预算用完（observation_exhausted）≠ 云任务失败。

### 失败处置（创建）

| 失败 | 工具行为 | 处置 |
|---|---|---|
| 请求文件不安全/别名缺失 | MCP_INVALID_ARGS（报错区分"别名不存在"与"注册表不可用"） | 按报错修：补别名，或修权限（0600）/路径；禁止用 Shell 代填秘密 |
| 结构校验不过 | MCP_INVALID_ARGS（**点名具体字段**，如 ha.mode、volume.size、password） | 按点名字段修正；不删用户要求后静默重试 |
| 预览超 10 分钟/参数变 | MCP_GUARDRAIL_BLOCKED | 重新预览确认 |
| 同意图有未完成执行 | MCP_GUARDRAIL_BLOCKED | 查记录核对，不新建计划绕过 |
| 响应含 order_id（包周期） | status=order_created，计划记 accepted | 走订单工具闭环：`get_supabase_order` 查状态/金额/币种并给用户核对 → 用户核准后 `pay_supabase_order`（预览→确认+plan_id；余额支付，有折扣订单走控制台）→ 支付后才开始创建，按正常节奏查任务；放弃则 `cancel_supabase_order`（未支付才能取消）；金额/状态变化须重新核准 |
| 提交中断 | submission_unknown + plan_id | `show_operation_job_status` 查任务、回查资源；禁止重放 |
| 后端明确拒绝（4xx） | MCP_INVALID_ARGS / MCP_PERMISSION_DENIED / MCP_NOT_FOUND 等，报错**附后端 error_code/error_msg**；计划标 **failed** | 如实转述后端报错；修正参数后**重新预览再提交**（failed 不阻塞重试，与结果不明不同） |
| 写开关没开 / 只读拦截开着 | MCP_READ_ONLY | 操作员同时核对两个变量：SUPABASE_ENABLE_WRITES=true 且 HUAWEICLOUD_MCP_READ_ONLY=false，改完重启 |
| 任务 failed/状态识别不了 | next_action 指向人工 | 停止当前链路，交操作方 |
| 资源回查状态非 normal | 后续写操作被护栏挡 | 继续按节奏观察，不强行绑 EIP |
| 应用完成但数据库失败（路线 A） | 两个任务独立返回 | 分别核对；部分成功**不自动删资源** |

### 公网开通与安全组

安全组在创建前就准备好：**应用组必须新建专用组**（别复用已有组），`create_supabase_security_group` 创建时**必须带 description 标记用途**——应用组填 `Supabase应用（自动创建）`，数据库组填 `数据库接入（自动创建）`（控制台一眼可辨、审计清理有据）。服务端自动打 `AUTO_CREATE=true` 与 `USE_FOR=Supabase` 双标签，整组删除只放行带双标签的组。建好后立刻配上规则——入方向 8443（用户来源网段）、出方向 5432（`direction='egress'`）；数据库组（路线 A）同样新建专用组，入方向 5432 放行所选子网。出入方向规则都走 MCP 工具（`add_supabase_security_group_rule` 的 `direction` 参数）；只有 0.0.0.0/0 全网入方向仍须用户明确确认后走 KooCLI（MCP 工具按设计不放行全网规则）。

绑定 EIP：`change_supabase_eip`（is_bind=true 须 public_ip_id + IPv4 两样）。**新建 EIP（KooCLI）时必须加标签 `USAGE_FOR: Supabase应用公网访问，自动创建的`**，与其他 EIP 区分开。

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

**删除前预检**：核验状态与进行中操作；记录 public_ip、安全组 ID、数据库实例 ID、桶名（残留核对用）；问数据要不要导出；可选先解绑 EIP（`change_supabase_eip` is_bind=false，不带任何绑定参数）。**必问**：要不要连托管 PG 实例一起删（`delete_managed_instance` 选 true/false，不能默认）——选是则应用与实例两笔删除同时提交，返回两个任务编号分别跟踪。

**删除后确认**：按用户节奏查任务 → `list_supabase_applications` 确认消失 → 数据库回到可托管列表（`list_supabase_manageable_instances` 可复核）→ 输出残留清单（见 SKILL.md 六项表）。

**残留处置通道**：EIP 释放（控制台/KooCLI，停计费唯一路径）；数据库删除——`delete_supabase_managed_instance`（须传入应用 ID + 其 `managed_instance.id` 双标识，服务端实测校验托管绑定、并确认无其他应用引用同一实例；数据不可恢复，先确认导出；包周期实例走控制台退订）；安全组规则清理（`delete_supabase_security_group_rule`，先核对该组未被共用）；安全组整组下线（`delete_supabase_security_group`，删前核对组未被实例/NIC 引用——后端会拒绝在用组，删组连带删除组内全部规则）；本地 Key 文件与请求文件（用户/操作员自行清理）；项目 MCP 配置（整个项目下线时移除）。

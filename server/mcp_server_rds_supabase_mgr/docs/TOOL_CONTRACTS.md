# MCP 工具契约

契约版本 v0.4；运行包版本见 ../README.md。本文件区分已提供工具和目标能力；目标能力不意味着可调用。内部 REST 路径和抓包保留在本地证据库，不在这里复刻。

## 通用输入输出

输入以 tools/list 公布的 schema 为准。所有工具拒绝未知顶层字段；不得将未知字段值回显到错误。凭据不作工具参数。application_id/key_id/job_id 均使用查询所得真实标识，不靠名称猜测。
写工具默认 confirm=false，返回 status=confirmation_required、application_id、action、changes、resource_path、plan_id、expires_at、execution=not_executed，以及适用的 warnings/follow_up。该预览目前不代表已做在线可执行性验证。
执行须同参数 confirm=true + plan_id，服务端写开关开启且未只读；服务端检查身份/参数摘要与当前目标状态。HTTP 202 返回 status=accepted、job_id、complete=false；不代表完成。
错误沿用共享核心 error.code/message/hint 等字段；调用方同时检查结构化 error，不能仅检查 MCP is_error。未知参数错误不附带原始参数值。

## 本轮提供的工具

| 工具 | 输入（?可选） | 输出/语义 | 风险 |
|---|---|---|---|
| get_supabase_capabilities | 无 | 列出可用能力范围（模式/策略/已实现操作/六场景契约）；离线声明，不探测云状态 | READ |
| plan_supabase_creation | manage_type?=newly_instance/existed_instance；needs_storage?/needs_public_access?/needs_ssl?/needs_email_login?/needs_github_login?（三态意图：省略=决策点/true=规划分支/false=规划排除） | 阶段化规划（decision_points/pre_creation/creation/post_creation/external_dependencies/security_notes/missing）；planning_only，无提交 | READ |
| plan_supabase_ssl | enable_ssl?=true | 证书选择步骤/缺口；无提交 | READ |
| list_supabase_applications | limit?=10, offset?=0, name?, application_id?, sort_key?=created_time, sort_dir?=desc | 分页应用列表；type 固定 supabase 不可指定；返回 total_count + 必备字段（名称/ID/公网IP/端口/规格/模式/创建时间/备注）+ 其余非秘密字段，脱敏限长 | READ |
| show_supabase_application | application_id | 应用详情（状态/SSL/IP/规格/节点/存储/托管实例）；direct_eip 归一 public_ip、时间戳 RFC 3339、嵌套递归透传；访问地址拼接：协议←enable_ssl、主机←public_ip（公网）/private_ip·traffic_vip（内网）、端口←port；状态非完成证明 | READ |
| list_supabase_api_keys | application_id, limit?=10, offset?=0, status?, key_type?, key_id?, sort_key?=created_time, sort_dir?=desc | Key 列表——service_role/anon/publishable/secret 四类 ID 记录，无 value 值；白名单 id/name/status/type 必备、created_time/updated_time/remark 可空；时间戳 RFC 3339；未知字段丢弃不透传；name/时间过滤尚未开放 | READ |
| show_supabase_auth_config | application_id | Auth 认证配置：注册开关/访问控制/URL、身份认证提供商（邮箱+SMTP、GitHub）、六类邮箱模板；9 个顶层字段必备缺一拒绝（布尔/字符串/对象类型锚定）；秘密（SMTP 凭据、OAuth client secret）任意深度剔除，标识符（oauth_client_id/smtp_user）保留；空串=未配置；是 update 预览与 reconcile 的对照基准 | READ |
| show_supabase_job | job_id | 原始状态证据、completion_verified=false；不推断终态 | READ |
| change_supabase_ssl | application_id, enable_ssl, cert_id?, confirm?, plan_id? | 开启需证书ID；关闭null；不自动改URL | WRITE |
| change_supabase_eip | application_id, is_bind, public_ip_id?, public_ip_address?, confirm?, plan_id? | 绑定需要ID和IPv4；解绑不得携带非空绑定参数 | WRITE |
| delete_supabase_application | application_id, confirm?, plan_id? | 仅删应用保留PG；无请求体 | DANGEROUS |
| reset_supabase_api_key | application_id, key_id, confirm?, plan_id? | 重置，无明文；提交前按应用和ID查询唯一normal记录，新记录关联仍待补齐 | DANGEROUS |
| update_supabase_auth_flags | application_id, enable_account_sign_up?, enable_anonymous_users?, confirm?, plan_id? | 至少一个明确布尔值；省略/null不修改 | WRITE |
| inspect_supabase_plan | plan_id | 本地 state/job_id/expires_at，completion_verified=false | READ |
| cancel_supabase_plan | plan_id | 仅 prepared→cancelled；重复取消幂等；不取消云任务 | WRITE（本地账本） |

本地取消不受 SUPABASE_ENABLE_WRITES 云写开关约束，但仍服从共享核心只读/保护规则。被只读策略阻断时停止操作并等待计划失效；禁止删除账本绕过。未知计划返回 MCP_NOT_FOUND；已提交计划拒绝取消。

## 目标工具族（未冻结签名，不得按下表虚构调用）

| 场景 | 待提供的业务能力 | 冻结签名前置 |
|---|---|---|
| 创建 | 发现候选、要求覆盖、推荐、预览、提交、结果查询 | 创建字段依赖/响应/资源归属 |
| 删除 | 关联影响查询、级联方案及执行 | 完整影响范围、保护和部分失败契约 |
| 访问 | 证书发现/适用性、受控改密、费用引导 | 原生CCM契约、安全输入；采购范围决策 |
| 安全组 | 列表详情、建组、规则变更方案和执行 | 原生鉴权/响应/共享影响证据 |
| ApiKey | 过滤查询、受控查看值、重置后定位 | 明文通道、新旧记录关联字段 |
| 业务配置 | 配置查询、非敏感差异、受控局部更新 | 字段清空/保留规则及秘密引用 |

## 目标结果模型与兼容

最终结果需独立表达 submission、task、resource_verification、business_verification 四个维度。该模型是设计要求，当前返回仍以现有字段为准；未迁移前 Skill 不得假定字段已经存在。任务终态只能映射有契约依据的值；未验证使用 unknown/not_checked。
未来适配层以业务动作、非敏感结果和分类错误为边界，REST 与 SDK 不直接暴露各自模型到 Skill。字段删除/语义变更需要新契约版本和兼容矩阵；新增可选字段先验证旧 Skill。

0.3.2a1：ApiKey输出白名单为id/name/status/type/created_time/updated_time；响应包裹data/total_count不符则拒绝。重置前检查不替代后端授权/状态校验。

0.4.0a3：应用列表新增 name/application_id 过滤与 sort_key/sort_dir 排序（缺省 created_time desc）；type 固定 supabase 不可指定。响应信封 applications+total_count 不符即拒绝；记录必备 id/name/public_ip/port/flavor_ref/mode/created_time/remark（flavor/description/gateway_port 等别名归一），缺一拒绝；其余非秘密字段限长透传。

0.4.0a4：按真实返回体修正——信封键为 data+total_count（与 ApiKey 同族，applications 键拒绝）；公网 IP 实际字段 direct_eip，归一为 public_ip；remark 后端可缺省，降为可空字段（updated_time 同）；created_time/updated_time 毫秒时间戳归一为 RFC 3339 UTC（毫秒精度）；嵌套对象/数组（az_details、managed_instance、current_actions 等）递归脱敏透传（秘密键名剔除、数组 100、字符串 2000、深度 8）。必备字段缺一仍拒绝。

0.4.0a5：show_supabase_application 按真实详情载荷对齐——必备 id/name/mode/status/port/enable_ssl/private_ip/created_time 缺一拒绝；direct_eip 归一 public_ip（未绑 EIP 为 null）；traffic_vip/manage_ip/updated_time/remark 可空；嵌套 spec_flavor/data_volume/nodes/dnat/az_details/managed_instance/storage_component 递归脱敏透传（nodes 内时间戳同样归一）；返回不再回显 limit/offset，note 写明访问地址拼接规则（协议←enable_ssl，主机←public_ip 或内网 IP，端口←port）。投影器与列表共享（别名仅在实际提升时跳过透传）。

0.4.0a6：show_supabase_auth_config 按真实载荷对齐——描述明确为"注册配置/访问控制/身份认证提供商（邮箱与 GitHub）/邮箱模板"；9 个顶层字段（enable_account_sign_up、enable_anonymous_users、api_external_url、site_url、allow_redirect_urls、github_oauth_provider、email_oauth_provider、email_template_config）必备缺一拒绝，布尔/字符串/对象类型锚定；嵌套（smtp_config、六类 mailer 模板）递归脱敏透传；秘密（SMTP 凭据、OAuth client secret）任意深度剔除、标识符保留；空串=未配置；返回不回显 limit/offset，note 声明其为 update 预览与 reconcile 的对照基准。

0.4.0a7：list_supabase_api_keys 按真实载荷对齐——描述明确为"service_role/anon/publishable/secret 四类 Key 的 ID 记录列表，永不返回 value 值"；白名单扩展 remark（后端实际返回的备注字段）；id/name/status/type 升为必备缺一拒绝；created_time/updated_time/remark 可空；毫秒时间戳归一 RFC 3339 UTC；未知字段仍丢弃不透传（Key 场景保持白名单语义，区别于应用场景的透传语义）。

## 0.3.7a1增量
任务单次判定、有界只读观察及补充资料冲突处置见[采纳与验收说明](SUPPLEMENT_REVIEW.md)。任务completed不等于资源/业务验收，账本不自动解除。创建信息已补充，秘密通道及剩余约束仍待完成。

0.3.7a1更新：Auth accepted计划可按[对账契约](RECONCILIATION.md)验证并结束；unknown及其他动作不解除。业务验收、资源并发控制和完整秘密通道仍待完成。

## 0.3.8a1 新增工具

总计29个工具；新增12个。`change_supabase_application_password`、`update_supabase_auth_config`、`update_supabase_storage`只接受application_id/request_ref/confirm/plan_id，schema和安全边界见[本地引用](LOCAL_REQUESTS.md)。应用改密为DANGEROUS，Auth/Storage为WRITE；沿用应用状态检查、两阶段确认、异步202/job和本地防重复账本。

VPC工具：list_supabase_security_groups(limit=10,marker=null)、show_supabase_security_group(group_id)、create_supabase_security_group(name,confirm=false,plan_id=null)、add_supabase_security_group_rule(group_id,source_cidr,port=8443,confirm=false,plan_id=null)、delete_supabase_security_group_rule(group_id,rule_id,confirm=false,plan_id=null)。查为READ、建组WRITE、规则增删DANGEROUS。与RDS共享原生入口；原生v3单对象；创建201/删除204，无RDS job。回查与业务成功另验，ledger保留accepted。

新增create_supabase_application(request_ref,confirm=false,plan_id=null)与deliver_supabase_api_key(application_id,key_id,delivery_ref,confirm=false,plan_id=null)，均为DANGEROUS，安全输入/输出和结构见LOCAL_REQUESTS.md。

创建候选：list_supabase_flavors(az_code,mode)和list_supabase_manageable_instances()为READ；返回creation_ready=false，不能当创建提交/费用报价或完整分页库存。

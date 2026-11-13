# 本地请求与字段契约

工具参数只传 `application_id`、`request_ref`、`confirm`、`plan_id`。凭据由操作方在模型会话之外写入本地 JSON 文件，设绝对路径 `SUPABASE_REQUESTS_FILE` 后启动 MCP。文件不进代码仓、交付包、云盘或聊天。Windows 须由操作员配置仅运行账户可读的 NTFS ACL（程序不自动核验）；Unix 强制当前用户所有且 0600，拒绝符号链接、重复 JSON 键、超 64KiB 文件。

文件格式：`{ "别名": { "字段": "值" } }`。别名 1-64 位字母/数字/下划线/连字符。工具每次重新读取同一别名——**预览后改文件会使计划失效，须重新预览**。预览自动隐藏秘密字段（显示"已在本地配置"）并擦除 URL 查询串。不要把秘密放进非秘密字段。

## 字段契约

### 改应用密码（change_supabase_application_password）

| 字段 | 规则 | 秘密 |
|---|---|---|
| application_password | 唯一允许的字段；非空、≤2048、无控制字符 | 是 |

只改应用密码，不接受 instance_password（数据库密码另管）。后端密码策略仍权威；改完由用户实际登录验证。

### Auth 配置（update_supabase_auth_config）

顶层八选一或多选，**全部可选但值不得为空**；省略=不变，没有"传空值清空"：

| 字段 | 规则 | 秘密 |
|---|---|---|
| enable_account_sign_up / enable_anonymous_users | 布尔 | 否 |
| site_url / api_external_url | 合法 URL（http/https，不允许内嵌账号密码/片段） | 否 |
| allow_redirect_urls | 逗号分隔，最多 10 个 URL | 否 |
| github_oauth_provider | 见下 | 部分 |
| email_oauth_provider | 见下 | 部分 |
| email_template_config | 见下 | 否 |

**api_external_url 跟着公网地址走**：EIP 绑定成功后必须同步更新为拼装的公网访问地址（场景一 4.1 的强制步骤）；解绑后旧值失效，与用户确认改回内网地址还是等重新绑定。

**github_oauth_provider**：enable_github（布尔）、oauth_client_id、oauth_client_secret（**秘密**）、redirect_uri（URL，与 GitHub App 内配置一致）。**关闭时只传 `{"enable_github": false}`**，带其他字段会被拒绝。

**email_oauth_provider**：enable_email_sign_up、enable_email_auto_confirm（布尔）、smtp_config 对象（非空）。smtp_config 子字段：smtp_host、smtp_port（整数 1-65535）、smtp_user、smtp_pwd（**秘密**，QQ/163 等为授权码）、smtp_admin_email、smtp_sender_name、smtp_max_frequency（非负整数）。**关闭时只传 `{"enable_email_sign_up": false}`**。

**email_template_config**：当前仅支持 `mailer_confirmation`（含 subject 和/或 url，至少一项）。查询侧能看到六种模板，但**只有确认邮件模板可改**——引导时不要承诺改其他五种。

### 存储对接（update_supabase_storage）

| 字段 | 规则 | 秘密 |
|---|---|---|
| enabled | 必填，布尔 | 否 |
| type | 固定 `obs` | 否 |
| bucket_name | 启用时必填；`[a-zA-Z0-9.\-]{3,64}` | 否 |
| ak | 启用时必填；`[a-zA-Z0-9_-]{1,32}` | **是** |
| sk | 启用时**唯一可省**的字段（条件见下） | **是** |

**省略 SK 的条件**（服务端提交前实时核验）：存储已启用 **且** AK 与当前一致。首次启用或换 AK 必须给全。禁用时（enabled=false）三个字段必须全空。

### 创建（create_supabase_application）

公共必填与两分支字段见 [场景手册](scenarios.md)（含实测参考载荷与**预览前逐项核对清单**）。秘密字段：顶层 password（应用密码）、managed_instance.password（路线 A 数据库密码）、existing_instance.database_pwd（路线 B）、storage_component 的 ak/sk。**密码规则**（应用密码与数据库密码同规则）：8-32 位，至少含大写/小写/数字/特殊字符（`~!@#$%^*-_+=?,`）三类。**创建路径没有"省略 SK"——启用存储必须全凭据**。managed_instance.volume.type 按环境查询结果选择（KooCLI ListStorageTypes），服务端不限定具体盘型，云端策略权威。version 固定 "1.0.0"（应用版本）；ha 固定 `{"mode":"Single","replication_mode":"async"}`；port 传 5432 或省略。

### Key 交付（deliver_supabase_api_key）

引用对象：`{ "output_file": "操作方选择的新文件绝对路径" }`。文件必须**当前不存在**（独占创建 0600）；父目录属当前用户且无组/其他权限。每类 Key 一个别名一个文件。工具不返回文件路径或密钥值，只返回 delivery_ref。需要 `SUPABASE_ENABLE_WRITES=true`。

## 拒绝清单（防错点汇总）

未知字段、任何空值、空嵌套对象、关闭开关携带其他字段、非确认模板键、allow_redirect_urls 超 10 项、URL 内嵌凭据、端口/频率越界、控制字符——全部拒绝，按提示修正后重新预览。上述为已确认结构的受限子集，后端完整策略仍权威；未支持的用户要求必须显式说明，不能静默移除后提交。

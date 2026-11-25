# 连接交付场景

> 何时读：应用/客户端要连接实例时（拿连接串、SSL 证书）。

## 连接信息

`show_pg_connection_info(instance_id)` → 内网 IP/端口/HA 模式聚合视图。

psql 示例（hint 已内置）：
```bash
psql --no-readline -h <private_ip> -p 5432 dbname=postgres user=root
```

已开通内网域名时，`dns_name` 字段非空，可直接用域名替代内网 IP 作 host。

## 内网域名（DNS 域名替代 IP 连接）

链路：**申请 →（可选）自定义名 → 查询复核**：

1. `show_pg_dns_name(instance_id)` → 查当前域名（未开通时 dns_name 为空——属正常结构）
2. `create_pg_dns_name(instance_id, dns_type="private", 两段式)` → 开通内网域名（需实例 ACTIVE）；开通后 `show_pg_connection_info` 的 `dns_name` 出现
3. `update_pg_dns_name(instance_id, dns_name, 两段式)` → 改为自定义域名；**名称规则**：小写字母/数字/连字符（首尾不得为连字符）
4. 再 `show_pg_dns_name` 复核新名

**纪律（MUST）**：
- **修改域名后旧域名立即失效**——所有仍用旧域名的连接串会断，提交前必须转述此 warning 并通知应用方
- 域名仅同 VPC 内网解析有效，不改变公网访问路径
- 自定义名先做唯一性/格式自检，避免云端拒绝后重试浪费两段式 plan

## SSL 加密连接

1. `download_pg_ssl_cert(instance_id)` → 临时下载链接（有效期短，立刻下载）
2. 解压得 ca.pem / ca-bundle.pem
3. `psql "sslmode=verify-ca sslrootcert=/path/ca.pem ..."`

## 端口变更

`change_pg_instance_port(instance_id, port, 两段式)`：
- **4-10 分钟重启窗口**，所有客户端需改用新端口
- 按需实例的变配会走维护窗口执行

## 安全组（全量替换语义！）

`change_pg_security_group(instance_id, security_group_id, 两段式)`：
- 提交的组**替换**当前组（不是追加）——须确认目标组放行了 5432（或自定义端口）
- 换组前建议先在 VPC 侧确认新组规则

## pg_hba（客户端认证规则）

- 查：`list_pg_hba_conf(instance_id)`
- 改：`change_pg_hba_conf(instance_id, entries=[{type, database, user, address, mask?, method, priority?}], 两段式)`
- **风险**：规则错误可锁死所有客户端；变更后保留一个已连接会话再验证
- 每条 entry 必填 type/database/user/address/method；priority 0-10000 越小越先匹配

# 连接交付场景

> 何时读：应用/客户端要连接实例时（拿连接串、SSL 证书）。

## 连接信息

`show_pg_connection_info(instance_id)` → 内网 IP/端口/HA 模式聚合视图。

psql 示例（hint 已内置）：
```bash
psql --no-readline -h <private_ip> -p 5432 dbname=postgres user=root
```

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

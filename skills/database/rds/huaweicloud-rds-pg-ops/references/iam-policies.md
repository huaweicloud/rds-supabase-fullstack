# IAM 权限策略（iam-policies.md）

> 何时读：MCP 服务器返回 403 / DBS.280015 权限错误时；或为运行本技能的 IAM 用户/委托规划最小授权时。

## 1. 概述

本技能的全部 74 工具经 `mcp-huaweicloud-rds-pg` MCP 服务器调用华为云 OpenAPI（SDK 直连，非 KooCLI）。涉及两个云服务：

- **RDS**（rds:）：实例生命周期、备份、库/账号/参数/插件、日志
- **CES**（ces:）：监控指标查询与告警规则创建

Action 名称均来自 SDK 请求类（`_http_info` 级核实），未按命名规律虚构；个别工具在文档中给出官方 IAM 权限对应项的通用写法，请以控制台「权限及授权项说明」最终核对。

## 2. 按工具分组的权限需求

| 工具分组 | 工具（示例） | RDS Action | 权限名（IAM 细粒度） |
|---|---|---|---|
| 实例查询（READ） | list_pg_instances / show_pg_instance / show_pg_instance_job | rds:instances:list / rds:instances:get / rds:jobs:list | RDS ReadOnlyAccess 覆盖 |
| 选型目录（READ） | list_pg_flavors / list_pg_datastores / list_pg_storage_types / show_pg_quotas | rds:flavors:get / rds:datastores:list / rds:storagetype:get / rds:quotas:get | RDS ReadOnlyAccess 覆盖 |
| 创建实例（DANGEROUS） | plan_pg_instance_creation（只读聚合）/ create_pg_instance | rds:instances:create | rds:instance:create |
| 生命周期（WRITE） | reboot / stop / start_pg_instance | rds:instances:reboot / rds:instances:stop / rds:instances:start | rds:instance:reboot 等 |
| 重置管理员密码（DANGEROUS） | reset_pg_admin_password | rds:instances:modifyPwd | rds:instance:resetPassword |
| 连接管理（READ+WRITE） | show_pg_connection_info / download_pg_ssl_cert / change_pg_instance_port / change_pg_security_group / list_pg_hba_conf / change_pg_hba_conf / show_pg_dns_name / create_pg_dns_name / update_pg_dns_name | rds:instances:get / rds:sslCert:get / rds:instances:modifyPort / rds:instances:modifySecurityGroup / rds:instances:hba:get / rds:instances:hba:modify / rds:instances:dnsName:get / rds:instances:dnsName:create / rds:instances:dnsName:modify | rds:instance:update（含安全组端口/域名） |
| 备份（READ+WRITE） | show/list_pg_backup*、list_pg_restore_times / set_pg_backup_policy、create_pg_manual_backup | rds:backups:get / rds:backups:list / rds:restores:list / rds:backupPolicy:get、rds:backupPolicy:modify、rds:backups:create | rds:backup:manage |
| 库与账号（READ+WRITE） | list_pg_databases/schemas/db_users / create_pg_database、create_pg_schema、create_pg_db_user、set_pg_db_user_password（DANGEROUS）、update_pg_db_user_comment、grant_pg_db_privilege | rds:instances:database:get、rds:instances:database:list / rds:instances:database:create、rds:instances:schema:create、rds:instances:dbUser:create、rds:instances:dbUser:modify、rds:instances:dbUser:grant | rds:database:manage / rds:user:manage |
| 变配（DANGEROUS/WRITE） | resize_pg_flavor / extend_pg_volume / reduce_pg_volume / set_pg_auto_enlarge_policy / switch_pg_single_to_ha / change_pg_ops_window | rds:instances:resize / rds:instances:volume:extend / rds:instances:volume:reduce / rds:instances:autoEnlargePolicy:modify / rds:instances:single2Ha / rds:instances:opsWindow:modify | rds:instance:update |
| 监控告警（CES） | list_pg_resource_metrics、show_pg_metric_data / create_pg_alarm_rule | ces:metrics:get、ces:metrics:list / ces:alarms:create | CES ReadOnlyAccess / CES alarm:put |
| 日志（READ+WRITE） | list/download_pg_slow_log、list/download_pg_error_log、list_pg_audit_logs / set_pg_audit_log_policy | rds:instances:slowLogs:get、rds:instances:errorLogs:get、rds:instances:auditLogs:get / rds:instances:auditLogPolicy:modify | rds:log:manage |
| 参数（READ+WRITE） | show_pg_parameters、list/compare_pg_configurations / update_pg_parameter、apply_pg_configuration | rds:configurations:get、rds:configurations:list、rds:configurations:compare / rds:instances:configuration:modify、rds:configurations:apply | rds:param:manage |
| 插件（READ+WRITE） | list_pg_extensions / install、uninstall_pg_extension | rds:extensions:get / rds:extensions:create、rds:extensions:delete | rds:extension:manage |

## 3. 最小权限策略 JSON 样例

只读起步（推荐首次接入）：

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:instances:list", "rds:instances:get", "rds:jobs:list",
        "rds:flavors:get", "rds:datastores:list", "rds:storagetype:get", "rds:quotas:get",
        "ces:metrics:get", "ces:metrics:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

全量运维（含写操作，建议限定资源）：

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:instances:*", "rds:backups:*", "rds:backupPolicy:*",
        "rds:configurations:*", "rds:extensions:*",
        "ces:metrics:get", "ces:metrics:list", "ces:alarms:create"
      ],
      "Resource": ["*"]
    }
  ]
}
```

生产收紧：把 `Resource` 从 `"*"` 收敛为具体实例 ARN 列表，删除 `rds:instances:delete`（本技能不含删除类工具，但 `instances:*` 通配会带入——如需极简可按第 2 节表格逐 Action 枚举）。

## 4. 权限失败处理流程（MUST）

1. 工具返回 403 / `DBS.280015`（权限不足）信封
2. 读取本文件，定位该工具所属分组的 Action
3. 向用户展示所需权限列表与上方策略 JSON
4. 指导用户在 IAM 控制台创建自定义策略并授权（系统策略可用：`RDS ReadOnlyAccess` / `RDS Administrator`、`CES ReadOnlyAccess`）
5. **暂停执行，等待用户确认权限已授予后**再重试原操作

## 5. ✅/❌ 正误对比

- ✅ `Action: ["rds:instances:get", "rds:instances:list"]` —— 最小只读，来自 SDK 请求类
- ❌ `Action: ["rds:*:*"]` 或 `"Action": "rds"` —— 过宽通配，不满足最小权限要求
- ❌ 凭命令名猜测 Action（如按工具名拼 `rds:reboot:get`）——必须以上表 / 官方《权限及授权项说明》为准

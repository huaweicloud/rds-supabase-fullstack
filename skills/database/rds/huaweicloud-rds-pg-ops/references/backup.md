# 备份管理场景

> 何时读：配置备份策略、创建手动备份、查看备份列表/下载。

> 范围外提醒：恢复到新实例 / PITR / 库表级恢复、删除备份已按用户决策移除，本技能不提供这些流程。

## 备份策略

- 查：`show_pg_backup_policy(instance_id)`
- 改：`set_pg_backup_policy(instance_id, keep_days, start_time, period, 两段式)`

| 参数 | 规则 |
|---|---|
| `keep_days` | **≥7**（工具强制校验，更小直接拒绝） |
| `start_time` | "21:00-22:00" 格式（**不带时区后缀**，实测带 GMT 报 DBS.280216） |
| `period` | "1,2,3,4,5,6,7"（周几备份） |

延长保留期会增大备份存储费用（预览 warning 已含）。

## 手动备份

`create_pg_manual_backup(instance_id, name, 两段式)` → 备份任务异步执行（BUILDING → COMPLETED）。
关键变更前（变配/升级/大批量 DDL）建议先手动备份。

## 备份清单与下载

- `list_pg_backups(instance_id, backup_type="auto"|"manual"|"all")` → id/name/type/size/status/begin_time
- `show_pg_backup_download_link(backup_id)` → 临时 URL（尽快下载）

## 可恢复时间窗

`list_pg_restore_times(instance_id)` → 查询该实例的可恢复时间范围（信息性——恢复操作本身范围外）。

## 备份期间的操作互斥

实例处于备份任务中（或后台自动备份周期）时，其他写操作会收到 DBS.201015/200019——等待后重试，不要取消备份。

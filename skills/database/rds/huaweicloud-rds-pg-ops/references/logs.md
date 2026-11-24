# 日志排查场景

> 何时读：应用变慢查慢 SQL、数据库报错查错误日志、合规审计。

## 慢 SQL 排查

1. `list_pg_slow_logs(instance_id, start_date, end_date, limit)` 
   - 日期格式：ISO（工具自动归一化为 RDS 要求的 +0800 格式，直接传 UTC 的 "2026-11-23T08:00:00Z" 即可）
   - 返回执行超阈值的语句明细（时间/语句/耗时/行数）
2. 定位最重语句后：优化索引/改写 SQL（SQL 质量规则不在本技能）
3. 取全量文件：`download_pg_slow_log(instance_id)` → 临时下载链接

慢日志阈值由参数 `log_min_duration_statement` 控制（见 parameters.md）。

## 错误日志

`list_pg_error_logs(instance_id, start_date, end_date, limit)` → 报错事件清单。
下载：`download_pg_error_log(instance_id)`。

## SQL 审计（合规）

- 开启：`set_pg_audit_log_policy(instance_id, keep_days, 两段式)`
  - **按量计费**（预览 warning 必现，向用户明确成本）
  - keep_days 为保留天数
- 查询：`list_pg_audit_logs(instance_id, limit)`

## 排查节奏

同时间段 error + slow 交叉看：错误往往伴随慢查询（锁等待、超时）。
CPU 异常时先 monitoring.md 查指标再回来看慢日志。

# 监控与告警场景

> 何时读：查实例健康指标、配置告警规则。

## 指标元数据

`list_pg_resource_metrics()` → RDS PostgreSQL 支持的指标清单（名称/单位/维度）。
常用指标：

| 指标名 | 含义 |
|---|---|
| rds001_cpu_util | CPU 使用率 % |
| rds002_mem_util | 内存使用率 % |
| rds061_disk_util / rds080_disk_util | 磁盘使用率 |
| rds077_conn_usage / rds073_conns | 连接数 |

## 查指标数据

`show_pg_metric_data(instance_id, metric_name, period=300, time_range=3600)`
- period：采样粒度秒（300 = 5 分钟）
- time_range：回看秒数（3600 = 最近 1 小时）
- 返回 datapoints 时序

## 建告警规则

`create_pg_alarm_rule(instance_id, name, metric_name, comparison_operator=">=", value=85, confirm)`
- 典型：CPU ≥ 85% 持续 5 分钟告警
- 阈值与通知渠道是用户决策项（通知需 CES 侧通知主题配合）

## 健康巡检模板（每日简报）

```
1. list_pg_instances → 清单 + 异常状态计数
2. 逐实例 show_pg_metric_data(rds001_cpu_util) → 当前水位
3. current_actions 非空的实例 → 标记「变更中，勿下发操作」
4. 输出：实例数/异常数/高负载实例/锁定实例
```

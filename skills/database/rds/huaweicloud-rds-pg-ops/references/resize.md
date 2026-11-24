# 变配与容量演进场景

> 何时读：升配/降配、扩容磁盘、单机转主备、维护窗口调整。

## 规格变更

`resize_pg_flavor(instance_id, spec_code, 两段式)`
- **会重启**（warning 必现）；建议业务低峰
- spec_code 从 `list_pg_flavors(version)` 取
- 降配可能因数据量不足而失败

## 磁盘扩容/缩容

- `extend_pg_volume(instance_id, size, 两段式)`：扩容不中断；**计费按新容量**（只升不降的账单）
- `reduce_pg_volume`：引擎 **17+** 才支持；16 实例直接拒绝

## 自动扩容策略

`set_pg_auto_enlarge_policy(instance_id, switch_option, limit_size?, trigger_threshold?, 两段式)`
- trigger_threshold：剩余空间百分比触发阈值（如 10 表示剩 10% 触发）
- limit_size：扩容上限（GB），防止费用失控

## 单机转主备

`switch_pg_single_to_ha(instance_id, az_code_new_node, 两段式)`
- 备机部署到指定 AZ
- **计费约 2 倍**（warning 必现）；转换期间实例重启

## 维护窗口

`change_pg_ops_window(instance_id, start_time, end_time, 两段式)`
- 格式 "02:00"/"06:00"（**最大 4 小时**，不支持跨午夜如 22:00→03:00，实测报参数错误）
- 窗口内变更操作自动安排执行；会有 1-2 次连接闪断

## 只读实例（读写分离）

`list_pg_read_replicas(primary_id)` 查看挂载的副本。
新建副本走创建编排（plan_pg_instance_creation 的 replica 路径）。

## 变更期间互斥

变更与备份/重启/升级互斥（DBS.201015）；连续变配之间必须等前一 job 终态。

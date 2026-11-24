# 参数调优场景

> 何时读：连接数吃紧、内存配置、日志级别等数据库参数调整。

## 查参数

`show_pg_parameters(instance_id, name?)`
- 不带 name：全量 325 个参数（含 value / restart_required / readonly / value_range / description）
- 带 name：精确单个（如 max_connections）

## 改参数

`update_pg_parameter(instance_id, name, value, 两段式)`

**restart_required 判定纪律**：
1. 先 `show_pg_parameters(name=...)` 看该参数的 restart_required
2. `true` 的参数改后需重启才生效——预览时必须向用户说明「生效需要重启窗口」
3. value_range 之外的值云端会拒绝；readonly 参数不可改

常见调优项：

| 参数 | 场景 | 注意 |
|---|---|---|
| max_connections | 连接数不足 | 受内存约束（勿超总内存 20% 估算） |
| log_min_duration_statement | 慢日志阈值（毫秒） | 动态生效 |
| work_mem | 排序/哈希内存 | 动态，总量 = 并发×值 |

## 参数模板

- `list_pg_configurations()` → PostgreSQL 模板清单（引擎过滤）
- `compare_pg_configurations(source_id, target_id)` → 两模板参数差异
- `apply_pg_configuration(config_id, instance_ids, 两段式)` → 应用到实例（模板参数覆盖实例参数）

**权限提示**：参数写操作需要 AK/SK 具备 RDS 参数管理权限；403 DBS.280015 即权限不足（IAM 侧补策略，不是工具问题）。

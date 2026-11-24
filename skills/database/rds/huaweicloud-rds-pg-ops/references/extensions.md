# 插件管理场景

> 何时读：启用 pgvector（向量检索）、pg_stat_statements（SQL 统计）等 PG 插件。

## 查看插件

`list_pg_extensions(instance_id, database_name)` → 插件清单（名称/版本/是否需要 shared_preload_libraries）

## 安装

`install_pg_extension(instance_id, database_name, extension_name, 两段式)`

**注意**：
- **依赖 schema 已建**且插件可用
- 标记 `shared_preload_libraries` 的插件（如 pg_stat_statements）安装后需**重启实例**才完全生效——预览 warning 已提示
- 安装到指定 database（不是实例级）

## 常用插件速查

| 插件 | 用途 | 重启要求 |
|---|---|---|
| pgvector | 向量检索（AI 场景） | 否 |
| pg_stat_statements | SQL 执行统计（Top SQL） | shared_preload，需重启 |
| pg_repack | 在线膨胀治理 | 否 |
| pg_cron | 定时任务 | shared_preload，需重启 |
| zhparser | 中文全文检索 | 否 |

## 卸载

`uninstall_pg_extension(instance_id, database_name, extension_name, 两段式)`
- 依赖该插件的对象（索引/表列类型）必须先删除，否则云端拒绝
- 卸载前提示用户确认数据依赖

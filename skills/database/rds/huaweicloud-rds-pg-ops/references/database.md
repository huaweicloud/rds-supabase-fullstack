# 库与账号开通场景

> 何时读：新应用上线需要建库、建 schema、建专用账号、授权。

## 标准链路（每步两段式 + 等待生效）

```
create_pg_database → (等~20s) → create_pg_schema → (等~20s)
  → write_pg_secret_request → create_pg_db_user → (等~20s) → grant_pg_db_privilege
```

**串行纪律**：RDS 一个实例同时只执行一个管理操作；连续步骤间隔不足会 409。工具层已做重试等待提示，Skill 层遵守「上一步提交成功→等待→下一步」。

## 建库

`create_pg_database(instance_id, name, owner?, character_set?, 两段式)`
- name 重复会被云端拒绝（错误信封含 request_id）
- owner 缺省 root；字符集缺省实例默认（UTF8）

## 建 schema

`create_pg_schema(instance_id, db_name, schema_name, owner?, 两段式)`

## 建账号（密码纪律）

1. `write_pg_secret_request(password)` → request_ref（0600 本地文件）
2. `create_pg_db_user(instance_id, name, password_ref, comment?, 两段式)`
- 预览信封中密码只显示 request_ref 引用；审计日志已脱敏
- 密码规则：8-32 位，含大小写+数字+特殊字符（`~!@#$%^&*()-_=+|[]{};:,<.>/?）之一

改密：`set_pg_db_user_password(instance_id, name, password_ref, 两段式)`
备注（L1 轻写，无 plan_id）：`update_pg_db_user_comment(instance_id, name, comment, confirm)`

## 授权（最小权限）

`grant_pg_db_privilege(instance_id, db_name, users=[{name, readonly, schema_name?}], 两段式)`
- `readonly: true` = 只读；`false` = 读写
- **目标 schema 必须已存在于该库**，否则 DBS.200001 参数错误（实测）
- 推荐模式：应用账号按库只读 + 管理账号读写分离

## 验证

- `list_pg_databases / list_pg_schemas(db_name) / list_pg_db_users` 复核全部生效

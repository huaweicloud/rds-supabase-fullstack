# 创建实例场景

> 何时读：用户要新建 RDS for PostgreSQL 实例时。

## 流程（plan → 确认 → 创建 → 轮询）

1. **`plan_pg_instance_creation(needs_public_access=?, flavor_hint=?)`**（只读编排）：
   返回三段式方案：
   - `baseline`：实时推荐的引擎版本/flavor/磁盘/HA
   - `decision_checklist`：分三档——**user-only**（计费模式、EIP 计费——用户必须本人选）/ **user-confirm**（flavor、磁盘、HA——Agent 可推荐、用户点头）/ agent-default（端口、AZ）
   - `apply_steps`：编号执行流
2. **收集用户决策**：把 decision_checklist 呈现给用户，收齐 user-only/user-confirm 两档的选择才能进下一步。**用户没回答 user-only 项就停**。
3. **`write_pg_secret_request(password)`**：管理员密码落本地 0600 文件，拿 `request_ref`。
4. **`create_pg_instance(..., confirm=false)`**：预览（含计费 warnings）。
5. 用户确认后同参 `confirm=true` + plan_id 提交 → job_id。
6. **`show_pg_instance_job` 轮询**（5-25 分钟）→ Completed 后 `show_pg_instance` 复核 ACTIVE。

## 关键参数契约（实测）

| 参数 | 规则 |
|---|---|
| `availability_zone` | **Ha 模式必须双 AZ**："cn-north-4a,cn-north-4g"；Single 单 AZ。从 flavor 的 az_status 取 normal 状态的 AZ |
| `ha_mode` | "Ha"（主备，~2 倍计费）或 "Single" |
| `charge_mode` | postPaid（按需）或 prePaid（需 period 月数，user-only 决策） |
| `region` | 必填，如 "cn-north-4" |
| `flavor_ref` | 从 `list_pg_flavors(version)` 取 spec_code |
| `volume_type` | 从 `list_pg_storage_types` 取（CLOUDSSD 通用默认） |
| `admin_password_ref` | request_ref 路径（不是明文） |

## 护栏与重试

- 同意图未决时重复提交被 PlanStore 拒绝（防双开）——先查实例是否已建
- 创建提交超时返回 unknown：**查 job 与实例列表，禁止重新提交**（可能已在创建）
- 配额不足：先 `show_pg_quotas`（quota=50/used=3 之类），避免撞到 CreateInstance 才报错

# 网络环境与 EIP 场景（network.md）

> 何时读：用户要为 RDS for PostgreSQL 准备网络环境（VPC/子网/安全组/企业项目）、给实例开公网访问（EIP 绑定/解绑），或在创建实例前做网络选型时。

## 1. 发现 → 决策 → 创建 链路（核心流程）

```
discover_pg_network（一次拿全：EPS + VPC + 子网 + SG + placement 推荐 + SG 规格计划）
  → 呈现决策点（复用 default 资产 or 新建；SG reuse-or-new）
  → 需要新建时逐个两段式创建（create_pg_vpc → create_pg_subnet → create_pg_security_group）
  → 把 vpc_id / subnet_id / security_group_id 填进 create_pg_instance
```

纪律（写死，非自觉）：
1. **发现先行**：任何创建类网络操作前必须先 `discover_pg_network`（或对应 list 工具）实查，禁止凭记忆或用户口述的 id 直接创建子网/规则（子网 CIDR 归属校验依赖实查的 VPC CIDR）。
2. **所有创建类工具两段式**：confirm=false 预览 → 展示 changes+warnings → 用户同意 → confirm=true+plan_id。plan_id 失效重新预览，不凭记忆重发。
3. **SG 5432 来源永不缺省放行全网**：`open_5432=true` 必须给 `open_5432_from`（'open' / 设备出口 IP / 有界 CIDR）或 `subnet_id`（取该子网网段）。工具对缺失来源直接拒绝——不要绕过。
4. **EIP 计费是 user-only 决策**：`create_pg_eip` 的 billing_type（traffic 按流量 / bandwidth 按带宽 Mbps）必须用户本人选，Agent 禁代选。
5. **EIP 未绑定也计费**：创建即开始计费直至释放。测试/临时用途结束要提醒用户释放（MCP 无删除工具，删除不在本技能范围）。释放方式：控制台 EIP 页删除，或 CLI：`hcloud EIP DeletePublicip/v3 --publicip_id=<id> --cli-region=<region>`；Python SDK：`EipClient.delete_publicip(DeletePublicipRequest(publicip_id=<id>))`。
6. 单个 step 单独推进；创建子网前先建好 VPC；绑定 EIP 前实例必须 ACTIVE 无 current_actions。

## 2. 工具契约（实测）

| 工具 | 关键契约 |
|---|---|
| discover_pg_network | 聚合返回；EPS 不可用时降级为 null+提示（个人账号正常现象，其余网络事实照常返回）；placement 推荐优先 default VPC/subnet |
| list_pg_subnets(vpc_id) | vpc_id 必填；先 list_pg_vpcs 拿准确 id |
| list_pg_security_groups | 每组带 open_5432 标记（实查 ingress TCP 5432 规则）；reuse 优先选带标记的组 |
| create_pg_vpc | cidr 必须 RFC1918 私网段（默认 192.168.0.0/16）；空 VPC 免费但占配额 |
| create_pg_subnet | **服务端校验子网 CIDR 必须落在 VPC CIDR 内**；AZ 必须与实例一致（错 AZ 只在创建实例时才暴露） |
| create_pg_security_group | 三选一源见 §1.3；open_5432=false 建空组；规则创建失败时组已建（返回 rule_warning，可手动补规则，不构成未知写结果） |
| create_pg_enterprise_project | 需管理员权限、组织级资源；EPS 未启用账号会失败（先 list 确认） |
| create_pg_eip | billing_type 必填（user-only）；自动打 USAGE_FOR=rds-pg 标签（失败降级 warning）；按需计费 |
| bind_pg_instance_eip | 传 public_ip_id 即可（地址自动实查补全）；实例须 ACTIVE 无锁；**单 IP 语义：实例已绑有 EIP 时必须先解绑（工具会在提交前检查并明确报错指引）**；warning 含公网暴露+流量费 |
| unbind_pg_instance_eip | 解绑不释放不停止计费（warning 必转述）；实例必须当前有 public_ips |

## 3. 安全组 5432 源三选一（决策表）

| 用户说法 | 参数 | 风险 |
|---|---|---|
| 「全放行/能连就行」 | open_5432_from='open'（0.0.0.0/0） | **高危**：必须用户显式说出才可用；Agent 主动建议 bounded 源替代 |
| 「只有我这台机器连」 | open_5432_from='<用户出口IP>'（自动 /32） | 推荐；出口 IP 可让用户提供或从其连接环境判断后**向用户确认** |
| 「公司内网段连」 | open_5432_from='10.0.0.0/24'（有界 CIDR） | 推荐；缺省（不给 from 只给 subnet_id）取所属子网网段，同为有界源 |

## 4. EIP 全流程（创建 → 绑定 → 验证 → 解绑）

1. `create_pg_eip(billing_type=<用户选>, name=...)` 两段式 → 拿 publicip id/address。
2. 等实例 ACTIVE 无 current_actions（`show_pg_instance`）。
3. `bind_pg_instance_eip(instance_id, public_ip_id)` 两段式 → 提交后回查 `show_pg_instance` 的 public_ips 出现该地址。
4. 提醒：绑定后 SG 必须只放行预期来源（若绑定前未配好，先 `change_pg_security_group` 或补规则）。
5. 不再需要公网：`unbind_pg_instance_eip(instance_id)` 两段式 → 验证 public_ips 清空 → **提醒用户释放 EIP**（控制台/CLI，删除不在本技能）。

## 5. 与 plan_pg_instance_creation 的衔接

plan 的 baseline.network 已含发现结果与 placement 推荐；decision_checklist 的 network/security_group/eip 三档决策按本页 §1-§4 纪律收集用户选择后，进入 create_pg_instance 主流程（见 references/creation.md）。

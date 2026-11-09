---
name: rds-supabase-web-build
description: 'RDS Supabase 全栈开发编排技能：AI Agent 通过自然语言创建并托管 Web 应用网站的端到端工作流——前端代码生成、后端 init.sql（DDL/GRANT/RLS/RPC）生成与部署、前端静态资源 OBS+CDN 全托管、端到端上线与生命周期管理（更新/回滚/下线）。Use when：创建 Web 网站、搭建 AI 应用、全栈应用从零到上线、已有 RDS Supabase 应用的迭代更新与托管维护。编排管理面 MCP（实例生命周期）与数据面 MCP（动态安装）及 rds-supabase-mgr-mcp / rds-supabase-mcp / rds-supabase-usage / rds-supabase-frontend / rds-supabase-postgres-best-practices 五个专项技能。v1 后端边界为数据层；复杂业务逻辑（支付/第三方调用/长任务）不在 v1 范围，SSR 后端部署不支持。'
license: MIT
metadata:
  version: "0.1.0"
---

# RDS Supabase 全栈开发编排（web-build）

## 概述

RDS Supabase 全栈开发的**总指挥技能**：用户以一句话（"建一个网站"/"搭一个 AI 应用"）触发，AI Agent 走完前端与后端的代码生成、部署运行、托管上线的完整链路。本技能是厚工作流编排者——拥有阶段状态机、通过门槛、失败处置与断点续作；各环节深度内容由专项技能承载，本技能只路由、不复制。

双工作流总图：

```
【首次创建流水线】（每阶段有通过门槛；门槛不过不前进）
 ⓪ 需求澄清 → ① 资源准备 → ② 数据面接入 → ③ 后端生成部署 → ④ 前端生成 → ⑤ 构建与托管 → ⑥ 端到端上线
                ↳ 管理面 MCP（实例/EIP/安全组/SSL/密钥）+ OBS 租户桶
                ↳ install.md 动态安装数据面 MCP
 ⑤↻ 回调回路：域名确定 → 管理面配置 site_url/redirect_uris → 前端重建

【生命周期循环】（独立工作流）
 更新（增量 init.sql → 重走③⑥）｜回滚（前端版本回退 + DB 批次管理）｜下线（清理清单）｜密钥轮换
```

双平面与双轨：

- **管理面**：`mcp_server_rds_supabase_mgr`（29 工具）——RDS Supabase 实例全托管生命周期（创建/配置/安全访问/删除）
- **数据面**：`mcp_server_rds_supabase`（38 工具）——init.sql 执行、结构查询、RLS/advisors
- **后端轨**：产出 init.sql（DDL/GRANT/RLS/RPC/种子），运行于 RDS Supabase（PostgREST/GoTrue）
- **前端轨**：产出静态站点（默认 React+Vite+TS + supabase-js），托管于 OBS+CDN

## 适用范围

**触发条件**（满足任一即启用）：

1. 创建 Web 网站 / 搭建 AI 应用（从零到上线的全栈需求）
2. 全栈应用需要完整走"前端 + 后端 + 托管 + 上线"链路
3. 已有 RDS Supabase 应用的迭代更新、回滚、下线

**边界**（编排者不做细节，路由到位）：

| 任务 | 归属 |
|---|---|
| 实例创建/配置（EIP/安全组/SSL）/密钥交付/删除 | rds-supabase-mgr-mcp 技能 + 管理面 MCP |
| 数据面 MCP 动态安装 | rds-supabase-mcp 技能 references/install.md |
| init.sql 质量规则（③ 强制门） | rds-supabase-postgres-best-practices 技能 |
| 前端 supabase-js SDK 用法（④ 强制门；③ 消费视角） | rds-supabase-usage 技能 |
| 前端构建/OBS 发布/CDN/版本回退 | rds-supabase-frontend 技能 |
| init.sql 五步部署/单工具数据操作 | rds-supabase-mcp 技能 |
| SSR 后端部署 | 不支持（静态导出为边界，继承 frontend 技能策略） |
| 复杂业务逻辑（支付/第三方调用/长任务） | v1 边界外（FunctionGraph 路由留待 v2） |

## 前置条件

1. uv（含 uvx）已安装；MCP 客户端（Claude Code 等）可用
2. ① 起点：devkit 已在用户登录时初始化管理面 MCP 与凭据；或可经 uvx 动态拉起管理面 MCP（凭据由用户提供或经受保护文件交付）
3. 云侧付费资源（实例/OBS 桶/CDN）创建前须用户显式确认（费用预估在 ⓪ 输出）

## 工作流

**阶段状态机**（断点续作依据，记录于 `.hwsupabase/webapp.json` 的 `last_completed_stage`）：

```
requirements_confirmed → instance_ready → mcp_connected → backend_deployed
                      → frontend_built → hosting_published → launched
```

| 阶段 | 动作（路由） | 通过门槛 |
|---|---|---|
| ⓪ 需求澄清 | 网站/页面/数据模型/认证澄清；AI 能力识别（pgvector 检索/Realtime/文件上传为可选扩展）；费用预估清单 | 用户确认需求摘要 + 数据模型草案 |
| ① 资源准备 | a. 管理面就绪（devkit 检测→uvx 动态拉起）；b. 实例创建/选定+配置（EIP/安全组 8443/SSL）；c. 凭据获取（网关 URL + Anon/Service Role Key 两种都要）；d. OBS 租户桶创建（frontend 技能引导） | 实例 running 且实际可访问；凭据就绪（只记 env 名）；桶就绪 |
| ② 数据面接入 | rds-supabase-mcp 技能 install.md 动态安装；凭据注入 devkit 优先、半自动兜底（agent 写配置骨架 + 用户从受保护文件填值） | `get_project_url` 与网关一致 + `list_tables` 应答 |
| ③ 后端生成部署 | **强制门**：生成 init.sql 前必读 best-practices（逐条对照）+ usage 客户端消费视角；数据面 MCP 五步部署 | 结构确认 + advisors 无新增安全项 + REST 200 |
| ④ 前端生成 | **强制门**：生成前必读 usage（SDK 正确用法，避免运行时报错）；默认 React+Vite+TS | 本地构建成功 + 本地功能验证 |
| ⑤ 构建与托管 | frontend 技能：build → 上传①预建桶 → CDN；↻ 域名确定后回调配置（管理面 `update_supabase_auth_config`）→ 前端重建 | frontend checks 通过 + stable_url |
| ⑥ 端到端上线 | launch-checklist 三层验证（后端/前端/连通） | 全必需项 passed → 标记 launched + 上线报告 |

每阶段的完整 playbook（输入/动作/门槛/失败处置/断点）见 references/workflow-stages.md。

**断点续作**：会话开始先读 webapp.json → 从 `last_completed_stage` 的下一阶段重入，并**重验该阶段门槛**（不信任历史结论）。

**生命周期循环**（更新/回滚/下线/密钥轮换）：见 references/lifecycle.md。

## 可用工具

| 平面 | MCP | 关键能力 |
|---|---|---|
| 管理面 | mcp_server_rds_supabase_mgr（29 工具） | 实例创建/配置（EIP/安全组/SSL）、ApiKey 交付、`update_supabase_auth_config`（回调配置）、删除；两阶段确认 + 执行账本 |
| 数据面 | mcp_server_rds_supabase（38 工具） | `execute_sql`（单一事务，五步部署执行者）、结构查询、RLS/advisors、用户管理；只读拦截/审计脱敏 |

完整路由矩阵见 references/routing-table.md。

## 参数确认

| 项 | 确认规则 |
|---|---|
| ⓪ 需求摘要与数据模型 | 用户逐项确认后才进入①；模糊表述不放大授权 |
| 付费资源创建（实例/桶/CDN） | 费用预估清单展示 + 用户显式确认（管理面两阶段确认兜底） |
| init.sql（③ 产出） | best-practices 四项审查通过；破坏性语句逐条人工确认 |
| 凭据 | agent 永不接触明文；只处理 env 名与注入状态；连通性以工具调用结果证明 |
| 回调配置（⑤↻） | 展示 site_url/redirect_uris 差异后确认 |

## 输出格式

- **阶段报告**（每阶段完成时）：目标、执行动作、门槛验证结果、下一阶段
- **上线报告**（⑥）：三级交付语义（本地已验证/环境已准备/线上验收通过）+ stable_url + 前端版本记录引用；格式见 references/launch-checklist.md
- **失败/断点报告**：当前阶段、失败原因、已恢复/待人工项、webapp.json 状态

## 验证方法

- 每阶段门槛即验证点（见工作流表与 workflow-stages.md）
- ⑥ 上线门槛 = 三层组合（后端项/前端项/连通项），完整清单见 references/launch-checklist.md
- 上线后复查：webapp.json 标记 launched 且 stable_url 可访问

## 注意事项

- **凭据红线**：密钥永不写入 webapp.json/聊天/工具返回；agent 不读取交付文件；devkit 注入优先、半自动兜底；anon key 进入前端产物属预期，Service Role Key 绝不进入
- **边界外处置**：复杂业务逻辑（支付/第三方调用/长任务）超出 v1 数据层边界——明确告知用户并停止，不擅自以 RPC 模拟
- 文件上传（Storage）v1 默认不含：⓪ 识别并说明（可选扩展路径：管理面 `update_supabase_storage` 配 OBS 凭据）
- v1 单环境（webapp.json 字段预留多环境扩展）
- 管理面操作遵循其两阶段确认与执行账本；未知结果不重放、不删账本
- 阶段门槛不通过不前进；强制门（③④）不可跳过

## 参考文档

- references/workflow-stages.md（⓪–⑥ 阶段 playbook）
- references/lifecycle.md（更新/回滚/下线/密钥轮换）
- references/project-state.md（webapp.json 契约）
- references/routing-table.md（跨技能/MCP 路由矩阵）
- references/launch-checklist.md（端到端上线清单）

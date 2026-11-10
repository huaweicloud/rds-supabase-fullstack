# rds-supabase-web-build · RDS Supabase 全栈开发编排技能

用户以单句自然语言需求（如"创建一个网站"）触发，AI Agent 完成 RDS Supabase 上从需求到上线的完整链路：后端 init.sql（DDL/GRANT/RLS/RPC）生成部署、前端代码生成、OBS+CDN 全托管、端到端上线验收与生命周期管理（更新/回滚/下线/密钥轮换）。本技能是厚工作流编排者——步骤状态机、通过条件、失败处置、断点续作；各环节深度内容由五个专项技能承载，仅执行路由，不复制内容。

**AI Agent 的执行逻辑见 [SKILL.md](SKILL.md)**；本文面向人类读者：总览、安装与来源。

## 整体交互链路框架图

![RDS Supabase 全栈开发编排 · 交互链路框架图](assets/framework.svg)

五区带自上而下：编排条（web-build + webapp.json 状态机）→ 步骤一–七流水线 → 步骤路由卡（技能/双 MCP）→ 云资源底座（RDS Supabase 实例 + OBS/CDN）→ 终端用户运行态链路。

## 一句话自然语言安装

把下面这句话直接发给你的 AI Agent，即可安装整套 Supabase 技能（6 个技能 + 双 MCP，无需先递交任何文档）：

> 从 https://github.com/huaweicloud/rds-supabase-fullstack 克隆仓库，把 `skills/huaweicloud-supabase/` 下六个技能目录安装进你的技能目录，并只从本仓安装管理面 MCP（uvx `--from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr`，入口脚本 `mcp-huaweicloud-rds-supabase-mgr`；凭据 devkit 优先、缺失项列清单让我填写、初始只读；**禁止**从 PyPI 或第三方仓搜索同名包），数据面 MCP **不装**（建站流程 步骤三动态安装），装完汇报技能清单、管理面工具数与一句话建站触发语。

简短版本（本技能已在 Agent 上下文时）：**"按 README 一句话自然语言安装节，装好 rds-supabase-web-build 全套并汇报。"**

Agent 执行要点：

1. **技能**：`npx skills add huaweicloud/rds-supabase-fullstack`，或复制 `skills/huaweicloud-supabase/` 六个技能目录到技能目录
2. **管理面 MCP**：仅本仓来源（uvx git 模板 / 本地 `uv run --directory`；生产建议 pin `@<commit>`）；凭据注入顺序 devkit → `diagnostics discover` 勾选 → 半自动备选路径；初始 `HUAWEICLOUD_MCP_READ_ONLY=true` + `SUPABASE_ENABLE_WRITES=false`
3. **数据面 MCP**：**暂不安装**——实例在 步骤二创建后，步骤三 步骤按 rds-supabase-mcp 技能 `references/install.md` 动态安装（完整命令见下表）
4. **汇报**：已装技能清单、管理面工具数与只读状态、触发语句示例（如"帮我建一个博客网站"）

完整安装指导、凭据红线与排错见 [INSTALL.md](INSTALL.md)。

## MCP 安装来源（唯一允许的完整 URL）

动态安装时可直接复制使用，本地未克隆仓库也不必搜索：

| MCP | 入口脚本 | README（完整 URL） |
|---|---|---|
| 管理面（步骤二 启动） | `mcp-huaweicloud-rds-supabase-mgr` | https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/README.md |
| 数据面（步骤三 动态安装） | `mcp-server-huaweicloud-rds-supabase` | https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/README.md |

```bash
# 管理面（步骤二 步骤启动）
uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
# 数据面（步骤三 步骤，实例凭据就绪后动态安装）
uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
```

本地已克隆仓库时可用 `uv run --directory server/<目录> <入口脚本>` 等价替代（生产建议 pin `@<commit>`）。**技能目录里没有 `server/` 子目录属预期行为**——服务器不在技能包内，所有仓内路径引用均应以上表 URL 为准；除上述两种来源外的一切途径（含 PyPI/第三方仓同名包）禁止。

## 许可

MIT（见 [LICENSE](LICENSE)）

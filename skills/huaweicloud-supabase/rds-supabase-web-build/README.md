# rds-supabase-web-build · RDS Supabase 全栈开发编排技能

用户以单句自然语言需求（如"创建一个网站"）触发，AI Agent 完成 RDS Supabase 上从需求到上线的完整链路：需求澄清与设计、后端声明式配置（DDL/GRANT/RLS/RPC）生成部署、前端代码生成、本地测试验证、OBS+CDN 全托管、端到端上线验收与生命周期管理（更新/回滚/下线/密钥轮换）。本技能是厚工作流编排者——九步状态机、通过条件、失败处置、断点续作；各环节深度内容由六个专项技能承载，仅执行路由，不复制内容。

**执行逻辑见 [SKILL.md](SKILL.md)**。

## 整体交互链路框架图

![RDS Supabase 全栈开发编排 · 交互链路框架图](assets/framework.svg)

五区带自上而下：编排条（web-build + webapp.json 状态机）→ 步骤一–九流水线 → 步骤路由卡（技能/双 MCP）→ 云资源底座（RDS Supabase 实例 + OBS/CDN）→ 终端用户运行态链路。

## 安装

安装阶段**只安装 rds-supabase 技能包**（全部技能，从本 GitHub 源码仓克隆/添加）——不安装、不配置任何 MCP 与凭据。把下面这句话直接发给你的 AI Agent 即可：

> 从 https://github.com/huaweicloud/rds-supabase-fullstack 克隆仓库，把 `skills/huaweicloud-supabase/` 下所有技能完整安装进项目级技能目录，装完汇报已装技能清单与一句话建站触发语。

完整安装步骤、各宿主安装目录强约束、网络逃生通道与排错见 [INSTALL.md](INSTALL.md)；建站模式价值对比（传统自建 vs 全托管）见 [USER_GUIDE_REPORT.md](USER_GUIDE_REPORT.md)。

## MCP 安装来源（工作流动态安装时使用；唯一允许的完整 URL）

两台 MCP 不在安装阶段出现，由技能工作流按需动态安装（管理面 → 步骤三、数据面 → 步骤四）。动态安装时可直接复制使用，本地未克隆仓库也不必搜索。**注册位置强约束**：动态安装后只注册进**当前项目的项目级 MCP 配置**（Claude Code `.mcp.json`、CodeArts `.codeartsdoer/`、OfficeAce 项目级配置、opencode `opencode.json`；禁止一切用户级/系统级位置——详见 rds-supabase-mcp 技能 references/install.md）：

| MCP | 入口脚本 | README（完整 URL） |
|---|---|---|
| 管理面（步骤三启动） | `mcp-huaweicloud-rds-supabase-mgr` | https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase_mgr/README.md |
| 数据面（步骤四动态安装） | `mcp-server-huaweicloud-rds-supabase` | https://github.com/huaweicloud/rds-supabase-fullstack/blob/main/server/mcp_server_rds_supabase/README.md |

```bash
# 管理面（步骤三启动）
uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack#subdirectory=server/mcp_server_rds_supabase_mgr mcp-huaweicloud-rds-supabase-mgr
# 数据面（步骤四动态安装，实例凭据就绪后）
uvx --from git+https://github.com/huaweicloud/rds-supabase-fullstack --subdirectory server/mcp_server_rds_supabase mcp-server-huaweicloud-rds-supabase
```

本地已克隆仓库时可用 `uv run --directory server/<目录> <入口脚本>` 等价替代（生产建议 pin `@<commit>`）。**技能目录里没有 `server/` 子目录属预期行为**——服务器不在技能包内，所有仓内路径引用均应以上表 URL 为准；除上述两种来源外的一切途径（含 PyPI/第三方仓同名包）禁止。

## 许可

MIT（见 [LICENSE](LICENSE)）

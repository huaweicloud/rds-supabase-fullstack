# 安装 huawei-cloud-rds-pg-ops 技能

技能位于仓库 `skills/database/rds/huaweicloud-rds-pg-ops/`（database 产品域三级目录）。

## 前置

- Node ≥ 22.20（方式 A）或 git（方式 B）
- 华为云 AK/SK（建议只读起步）

## 方式 A：skills CLI（推荐）

```bash
npx skills add huaweicloud/rds-supabase-fullstack \
  --skill huaweicloud-rds-pg-ops -a claude-code -y
```

## 方式 B：git 复制

```bash
git clone --depth 1 https://github.com/huaweicloud/rds-supabase-fullstack.git /tmp/rsf
mkdir -p <项目根>/.claude/skills
cp -R /tmp/rsf/skills/database/rds/huaweicloud-rds-pg-ops <项目根>/.claude/skills/
```

## 安装位置

默认**项目级**（`<项目根>/.claude/skills/`）。宿主仅支持用户级时停止并报告，不注册。

## 配套 MCP

本技能不含 MCP 服务器。安装后按 `references/install.md` 配置
`mcp-huaweicloud-rds-pg`（uv、从本仓 server 目录启动）。

## 验证

对话中输入「帮我列出 cn-north-4 的 PG 实例」→ 技能应路由到
`list_pg_instances` 并返回实例清单。

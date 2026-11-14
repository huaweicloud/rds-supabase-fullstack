# rds-supabase-postgres-best-practices（Postgres 最佳实践规则库）

Postgres 规则库技能，源自 Supabase 维护的通用规则集（"for Postgres running anywhere"），针对华为云 RDS Supabase 自建部署适配（JWT claims 身份判定、RDS 参数模板通道、扩展可用性、PostgREST 暴露面），并新增 `rds-` 前缀分区承载部署专属规则。共 35 个规则文件、九个分区，每条规则含 Incorrect/Correct 对照与量化收益。

适用承诺：**编写或修改任何存入 Postgres 数据库的内容之前加载**——建表改表、列类型选择、schema 设计、RLS 策略、索引、触发器、数据库函数、主键与 UUID 选型、批量导入、数据恢复；单列变更与单条查询同样适用。诊断场景（慢查询、高 CPU、超时、EXPLAIN 计划、连接耗尽、锁等待、死锁、表膨胀、N+1、深分页、upsert 竞态、JSONB 查询慢、全文检索、定时任务、跨租户数据可见）同样覆盖。

执行逻辑与症状索引见 [SKILL.md](SKILL.md)。

## 规则分区

按影响降序排列，规则文件位于 `references/` 目录：

| 优先级 | 分区 | 影响等级 | 文件前缀 |
|---|---|---|---|
| 1 | 查询性能（缺索引、复合索引、索引类型选型、覆盖索引、部分索引） | CRITICAL | `query-` |
| 2 | 连接管理（池化、连接上限、预备语句、空闲超时） | CRITICAL | `conn-` |
| 3 | 安全与 RLS（多租户隔离、RLS 性能、最小授权） | CRITICAL | `security-` |
| 4 | schema 设计（主键选型、约束、列类型、外键索引、大小写、分区） | HIGH | `schema-` |
| 5 | 并发与锁（短事务、SKIP LOCKED、死锁预防、咨询锁） | MEDIUM-HIGH | `lock-` |
| 6 | 数据访问模式（N+1、批量插入、深分页、upsert） | MEDIUM | `data-` |
| 7 | 监控与诊断（pg_stat_statements、EXPLAIN、VACUUM/ANALYZE） | LOW-MEDIUM | `monitor-` |
| 8 | 高级特性（全文检索、JSONB 索引） | LOW | `advanced-` |
| 9 | 华为云 RDS 部署专属（JWT claims RLS、参数模板、身份辅助函数、定时任务） | CRITICAL | `rds-` |

使用方式：Agent 在执行 SQL 相关任务时按 SKILL.md 的症状与任务索引定位规则文件后按规则修改 SQL；也可直接检索 `grep -il "关键词" references/`。新增规则遵循 `references/_contributing.md` 的格式契约。

## 快速安装

### 安装范围

本技能为纯规则文档（SKILL.md 与 38 个规则文件），自包含、零运行期依赖：不需要 MCP 服务器、不需要凭据、不限定数据库连接方式（SQL 变更可经任意通道执行）。单独安装即可完整使用。

### 方式一：自然语言安装（推荐）

将下面这句话发送给你的 AI Agent（适用于 Claude Code、CodeArts、opencode 等支持 Agent Skills 标准的宿主）：

> 从 https://github.com/huaweicloud/rds-supabase-fullstack 克隆仓库，把 `skills/huaweicloud-supabase/rds-supabase-postgres-best-practices/` 复制到本项目的项目级技能目录（禁止装入个人级或系统级目录），安装完成后报告安装路径。

说明：

- 各宿主的项目级技能目录：Claude Code 为 `<项目根>/.claude/skills/`，opencode 为 `<项目根>/.opencode/skills/`，CodeArts 为 `<项目根>/.codeartsdoer/skills/`；其余宿主使用其项目级技能机制。
- 需要完整技能包（平台操作、客户端集成等）时改为整套安装：将安装语句中的范围替换为 `skills/huaweicloud-supabase/` 全目录。

### 方式二：手动安装

```bash
TMP=$(mktemp -d)
git clone https://github.com/huaweicloud/rds-supabase-fullstack "$TMP/repo"
cp -r "$TMP/repo/skills/huaweicloud-supabase/rds-supabase-postgres-best-practices" <项目技能目录>/
rm -rf "$TMP"
```

网络不可达时改用 ZIP 归档下载：把上述 git clone 替换为下载 `https://github.com/huaweicloud/rds-supabase-fullstack/archive/refs/heads/main.zip` 并解压，复制解压目录下 `skills/huaweicloud-supabase/rds-supabase-postgres-best-practices`。禁止使用 `npx skills add` 等包管理器安装——技能包未发布至此类渠道。

安装校验：技能目录内含 `SKILL.md` 且 `references/` 下有 35 个规则文件；克隆了仓库的可运行 `uv run --directory server/mcp_server_rds_supabase python ../../scripts/validate_skills.py`，期望输出 `validate-skills: OK (8 skills)`。

## 使用

安装后正常开展开发对话即可，Agent 在编写或修改 SQL、设计 schema、排查性能问题前自动加载。触发语句示例：

> 帮我设计订单表结构：每天百万行写入，按买家和状态查询为主。

> 这条关联查询越来越慢，帮我优化并说明原因。

> 给多租户表写 RLS 策略，用户只能访问自己租户的数据。

规则库不限定数据库操作通道：SQL 可经 MCP `execute_sql`、psql 或 RDS 控制台执行；规则本身适用于任何 Postgres 通道。

## 许可

MIT。衍生自 [supabase/agent-skills](https://github.com/supabase/agent-skills)（commit `c9be0e9`，MIT），针对华为云 RDS 部署适配并扩充。

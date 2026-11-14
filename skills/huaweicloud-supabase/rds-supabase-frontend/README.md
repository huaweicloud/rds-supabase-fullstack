# rds-supabase-frontend（华为云 OBS 静态前端部署技能）

面向华为云 OBS 静态托管的**前端部署与 Supabase 接入技能**：创建并部署、更新、回退和维护 OBS 静态前端（入口域名直连桶 `obs-domain` 或经 CDN 回源 `obs-cdn` 两条路线），接入已有华为云 RDS Supabase（浏览器直调其 HTTPS API，终端用户无需华为云账号），以及为这些任务准备构建环境。保留项目已有框架、构建环境和 OBS 发布方式，不新增独立部署 CLI。

核心纪律：先快照再动手（只读检查项目记录、OBS 配置、产物清单与入口候选，由快照定区域/桶/路线/差异）；重复发布走快速路径（已有成功记录且产物哈希一致时单遍上传+批量验证）；发布校验以真实 URL 的内容、MIME、版本与浏览器验收为准；endpoint 属内部云（`.ulanqab.huawei.com`）时自动切换内部云规程。

执行逻辑见 [SKILL.md](SKILL.md)。

## 能力概览

| 领域 | 内容 |
|---|---|
| 托管路线 | `obs-domain`（入口域名直连桶，默认）/ `obs-cdn`（入口域名经 CDN 回源同一公开桶） |
| 部署与更新 | 构建产物上传公开读 OBS 桶、website 配置、域名绑定、批量 GET 发布校验、哈希级回退 |
| Supabase 接入 | 前端认证流（authentication）、API 调用（supabase）、区域选择（regions） |
| 环境适配 | 构建环境准备（build-environment）、内部云规程（internal-cloud）、OBS 发布（obs-release） |
| 框架适配 | 常见框架的构建与产物形态（frameworks）及示例（references/examples） |

## 安装

见 [INSTALL.md](INSTALL.md)。

## 使用

安装后正常开展对话即可，命中场景时 Agent 自动加载。触发语句示例：

> 把我的 Vite 项目部署到华为云 OBS，用我自己的域名访问，接上现有的 RDS Supabase。

> 前端发了个修复版，帮我更新线上产物并验证。

## 许可

MIT。

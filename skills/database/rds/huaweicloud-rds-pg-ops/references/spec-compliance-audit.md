# 规范遵从审核报告：huaweicloud-rds-pg-ops（Skill 包）+ mcp_server_rds_pg（MCP 工程）

> 审核依据：《华为云基础云服务 Skill 开发与管理规范 v2.0.0》（全文 13 章，仓内 `.playwright-mcp/huaweicloud-skill-spec-v2.md`）
> 审核对象：本技能包（SKILL.md + references/ 10 场景文件 + INSTALL.md）与配套 MCP 工程 `server/mcp_server_rds_pg`（74 工具，Python 三层架构）
> 审核日期：2025-11-24 · 审核轮次：第 1 轮（含整改复查）

---

## 0. 总体结论

| 对象 | 合规 | 违规 | 豁免（含理由） | 整改后状态 |
|---|---|---|---|---|
| Skill 包（skills/database/rds/huaweicloud-rds-pg-ops） | 18 | 6 | 5 | 全部违规项已整改或按豁免口径处理 |
| MCP 工程（mcp_server_rds_pg，仅审规范符合性，未改代码） | 8 | 1 | 2 | 违规项为文档路径陈旧（非代码），已记遗留 |

---

## 1. 分型豁免口径（MCP 型技能 vs 规范的 CLI 前提）

规范 v2.0.0 默认面向 **KooCLI/CLI 型技能**（Agent 生成 `hcloud` 命令执行）。本技能是 **MCP 型技能**：Agent 经 MCP 协议调用 `mcp-huaweicloud-rds-pg` 服务器的 74 个结构化工具，不生成、不执行任何 `hcloud` 命令。为此建立以下分型口径，供后续其他 MCP 型技能复用：

### 1.1 不适用条款（CLI 专属，MCP 型豁免）

| 规范条款 | 内容 | 豁免理由与替代 |
|---|---|---|
| §6 全章 | KooCLI 命令格式（`hcloud <SERVICE> <Operation>`、`--cli-region`、数组/嵌套参数格式、`--limit=1` 探索查询、v3 后缀/Keystone 前缀等易错点） | MCP 工具参数为结构化 JSON Schema，由服务器端校验；`--cli-region` 退化为 `HUAWEICLOUD_REGION` 环境变量。SKILL.md「核心命令」章节改为按功能分组的工具表（对应规范意图的 MCP 形态） |
| §2.5 节 3「前置条件+KooCLI」中 CLI 版本与验证命令 | `hcloud version` ≥ 7.2.2 | 替代为 MCP 服务器版本（pyproject v0.1.0）+ `uv sync` + `/health` 探活 + `tools/list` 74 工具 |
| §2.2 四件套之 `cli-installation-guide.md` | 「涉及 CLI 命令时必选」 | 不涉及 CLI 命令 → 不触发该必选条件；安装指引由本包 `references/install.md`（MCP 服务器安装/宿主注册/环境变量）承担同等职责 |
| §5.4 集成测试「CLI 命令端到端执行（hcloud + jq）」 | 每次跑真实 hcloud | 替代为 LIVE-TESTING.md 的 G/B 测试组（真实 OpenAPI 端到端）+ `uv run pytest` 三件套 |
| §7.2 / §7.3 认证梯队的 hcloud configure 项 | KooCLI 配置文件 | MCP 工程用 AK/SK 环境变量（`HUAWEICLOUD_ACCESS_KEY/SECRET_KEY`），符合「配置外置」；规范 §8.1 环境变量速查同样认可该来源 |

### 1.2 依然适用的核心条款（不分型，MUST）

- §2.1/2.3 命名与三级目录、§2.4 frontmatter 校验（yaml.safe_load、name=目录名、description ≤1024）
- §3.1 大小限制（SKILL.md ≤500 行、包 ≤40 文件、≤50 MB）、§3.2 扩展名白名单
- §4.2 description 四原则（祈使句/意图优先/pushy/简洁）与触发词中英文
- §1.4 三条硬规则（无状态执行层、显式传参、技能间禁直接调用——本技能经 Agent 编排，未引用其他具名 Skill）
- §4.5 核心设计模式：逐步确认（两段式）、防跳步（user-only 停）、安全优先（只读起步/写开关双闸）、双输出（JSON 信封+人类报告）、配置外置（凭证环境变量）
- §9 安全规范全部条款（AK/SK 纪律、写确认、密码不入对话、报告脱敏、禁止读凭证文件）
- §5.3 三级验证思想的 MCP 形态落地（连接验证→功能验证→验收五连验）
- 渐进式披露：SKILL.md 只放路由与纪律，场景细节在 references/ 按需加载（10 个场景文件均带「何时读」标头）

**结论**：MCP 型技能与规范的关系是「执行面替换、治理面全继承」——凡属治理与安全条款一律适用；凡属命令语法与 CLI 工具链条款按上表豁免并给出 MCP 等价物。

---

## 2. Skill 包逐条审核

### 2.1 结构（规范 §2.1/2.2/2.3，检查清单「结构」「命名」）

| 检查项 | 结论 | 说明 |
|---|---|---|
| 三级目录 skills/database/rds/<技能名> | **违规→已整改** | 原在 skills/ 一级；已 `git mv` 至 `skills/database/rds/huaweicloud-rds-pg-ops/` |
| 技能包自包含（SKILL.md 唯一入口 + references/） | 合规 | 结构与 §2.2 蓝图一致 |
| 包目录命名 `huawei-cloud-{产品}-{功能}` 公式 | **违规（低危，建议保留）** | 目录名为 `huaweicloud-rds-pg-ops`，非规范的 `huawei-cloud-` 前缀。改名会破坏 MCP 工程内 `skill/huaweicloud-rds-pg-ops` 镜像目录与既有用户安装路径，且本仓技能族统一用 `huaweicloud-` 前缀（仓级惯例）。**豁免处理**：以仓库既有命名体系为准，审核记录在案；若上游开源仓库强制 `huawei-cloud-` 前缀，需整族统一迁移 |
| 参考文档 kebab-case 命名 | 合规 | backup.md / connection.md / iam-policies.md 等均合规 |
| 四件套：iam-policies.md | **违规→已整改** | 原缺失；已补（74 工具按分组列 RDS/CES Action + 最小权限 JSON + 权限失败流程） |
| 四件套：verification-method.md | **违规→已整改** | 原缺失；已补（三级验证 + 五连验 + LIVE-TESTING 矩阵引用） |
| 四件套：acceptance-criteria.md | 推荐级，原缺失→已补 | MCP 型技能验收清单 |
| 四件套：cli-installation-guide.md | **豁免** | 见 §1.1：不涉 CLI 命令，必选条件不触发；职责由 references/install.md 承担 |
| references 引用路径有效 | 合规 | SKILL.md 内 `references/xxx.md` 为 Skill 根相对路径，目录移动后不受影响（已 grep 复核无绝对/越级路径） |

### 2.2 Frontmatter 与格式（规范 §2.4，检查清单「格式」）

| 检查项 | 结论 | 说明 |
|---|---|---|
| yaml.safe_load 可解析 | 合规 | python3 实测解析成功 |
| name 与目录名一致 | 合规 | `huaweicloud-rds-pg-ops` 双向一致（整改后新路径仍一致） |
| name 约束（1-64 字符、小写字母数字连字符、无连续/首尾连字符） | 合规 | 23 字符，合法 |
| description ≤1024 字符 | 合规 | 569 字符（含中英混排触发词，符合 §2.6「description 可中英混排」） |
| description 五要素（做什么/何时用/触发词/技术基础/边界） | 合规 | 功能概要、场景枚举、英文 triggers、「不适用于」边界齐备 |
| tags ≤5 | 合规 | 5 个（huawei-cloud, rds, postgresql, ops, mcp） |
| version 字段 | 合规 | 修改已有技能 → 版本已递增 1.0.0 → **1.1.0**（规范 §2.4/§10.2 修改必填并递增） |

### 2.3 大小与文件（规范 §3，检查清单「规模」）

| 检查项 | 结论 | 说明 |
|---|---|---|
| SKILL.md ≤500 行 | 合规 | 整改后 133 行（原 78 行中文版） |
| 包文件数 ≤40 | 合规 | 15 个文件（SKILL.md + INSTALL.md + 13 references） |
| 包体积 ≤50 MB | 合规 | 全部为 .md 文本，约 60 KB |
| 扩展名白名单 | 合规 | 全部 `.md`，在白名单内 |

### 2.4 正文规范（规范 §2.5/2.6/§4.5/§5.2）

| 检查项 | 结论 | 说明 |
|---|---|---|
| 正文英文 | **违规→已整改** | 原正文全中文；已重写为英文（§2.6），frontmatter description 保持中英混排触发词 |
| 11 节顺序结构 | **违规→已整改** | 原为「概述/执行通道/硬纪律/场景路由/生命周期/排错/安装」自定义结构；已按规范 2.5 重排为 11 节（概述含 5 个典型用例与架构说明、安全硬约束、前置条件、工作流、核心命令分组表、参数确认表、输出格式、验证方法、最佳实践、参考文档、注意事项） |
| 安全硬约束章节（规范 2.5 注记「有条件必须」） | 合规（强化） | 整改后第 2 节共 8 条硬纪律：两段式、user-only、防重放、action 锁、密码 request_ref、job 轮询、操作串行、只读起步——正对应规范「写操作逐步确认/安全优先/防跳步」模式 |
| 典型用例 3-5 个 | **违规→已整改** | 原无显式用例列表；概述节现含 5 个 |
| 触发词体系（渐进披露第①层） | 合规 | description 含 8 组英文触发词 + 中文场景枚举 |
| 场景路由表（渐进披露第③层） | 合规 | 11 行路由表，逐文件指明何时读（references 均带「何时读」标头） |
| Gotchas 段（§5.2） | 合规 | 注意事项节为 7 行症状→处置表（plan_id 已消费、DBS.201015、引擎守卫等反直觉点） |
| 输出格式模板 | 合规 | 第 7 节定义信封形态与报告骨架 |
| 参考文档无外链 | 合规 | 全部指向包内 references/ |

### 2.5 安全规范（规范 §9，检查清单「安全」）

| 检查项 | 结论 | 说明 |
|---|---|---|
| 无 AK/SK 硬编码（grep 扫描） | 合规 | 全包无明文凭证；install.md 的 .mcp.json 示例用 `"..."` 占位 |
| 不引导用户对话内输 AK/SK | 合规 | install.md/SKILL.md 均要求环境变量带外配置 |
| 凭证文件禁读 | 合规 | 密码 request_ref 文件明确「Agent 禁止读取、打印、记录」 |
| 密码不入对话/报告 | 合规 | 密码纪律硬约束 #5 + 输出格式节「脱敏不可绕过」 |
| 写操作前确认 | 合规 | 两段式为硬约束 #1，全部 27 个写类工具经 confirm=false/true |
| 计费决策用户拍板 | 合规 | user-only 硬约束 #2 + 参数确认表 |
| 生产风险提示 | 合规 | 停机计费 warning、EIP 未释放计费、跨区备份费用等在 references 场景文件 |
| 首次接入只读验证 | 合规 | 前置条件节 READ_ONLY=true 建议路径 |

---

## 3. MCP 工程 mcp_server_rds_pg 规范符合性审核（只审不改）

| 规范条款 | 结论 | 说明 |
|---|---|---|
| 三层单向架构（tools→service→client，tools 禁 import SDK） | 合规 | 实测 tools/*.py 仅 import huaweicloud_mcp_core.guard 与本包 service；SDK import 全部在 client/ |
| 场景化工具（动词_对象命名） | 合规 | 74 工具全部 `动词_对象`（list_/show_/create_/set_/change_/resize_…） |
| 风险声明（每工具 @guard） | 合规 | 74 处 @mcp.tool 对应 74 处 @guard(risk=READ/WRITE/DANGEROUS)（creation 9、backup_database 15、instance 6、connection 9、m3 26、network 12，实测合计 74） |
| 写操作两段式 + plan_id 防重放 | 合规 | service/mutate.py run_mutation 管线：10 分钟 TTL、单次消费、digest 校验、提交前回查实例状态 |
| 配置外置（凭证不硬编码） | 合规 | AK/SK 全经环境变量，grep 无明文 |
| 输出脱敏 + 审计 | 合规 | core build_server 强制脱敏（不可关）+ JSONL 审计（含被拦调用） |
| scripts/ 规范（§4.4：shebang、错误处理、退出码） | **豁免** | MCP 型技能无 scripts/ 目录——可执行面在 MCP 服务器（工程内 ruff/mypy/pytest 三件套与 LIVE-TESTING 承担同等质量职责）；§4.4 的对象（SKILL 包内脚本）不存在 |
| 工具参数 ≤10（仓级架构铁律） | 合规 | 抽查 create_pg_instance 等最复杂工具参数在限内 |
| README 配套技能路径 | **违规（文档，非代码）** | `mcp_server_rds_pg/README.md` 第 3 行仍写 `skills/huaweicloud-rds-pg-ops`（旧一级路径，现为 `skills/database/rds/...`）。因本任务禁改 server/ 目录，记为遗留项 |
| LIVE-TESTING 测试矩阵（§5.4 的 MCP 等价物） | 合规 | G1-G6 + B1-B16 全量矩阵，含验收标准与实测状态 |
| Quality 上报集成（§10）/ VOD Collector（§11） | **豁免** | 需官方 creator/injector 工具链（huawei-cloud-skill-quality-cli-inject 有条件访问）；当前仓未接入该生态，遥测注入留待上游开源流程时统一处理。非豁免即违规项，因为属「配套工具链可用性」问题而非包内容问题 |

---

## 4. 整改清单（本轮已执行）

1. SKILL.md 重写：英文正文 + 规范 2.5 的 11 节顺序 + 8 条安全硬约束（保留两段式/user-only/防重放/action 锁/request_ref/job 轮询全部原纪律，英文表述）+ 5 个典型用例 + version 递增 1.1.0
2. 补 `references/iam-policies.md`（74 工具按 12 组列 RDS/CES Action、最小权限 JSON 两份、403 处理五步流程、正误对比）
3. 补 `references/verification-method.md`（连接/功能/五连验三级 + LIVE-TESTING 矩阵引用）
4. 补 `references/acceptance-criteria.md`（MCP 型技能验收清单：结构/内容/安全一票否决/工程侧）
5. 目录迁移 `git mv skills/huaweicloud-rds-pg-ops skills/database/rds/huaweicloud-rds-pg-ops`（git 全程识别为 rename）
6. INSTALL.md 更新安装路径（两处）
7. 10 个场景 references 文件保持不动（中文合规、实测背书、相对路径不受迁移影响）
8. 本审核报告落盘（即本文件）

## 5. 验证记录（整改后实测）

- frontmatter `yaml.safe_load` 解析成功；name=目录名；description 569 字符；tags 5
- SKILL.md 133 行（≤500）；包 15 文件（≤40）；扩展名全 `.md`（白名单内）
- 全包 grep 无 AK/SK/密码明文
- 旧路径引用 grep：skills/ 下零残留；仅 `server/mcp_server_rds_pg/README.md`（遗留，见下）

## 6. 遗留问题

1. **`server/mcp_server_rds_pg/README.md:3` 旧路径**（`skills/huaweicloud-rds-pg-ops` → 应为 `skills/database/rds/huaweicloud-rds-pg-ops`）——本任务禁改 server/，建议主窗口或下轮提交顺手修正（一行文档改动）
2. **包名前缀**：目录名 `huaweicloud-rds-pg-ops` 不符合规范 §2.3 的 `huawei-cloud-` 命名公式（仓级惯例豁免，见 §2.1）。若技能要单独贡献到 GitCode huaweicloud-skills 开源仓库，需整族统一改名并同步 MCP 工程 `skill/` 镜像目录
3. **Quality 遥测 / VOD Collector 未接入**（§10/§11）：依赖官方 creator/tester 工具链，属生态接入事项而非包内容缺陷
4. **MCP 工程内 `skill/huaweicloud-rds-pg-ops` 镜像目录**（mcp_server_rds_pg/skill/）仍是旧版且未随迁移更新——该目录在仓外（`mcp_server_rds_pg` 工程内为独立 git 管理推测），需工程侧自行同步或删除镜像

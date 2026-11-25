# 验收标准（acceptance-criteria.md）

> 何时读：技能包发版、合入 PR 前的最终验收；评审者核对 MCP 型技能质量门槛时。

## 1. 概述

本清单针对 **MCP 型技能**（Agent 经 MCP 协议调用工具服务器，非 KooCLI/CLI 型）的验收标准，是规范 13.4 检查清单在本形态下的落地。逐项核对，全部通过才可发版。

## 2. 结构验收

- [ ] 技能包含 SKILL.md；references/ 具备 iam-policies.md、verification-method.md、acceptance-criteria.md（cli-installation-guide.md 按 MCP 分型豁免，安装指引由 install.md 承担）
- [ ] 目录位于 `skills/database/rds/<skill-name>/`，包目录名 = frontmatter `name`
- [ ] Frontmatter 通过 `yaml.safe_load`；description ≤ 1024 字符；tags ≤ 5
- [ ] SKILL.md ≤ 500 行、英文正文；references 文档中英文皆可
- [ ] 技能包文件数 ≤ 40，全部扩展名在白名单内
- [ ] SKILL.md 对 references/ 的引用为相对路径且逐文件指明「何时读」

## 3. 内容验收

- [ ] 正文章节按规范 2.5 的 11 节顺序（概述/安全硬约束/前置条件/工作流/核心命令/参数确认/输出格式/验证方法/最佳实践/参考文档/注意事项）
- [ ] description 遵循四原则：祈使句、意图优先、明确边界（含「不适用于」）、触发词中英文覆盖
- [ ] 概述含架构文字说明 + 典型用例 3-5 个
- [ ] 写操作场景体现核心设计模式：逐步确认（两段式）、防跳步（user-only 未决即停）、安全优先（只读起步）、双输出（JSON 信封 + 人类可读报告）

## 4. 安全验收（MUST，一票否决）

- [ ] 全包 grep 无 AK/SK/密码明文；凭证一律环境变量带外配置
- [ ] 文档/示例中不出现「用户在对话中输入 AK/SK」的指引
- [ ] 密码经 `write_pg_secret_request` request_ref 别名，明文不入对话、不入审计
- [ ] 写操作全部两段式（confirm=false 预览 → 用户明确同意 → confirm=true + plan_id）
- [ ] 计费类决策（包周期时长、EIP 计费）user-only，Agent 不代选
- [ ] unknown 结果防重放（先查 job，禁止盲目重试）

## 5. MCP 工程侧验收（配套服务器）

- [ ] 74 工具逐一带 `@guard(risk=...)` 声明（READ/WRITE/DANGEROUS）
- [ ] 三层架构 tools → service → client 单向依赖，tools 层禁 import SDK
- [ ] `ruff check` + `mypy` + `pytest --cov` 三件套全绿
- [ ] 只读模式（HUAWEICLOUD_MCP_READ_ONLY）与写开关（RDS_PG_ENABLE_WRITES）双闸生效
- [ ] 输出脱敏不可关；审计 JSONL 完整（含被拦截调用）
- [ ] LIVE-TESTING.md 对应测试组全部 ✅（发版时点）

## 6. 验收执行顺序

1. 结构验收（机械检查：yaml 解析、行数、文件数、扩展名、grep 扫描）
2. 内容验收（人工对照章节与模式）
3. 安全验收（一票否决项）
4. 工程侧验收 + verification-method.md 三级验证全链跑通

## 7. ✅/❌ 正误对比

- ✅ 验收记录附证据（命令输出、测试报告编号、审计日志样例）
- ❌ 「工具都注册了就算过」——注册 ≠ 两段式/脱敏/防重放行为正确
- ❌ 用生产实例做破坏性验收（应使用专用测试实例或仅 READ 工具）

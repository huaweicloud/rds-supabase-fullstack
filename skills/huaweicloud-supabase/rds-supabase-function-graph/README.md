# rds-supabase-function-graph（RDS Supabase FunctionGraph 云函数技能）

为 RDS Supabase Web 应用承载 **Postgres RPC 装不下的服务端业务逻辑**：交易通知、对接外部系统、复杂领域逻辑、高安全隐私处理。生成零依赖 Node.js 函数 → 经 KooCLI（`hcloud`）部署到华为云 FunctionGraph → 共享版 APIG 触发器暴露 HTTPS 端点 → **函数内验签 Supabase GoTrue JWT** → `fgs-gate.py` 机械核验"无认证请求必须被拒绝"等安全事实。

## 安装

技能包随 rds-supabase 六技能一起安装（见 [web-build INSTALL.md](../rds-supabase-web-build/INSTALL.md)），无独立安装步骤、无新增 MCP 服务器（云操作全部经 KooCLI）。

## 使用

触发语句示例：

> 给我的博客网站加一个交易通知云函数：下单后异步通知发货系统，需要幂等防重放

技能自动执行：环境检查（KooCLI/认证/命令面自校准）→ 逻辑分解确认 → 样板代码生成 → 部署（OBS 私有制品 + APIG 触发器）→ **安全验证与发布**（无认证 401 / 坏 JWT 401 / 真 JWT 200 / CORS 精确 origin 机器核验 + 版本别名固化）→ 前端联调（fetch 封装 + 幂等重放验证）。

## 前端安全调用链（v1 · 共享版 APIG 路线）

```
前端（GoTrue JWT）
  ↘ APIG 触发器（auth=none，v1 唯一入口形态）
      ↘ 函数内：验签（FGS_JWT_SECRET）→ 精确 CORS → 幂等 → 统一错误契约
```

密钥只存函数环境变量（`--cli-json-file` 由用户组装，agent 不见明文）；升级路径（专享版 APIG 鉴权器 / DEW CSMS / VPC 直连）见 `references/secret-management.md` 附录。

## 文档

- [SKILL.md](SKILL.md)：六步工作流与执行纪律（agent 入口）
- `references/`：workflow-stages（playbook）、project-state（functions.json 契约）、routing-matrix（判定矩阵）、cli-commands（命令链）、secret-management（密钥纪律）
- `template/`：零依赖 Node.js 18 样板（验签/CORS/幂等/REST/错误契约 + 本地事件回放）
- `scripts/fgs-gate.py`：独立验证门 · `tests/`：21 用例 pytest

# 制品契约（functions.json）与 trace

## functions.json

位置：`<project>/.hwsupabase/functions.json`（与 webapp.json 同目录；webapp.json 经 `webapp_ref` 关联本文件）。**密钥/密码/凭证/token/用户数据永不入记录**——env 只存名字。

```json
{
  "schema_version": 1,
  "webapp_ref": ".hwsupabase/webapp.json",
  "functions": [
    {
      "name": "notify-transaction",
      "runtime": "Node.js18",
      "handler": "index.handler",
      "code_sha256": "<64 位小写 hex>",
      "obs_key": "artifacts/functions/notify-transaction/<sha8>/pkg.zip",
      "env_names": ["FGS_JWT_SECRET", "FGS_ALLOWED_ORIGINS", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"],
      "vpc": null,
      "db_role": null,
      "triggers": [
        {"type": "apig", "auth": "none", "url": "https://<api-gw-host>/<path>", "path": "/notify"}
      ],
      "idempotency": {"enabled": true, "key_field": "request_id"},
      "versions": [
        {"version": "1", "sha256": "<该版本 zip sha256>", "alias": "prod"}
      ]
    }
  ],
  "stages": {
    "history": [{"stage": "fgs_env_ready", "status": "passed", "at": "2026-11-11T08:00:00Z", "note": null}],
    "last_completed_stage": null
  }
}
```

### 字段规则

| 字段 | 规则 |
|---|---|
| `schema_version` | 固定 1 |
| `functions[].name` | 非空；小写字母/数字/连字符（云侧函数名约束） |
| `code_sha256` | 64 位小写 hex（zip 产物） |
| `env_names` | 字符串数组；**apig 触发函数必含 `FGS_JWT_SECRET` 与 `FGS_ALLOWED_ORIGINS`** |
| `vpc` | v1 固定 `null`（数据访问经 Kong 网关 REST；VPC 直连为 v2 升级项） |
| `db_role` | v1 固定 `null`（保留字段：v2 每函数受限角色） |
| `triggers[].auth` | v1 固定 `"none"`（函数内自验；网关层鉴权为 v2 专享版路线） |
| `triggers[].url` | 必须 https（loopback 豁免仅限本地测试） |
| `versions[].alias` | 已发布版本标 `"prod"`；同函数至多一个 `"prod"` |
| `stages.history` | 只追加不改写；`{stage, status(passed/failed/blocked), at(RFC3339 UTC), note}` |
| 阶段枚举 | `fgs_env_ready → functions_confirmed → code_built → deployed → released → integrated`；横向追加态 `rollback_switched`、`rollback_verified`、`decommissioned` |

### 不变量

- 阶段只前进；断点重验不信任历史结论（gate 现场核验）
- 部署≠发布：`deployed` 只证明函数存在可调用；`released` 才是发布完成
- 切换≠成功：别名切换后必须重验收（`rollback_verified` 同理）
- 密钥轮换只更新受保护文件与函数 env，functions.json 的 env_names 不变

## trace.jsonl

共用 `<project>/.hwsupabase/trace.jsonl`（与 web-build 共文件、各查各的阶段枚举）。每个 KooCLI/CLI 调用后追加一行：

```json
{"at": "2026-11-11T08:00:00Z", "stage": "deployed", "tool": "hcloud FGS CreateTrigger", "intent": "创建 APIG 触发器", "status": "ok", "note": null}
```

| 字段 | 规则 |
|---|---|
| `at` | RFC3339 UTC |
| `stage` | 本技能阶段枚举值 |
| `tool` | CLI 命令名（`hcloud FGS ...`、`hcloud obs ...`、`zip`、`node`、`fgs-gate`）——**不得携带参数中的密钥值或 cli-json-file 内容** |
| `status` | `ok` / `fail` / `blocked` |
| `note` | null 或一句结论（无敏感值） |

`deployed` 起各阶段 passed 前必须存在该阶段的 ok 记录（fgs-gate check-stage 强制核验）。

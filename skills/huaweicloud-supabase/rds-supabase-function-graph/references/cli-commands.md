# KooCLI 命令链与自校准纪律

## 状态声明

下表所有命令名与参数名均为**知识推断**（网络阻断未能实测官方 API 文档）。步骤一 `--help` 自校准是硬前提：**实测输出与本表冲突时，以实测为准并记入 trace note**。

## 命令链（按步骤顺序）

| 步骤 | 命令（待实测） | 说明 |
|---|---|---|
| 一 | `hcloud configure test` | 连通性自检 |
| 一 | `hcloud FGS CreateFunction --help` | 命令面自校准（CreateTrigger / UpdateFunctionConfig 同） |
| 三 | `node functions/<fn>/handler.js < test-events/apig.json` | 本地事件回放自测 |
| 四 | `zip -r pkg.zip .` | 零依赖产物打包 |
| 四 | `hcloud obs cp pkg.zip obs://<bucket>/<key>` | 私有 artifacts 上传 |
| 四 | `hcloud FGS CreateFunction` | body：func_name/package/runtime/handler/code_type=obs/memory_size/timeout |
| 四 | `hcloud FGS UpdateFunctionCode` | code_type=obs + 桶 URL |
| 四 | `hcloud FGS UpdateFunctionConfig --cli-json-file=<path>` | env/VPC 配置——**json 文件由用户/受保护文件组装，agent 只传路径** |
| 四 | `hcloud FGS CreateTrigger` | trigger_type_code=APIG；event_data 含 auth（v1 固定 none）、分组/路径 |
| 四 | `hcloud FGS InvokeFunction` | 冒烟测试（同步，test event） |
| 五 | `hcloud FGS CreateFunctionVersion` | 版本固化 |
| 五 | `hcloud FGS CreateFunctionAlias` / `UpdateAlias` | prod 指向新版本（回滚=切回） |
| 横向 | `hcloud FGS ListFunctions` / `ShowFunctionConfig` / `DeleteFunctionTrigger` / `DeleteFunction` | 查询与下线 |

## 纪律

1. **`--help` 先行**：每个新命令首次使用前先跑 `--help` 核对参数与枚举；schema 不猜（frontend 技能既有纪律平移）
2. **JSON 输出**：`--cli-output=json`（或命令默认 JSON）+ `--cli-query`（JMESPath）字段过滤；解析失败不得盲重试，先核对返回结构
3. **幂等重入**：部署链任一步失败后重入，先 `ListFunctions`/`ShowFunctionConfig` 查现状再决定 create/update；已存在即更新而非报错终止
4. **URN 记录**：CreateFunction 返回的 URN 回写 functions.json note（不在契约字段内，便于后续版本操作定位）
5. **费用意识**：FunctionGraph 免费额度（百万次调用/月量级，以实测账单为准）外按量计费；OBS artifacts 存储计费——步骤二确认清单时一并预估

## 已知风险对冲

| 风险 | 对冲 |
|---|---|
| API 名与文档不符 | `--help` 自校准 + trace note 记录实测差异 |
| zip 大小超限（inline 约 20MB / obs 约 40MB） | 零依赖样板极小（<50KB）；出现依赖即设计违规停止 |
| 触发器 URL 首次可达延迟 | 待生效类失败：15~30s 间隔重试上限 10 分钟 |
| 共享版 APIG 限流 | v1 不承诺 QPS；交易高峰引导用户评估 v2 专享版（secret-management.md 附录） |

# 入口域名、证书与入口探测

产物发布前后的域名环节：从用户提供的根域名派生入口域名、按托管路线绑定、配置 DNS、补齐 HTTPS，并对入口做一次实际探测。托管路线的资源前提见 [域名与托管](hosting.md)，发布与切换见 [OBS 发布](obs-release.md)，探测结果的记录字段见 [记录契约](record-contract.md#checksjson)。

本文件回答两个问题：入口是否真的能打开，打不开是谁的问题。它不代替 [真实验收](deployment.md#真实验收)。

## 前置条件

以下由用户提供，agent 只核实和记录，不代替用户完成：

- 根域名已由用户持有，并在适用区域满足备案条件。
- 根域名 DNS 托管在华为云时才能全自动写入记录；DNS 在第三方时按 [DNS](#dns) 降级。
- 本次允许创建的资源在一次性确认清单内（入口域名、证书、DNS 记录、路线选择）。

缺任一项仍可继续建域名资源，结果按 [失败后处置](#失败后处置) 报告，不宣称入口可用。

## 入口域名

1. 用已有记录中的入口域名；没有记录时使用用户提供的完整域名。
2. 用户只给根域名时派生 `www.<根域>`。派生名冲突（已被其他资源绑定、解析已指向别处、或用户已占用）时停止并询问，不静默改用其他标签，也不切换到存储服务默认域名。
3. 一次性确认清单中列出最终域名与本次路线，确认后不再逐项打断。

## 临时访问域名（确定性，原型/测试验证）

无正式域名与备案的原型验证场景（上层工作流勾选「临时访问」时），使用确定性自定义域名 + 本机 hosts 映射，不购买域名、不办备案、不接 CDN：

1. **域名固定**：`<应用名英文化>.huaweicloud-rds.com`（slug：小写字母/数字/连字符；为空或冲突追加短 uuid）——可复现，不随机不询问。
2. **桶绑定自定义域名**：在 OBS 域名管理为公开读托管桶新增该域名（命令经 `hcloud obs --help` 或官方帮助核实，不猜测字段；先查后建，冲突即停）。
3. **本机 hosts 映射**：解析 OBS endpoint 的 A 记录 IP → 向 hosts（Linux/macOS `/etc/hosts`；Windows `%SystemRoot%\System32\drivers\etc\hosts`）**追加** `IP → 域名` 行：
   - **只追加带标记行、禁止破坏已有映射**：行前加标记注释 `# rds-supabase-frontend:<项目名>`；目标域名已存在且 IP 相同 → 幂等跳过；IP 不同 → 仅替换本流程标记行，其余行一律不动
   - 修改前备份；系统文件须 root/管理员权限——展示精确变更经用户确认后执行
   - Linux/macOS：`printf '\n# rds-supabase-frontend:<项目名>\n<IP> <域名>\n' | sudo tee -a /etc/hosts`；Windows 管理员 PowerShell：`Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value '# rds-supabase-frontend:<项目名>','<IP> <域名>'`
4. **验证**：`GET http://<域名>/` 返回托管内容；OBS endpoint IP 变更时仅更新标记行。

局限：映射仅本机生效；非正式商用入口。转正式模式时按上文正式链路重走，下线时清理标记行并解绑自定义域名。

## 按路线绑定

**`obs-domain`（默认）**

1. 桶策略允许匿名读，否则静态网站托管与域名访问都取不到对象。
2. 开启静态网站托管，index document 与 error document 均取入口 HTML。这是全局回落，不是路径路由：`/login` 之类路径不会改写为独立资源，缺失资源也会回落首页。
3. 绑定自定义域名到该桶，记录返回的域名状态。
4. 需要路径级改写、负向路径 4xx 或 CDN 缓存时改用 `obs-cdn`，见 [域名与托管](hosting.md#托管路线)。

**`obs-cdn`**

1. 加速域名指向公开读桶的源站，回源协议与回源 Host 与实际桶一致。
2. 证书、HTTP 到 HTTPS 跳转、页面与缓存的改写规则配置在加速层。

两条路线都先查询后创建：已存在的域名绑定、DNS 记录、证书复用并核对差异，不覆盖共享字段。

## DNS

- **托管在华为云**：写入入口域名指向的 CNAME 或别名记录，先查现有记录、冲突和 TTL，保留无关记录；不拼接 CNAME，不用未经验证的 apex CNAME。
- **第三方 DNS**：不尝试对接第三方凭证，向用户输出精确的记录类型、主机记录、目标值和 TTL，并保持"入口未生效"状态。DNS 可继续保留现有服务商。

## 证书与 HTTPS

先 HTTP 上线，随后补 HTTPS；两者分别记录，不把 HTTP 结果当 HTTPS 通过。

1. 证书优先使用云侧签发的免费证书；用户已有证书时只负责绑定与域名匹配核对。
2. 绑定位置随路线：`obs-domain` 在存储侧的域名绑定上配置，`obs-cdn` 在加速层配置。
3. 私钥与含私钥的文件走官方安全配置或临时受限文件，不写入部署记录，不进入版本库。
4. 证书就位后把稳定入口切到 HTTPS，重新探测；证书未签发或域名不匹配期间，入口保持 HTTP 并标注未验证。

证书与域名的绑定命令名、字段和权限**尚未核实**，执行前按当前官方帮助确认；不以猜测的字段提交请求。

## 探测

目标固定为稳定入口的 `/`，方法 `GET`，跟随最多 5 次跳转，超时 30 秒，按实际协议发请求。

通过条件（全部满足）：

- 最终状态码为 2xx；
- `Content-Type` 为 HTML；
- `Content-Disposition` 缺失或不是 `attachment`；
- 正文含本版本的标记（构建注入的版本号、资源哈希或等价的版本指纹）；
- `access_mode` 为正常解析，不用 `--resolve`、改 Host 或跳过证书校验。

只探测 `/`。深层路由、静态资源、负向路径与 Supabase 登录单列，未执行即记未验证；`obs-domain` 下深层路径回落首页是预期行为，不能据此判负向路径通过。

探测通过时向用户返回：链接、状态码、最终 URL、命中的版本标记、托管路线、探测时间。不返回存储服务默认域名——它可能强制下载页面文件，只写入记录供排查。

探测通过不等于 [线上验收通过](deployment.md#真实验收)；HTTP 入口下 Supabase 登录可能因缺少安全上下文而不可用，登录项记未验证并提示补证书后复验。

## 失败原因枚举

失败或结果不确定时，按下列顺序逐项排除（前者排除后者），只记录最先命中的一项：

```text
icp_filing_missing
dns_not_hosted
domain_ownership_unverified
certificate_unavailable
dns_record_missing
cname_mismatch
bucket_policy_denies_anonymous
website_hosting_disabled
entry_object_missing
certificate_not_bound
cache_stale
cdn_deploying
dns_propagating
certificate_issuing
tls_handshake_timeout
```

判定与依据：

| 原因 | 依据 | 处理方 |
| --- | --- | --- |
| `icp_filing_missing` | 用户声明未备案，或云侧返回备案相关拒绝 | 用户 |
| `dns_not_hosted` | 根域名解析不在可写范围 | 用户 |
| `domain_ownership_unverified` | 归属或实名状态无法确认 | 用户 |
| `certificate_unavailable` | 无可用证书且无法签发 | 用户 |
| `dns_record_missing` | 入口域名无记录 | agent 可修复 |
| `cname_mismatch` | 记录指向与路线要求的 CNAME 不一致 | agent 可修复 |
| `bucket_policy_denies_anonymous` | 匿名 GET 桶内对象被拒绝 | agent 可修复 |
| `website_hosting_disabled` | 静态网站托管未开启 | agent 可修复 |
| `entry_object_missing` | 入口对象不存在或为空 | agent 可修复 |
| `certificate_not_bound` | 证书已签发但未绑定到该入口 | agent 可修复 |
| `cache_stale` | 加速层返回旧版本，内容哈希不符 | agent 可修复 |
| `cdn_deploying` | 域名处于部署中状态 | 等待 |
| `dns_propagating` | 记录已写入但解析尚未生效 | 等待 |
| `certificate_issuing` | 证书签发未完成 | 等待 |
| `tls_handshake_timeout` | TLS 握手超时或链路被拦截 | 等待 |

前四类为阻塞项，用户不处理后不会自行恢复；中间七类为可修复项，补配置后重新探测；最后四类为待生效项，只表示结果尚未确定。

记录映射：阻塞与可修复记 `failed`，待生效记 `unknown`；两类都不写成功版本字段，不写 `current_success_version`。

## 等待与续跑

同一环境串行执行。部署、解析与签发都是异步的：每次查询间隔 15 到 30 秒，总等待上限 30 分钟，超时保留域名、记录与证书的标识，标记结果未确定，再从查询恢复；不重复创建资源、不因一次超时改到其他区域。

## 失败后处置

不撤销已建资源。保留产物与已创建但未生效的资源，列出其标识、可能产生的费用和下一步动作，完成状态停在"环境已准备"，入口记为未可用。只有用户明确要求时才回收资源，并先确认回收不涉及共享 DNS、共享证书或其他项目引用的桶。

## 尚未核实

以下三项在文档中按待核实处理，不作为结论，执行前按当前官方帮助与真实账号确认：

1. 自定义域名与证书绑定是否可仅通过 KooCLI 或 obsutil 完成，还是必须走 SDK 或控制台。若不可自动化，本环节退化为输出控制台步骤，入口探测仍照常执行。
2. 华为云 DNS 记录写入的确切命令与字段。
3. 备案状态与实名状态是否可查询；无法查询时按用户声明记录，并注明该输入不来自 agent 验证。

# 内部云 OBS

从本机 OBS 配置的 endpoint 或已有 console URL 识别 `.ulanqab.huawei.com`；区域从该端点和发布记录推导，不套用公有云区域表。只读取 endpoint，不打印 AK/SK。配置冲突时先对账。

使用 `hcloud obs`，复用 `~/.obsutilconfig`，先看本机 `hcloud obs help` 确认支持的参数。内部云路径不运行需要公网下载服务列表的 KooCLI API 命令，也不做公网/代理连通性排查；内部区域对应的 `.myhuaweicloud.com` NXDOMAIN 不作为故障重试。

issue #6 的内部云实测发现 JS 默认 MIME 为 `application/x-javascript`；上传时显式规范化为 `application/javascript`（模块 JS 同样处理），CSS 为 `text/css`，HTML 为 `text/html`，同时设置 Cache-Control。以本环境实际 GET 为准。

默认域名可能强制下载，修正对象 MIME 或 Content-Disposition 不能保证解除平台限制。首次快照后即告知并索要真实入口域名；可并行准备获授权候选，真实域名未就绪时只报告候选状态。不可将内部云现象推广为所有 OBS 环境保证。

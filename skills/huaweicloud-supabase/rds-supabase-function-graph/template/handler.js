// FunctionGraph 零依赖样板入口（Node.js18）
// 契约：APIG 代理事件 -> {statusCode, headers, body}
// 本地自测：node handler.js < test-events/apig.json
"use strict";

const { verify } = require("./lib/jwt");
const { corsHeaders, isPreflight } = require("./lib/cors");
const { ok, fail, catchAll, applyCors } = require("./lib/response");
const { runIdempotent } = require("./lib/idempotency");

// ===== 业务段（按函数清单改写；样板组件不得删改） =====
async function business(event, ctx) {
  // event.body 已是对象（见下方 parseBody）
  // 幂等示例（交易类启用；config.json idempotency.enabled）：
  const result = await runIdempotent(event, ctx);
  if (result.replayed) return { replayed: true, request_id: ctx.requestId };
  // ... 领域逻辑 / 外部系统对接（签名密钥经 process.env.PARTNER_SIGN_KEY）...
  return { ok: true, request_id: ctx.requestId };
}

exports.handler = async (event) => {
  const requestId = header(event, "x-request-id") || crypto.randomUUID();
  const ctx = { requestId, env: process.env, body: parseBody(event) };
  const origin = header(event, "origin") || "";
  const cors = corsHeaders(origin, process.env.FGS_ALLOWED_ORIGINS);

  try {
    if (isPreflight(event)) {
      return { statusCode: 204, headers: { ...cors, Allow: "GET, POST, OPTIONS" }, body: "" };
    }
    if (!cors) return fail(403, "origin_forbidden", requestId); // 精确 origin 白名单之外

    const token = bearer(event);
    const auth = verify(token, process.env.FGS_JWT_SECRET);
    if (!auth.ok) return fail(401, auth.reason, requestId); // 验签红线：对外函数不得跳过

    const result = await business(event, ctx);
    return ok(result, cors);
  } catch (err) {
    return catchAll(err, requestId); // 500 只带 request_id；堆栈只进日志（LTS）
  }
};

// ===== 样板组件（不得删改） =====
function header(event, name) {
  const h = event && event.headers ? event.headers : {};
  const key = Object.keys(h).find((k) => k.toLowerCase() === name.toLowerCase());
  return key ? h[key] : undefined;
}
function bearer(event) {
  const a = header(event, "authorization") || "";
  return a.startsWith("Bearer ") ? a.slice(7) : "";
}
function parseBody(event) {
  if (!event || event.body === undefined || event.body === null) return {};
  if (typeof event.body === "object") return event.body;
  if (event.isBase64Encoded) return JSON.parse(Buffer.from(event.body, "base64").toString("utf8"));
  try { return JSON.parse(event.body); } catch { return {}; }
}

if (require.main === module) { // 本地事件回放
  let raw = "";
  process.stdin.on("data", (c) => (raw += c));
  process.stdin.on("end", async () => {
    const out = await exports.handler(JSON.parse(raw));
    console.log(JSON.stringify(out, null, 2));
  });
}

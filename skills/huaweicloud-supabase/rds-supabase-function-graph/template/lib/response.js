// 统一响应契约 + catch-all——样板组件，不得删改
// 契约：{statusCode, headers, body(字符串)}；500 只带 request_id，堆栈只进日志（LTS）
"use strict";

function ok(obj, extraHeaders) {
  return { statusCode: 200, headers: { "Content-Type": "application/json", ...(extraHeaders || {}) }, body: JSON.stringify(obj) };
}

function fail(status, code, requestId, extraHeaders) {
  return {
    statusCode: status,
    headers: { "Content-Type": "application/json", ...(extraHeaders || {}) },
    body: JSON.stringify({ error: code, request_id: requestId }),
  };
}

function catchAll(err, requestId) {
  console.error(JSON.stringify({ level: "error", request_id: requestId, message: String(err && err.message ? err.message : err) }));
  return fail(500, "internal_error", requestId);
}

module.exports = { ok, fail, catchAll };

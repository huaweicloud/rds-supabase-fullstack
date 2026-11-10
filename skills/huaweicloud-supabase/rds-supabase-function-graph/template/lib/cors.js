// 精确 origin 白名单——样板组件，不得删改（禁通配符 *）
"use strict";

function allowedList(csv) {
  return (csv || "").split(",").map((s) => s.trim().replace(/\/$/, "")).filter(Boolean);
}

// 返回允许的 CORS 头集合；origin 不在白名单时返回 null
function corsHeaders(origin, allowedCsv) {
  if (!origin) return null;
  const norm = origin.replace(/\/$/, "");
  if (!allowedList(allowedCsv).includes(norm)) return null;
  return {
    "Access-Control-Allow-Origin": norm,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Request-Id",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}

function isPreflight(event) {
  return (event && event.httpMethod === "OPTIONS") || false;
}

module.exports = { corsHeaders, isPreflight };

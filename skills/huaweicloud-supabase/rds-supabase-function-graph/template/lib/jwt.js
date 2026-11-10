// GoTrue JWT（HS256）零依赖验签——样板组件，不得删改
"use strict";
const crypto = require("node:crypto");

function b64urlDecode(s) {
  return Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8");
}

function verify(token, secret) {
  if (!token || typeof token !== "string") return { ok: false, reason: "missing_token" };
  if (!secret) return { ok: false, reason: "server_missing_secret" };
  const parts = token.split(".");
  if (parts.length !== 3) return { ok: false, reason: "malformed_token" };

  let header;
  try { header = JSON.parse(b64urlDecode(parts[0])); } catch { return { ok: false, reason: "malformed_header" }; }
  if (header.alg !== "HS256") return { ok: false, reason: "unsupported_alg" };

  const expected = crypto.createHmac("sha256", secret).update(`${parts[0]}.${parts[1]}`).digest();
  const actual = Buffer.from(parts[2].replace(/-/g, "+").replace(/_/g, "/"), "base64");
  if (expected.length !== actual.length || !crypto.timingSafeEqual(expected, actual)) {
    return { ok: false, reason: "bad_signature" };
  }

  let payload;
  try { payload = JSON.parse(b64urlDecode(parts[1])); } catch { return { ok: false, reason: "malformed_payload" }; }
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp !== undefined && now >= payload.exp) return { ok: false, reason: "token_expired" };
  if (payload.nbf !== undefined && now < payload.nbf) return { ok: false, reason: "token_not_yet_valid" };
  return { ok: true, payload };
}

module.exports = { verify };

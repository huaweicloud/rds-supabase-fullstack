// Kong 网关 REST 客户端（v1 唯一数据访问通道，免 VPC）——样板组件
"use strict";

// env：SUPABASE_URL（网关 https://...）、SUPABASE_SERVICE_ROLE_KEY
function headers() {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const url = process.env.SUPABASE_URL;
  if (!key || !url) throw new Error("supabase_env_missing");
  return {
    url: url.replace(/\/$/, ""),
    init: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
  };
}

// 幂等插入：冲突时静默忽略并返回 created=false（唯一约束即幂等键）
async function insertOnce(table, row, conflictColumns) {
  const { url, init } = headers();
  const cols = (conflictColumns || Object.keys(row)).join(",");
  const res = await fetch(`${url}/rest/v1/${table}?on_conflict=${encodeURIComponent(cols)}`, {
    method: "POST",
    headers: { ...init, Prefer: "resolution=ignore-duplicates,return=representation" },
    body: JSON.stringify(row),
  });
  if (!res.ok) throw new Error(`supabase_insert_${res.status}`);
  const rows = await res.json();
  return { created: Array.isArray(rows) && rows.length > 0 };
}

// RPC 调用（复用既有 Postgres 函数，权限走服务端）
async function callRpc(fn, args) {
  const { url, init } = headers();
  const res = await fetch(`${url}/rest/v1/rpc/${encodeURIComponent(fn)}`, {
    method: "POST",
    headers: init,
    body: JSON.stringify(args || {}),
  });
  if (!res.ok) throw new Error(`supabase_rpc_${res.status}`);
  return res.json();
}

module.exports = { insertOnce, callRpc };

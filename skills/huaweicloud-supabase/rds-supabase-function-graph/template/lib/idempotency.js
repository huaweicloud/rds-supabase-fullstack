// 幂等执行（unique 约束落库，防重放/重复投递）——样板组件
// 前提：幂等表已建（经 web-build 步骤五通道部署 DDL），形如
//   create table fn_<name>_idem (
//     request_id text primary key,
//     created_at timestamptz not null default now()
//   );
"use strict";
const { insertOnce } = require("./supabase");

// 依据 config.json 的 idempotency 配置执行；replayed=true 表示重复请求已处理过
async function runIdempotent(event, ctx) {
  if (process.env.FGS_IDEMPOTENCY_TABLE === "disabled") return { replayed: false };
  const table = process.env.FGS_IDEMPOTENCY_TABLE; // 例：fn_notify_transaction_idem
  if (!table) throw new Error("idempotency_table_missing");
  const key = ctx.body[process.env.FGS_IDEMPOTENCY_KEY_FIELD || "request_id"] || ctx.requestId;
  const { created } = await insertOnce(table, { request_id: key }, ["request_id"]);
  return { replayed: !created };
}

module.exports = { runIdempotent };

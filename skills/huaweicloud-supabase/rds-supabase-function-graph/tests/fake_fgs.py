#!/usr/bin/env python3
"""Local fake APIG + function endpoint for fgs-gate tests.

Stands in for a deployed shared-APIG trigger URL. Mirrors the template's
security behavior so the gate can be exercised end-to-end without cloud
access:

  OPTIONS            -> 204 + exact-origin CORS headers
  valid Bearer JWT   -> 200 {"ok": true}
  missing/invalid    -> 401
  path /broken-open  -> 200 regardless of auth (a function that forgot its
                        auth gate — the gate must flag this)
  env FGS_FAKE_BAD_CORS=1 -> preflight lacks Access-Control-Allow-Origin

Usage: python3 fake_fgs.py --jwt <token> --origin <origin> [--port 0]
Prints the bound port on stdout, then serves until killed.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def make_handler(jwt: str, allowed_origin: str) -> type:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence stderr noise
            pass

        def _reply(self, status: int, body: dict, headers: dict | None = None):
            payload = json.dumps(body).encode()
            self.send_response(status)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _cors(self) -> dict:
            if os.environ.get("FGS_FAKE_BAD_CORS") == "1":
                return {}
            if self.headers.get("Origin", "") == allowed_origin:
                return {
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Request-Id",
                    "Access-Control-Max-Age": "600",
                }
            return {}

        def do_OPTIONS(self):
            self._reply(204, {}, self._cors())

        def do_POST(self):
            if self.path.startswith("/broken-open"):
                self._reply(200, {"ok": True, "broken": True}, self._cors())
                return
            origin = self.headers.get("Origin", "")
            if origin and origin != allowed_origin:
                self._reply(403, {"error": "origin_forbidden", "request_id": "fake-1"}, {})
                return
            auth = self.headers.get("Authorization", "")
            cors = self._cors()
            if auth == f"Bearer {jwt}":
                self._reply(200, {"ok": True, "request_id": "fake-1"}, cors)
            else:
                self._reply(401, {"error": "missing_token", "request_id": "fake-1"}, cors)

        do_GET = do_POST

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jwt", required=True)
    ap.add_argument("--origin", required=True)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.jwt, args.origin))
    print(server.server_address[1], flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

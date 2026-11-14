"""Explicit RDS API transport. No redirects or automatic retries."""
import asyncio
import http.client
import json
import os
import re
from urllib.parse import urlsplit, urlencode
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.failures import http_failure, RecoveryError


def segment(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise McpToolError("MCP_INVALID_ARGS", "Invalid resource identifier")
    return value


def error_detail(raw):
    """Parse a backend error body (bytes/str) into a bounded detail dict, or None."""
    try:
        parsed = json.loads(raw) if raw else {}
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    source = parsed.get("error") if isinstance(parsed.get("error"), dict) else parsed
    detail = {k: str(source[k])[:300] for k in ("error_code", "error_msg", "code", "message", "request_id")
              if isinstance(source.get(k), (str, int))}
    return detail or None


def resolve_endpoint(explicit=None):
    """Endpoint resolution follows the GaussDB MCP convention: an explicit
    SUPABASE_RDS_ENDPOINT override wins; otherwise the standard regional RDS
    origin is derived from HUAWEICLOUD_REGION."""
    if explicit:
        return explicit
    override = os.getenv("SUPABASE_RDS_ENDPOINT", "").strip()
    if override:
        return override
    region = os.getenv("HUAWEICLOUD_REGION", "").strip()
    if region:
        return f"https://rds.{region}.myhuaweicloud.com"
    return ""


class RestClient:
    def __init__(self, endpoint=None, project=None, token=None, allow_loopback=False):
        self.endpoint = resolve_endpoint(endpoint)
        self.project = project or os.getenv("HUAWEICLOUD_PROJECT_ID", "")
        self.token = token
        self.allow_loopback = allow_loopback

    async def request(self, method, path, body=None, query=None, headers=None):
        return await asyncio.to_thread(self._request, method, path, body, query, headers)

    def _request(self, method, path, body, query, headers):
        url = urlsplit(self.endpoint)
        local = self.allow_loopback and url.hostname in ("127.0.0.1", "localhost")
        if (url.scheme != "https" and not (local and url.scheme == "http")) or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise McpToolError("MCP_INVALID_ARGS", "Configure a trusted HTTPS RDS origin without path or credentials")
        token = self.token if self.token is not None else os.getenv("HUAWEICLOUD_AUTH_TOKEN", "")
        if not token or any(x in token for x in ("\r", "\n")):
            raise McpToolError("MCP_PERMISSION_DENIED", "Missing or invalid auth token")
        route = path.replace("{project}", segment(self.project)) if "{project}" in path else path
        if query:
            route += "?" + urlencode(query, doseq=True)
        request_headers = {"X-Auth-Token": token, "Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        connection = (http.client.HTTPConnection if local and url.scheme == "http" else http.client.HTTPSConnection)(url.hostname, url.port, timeout=30)
        try:
            connection.request(method, route, None if body is None else json.dumps(body), request_headers)
            response = connection.getresponse()
            raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError("oversized")
            if not 200 <= response.status < 300:
                # Surface the backend error body instead of dropping it: the agent
                # needs error_code/error_msg to repair the request.
                raise http_failure(response.status, error_detail(raw))
            value = json.loads(raw) if raw else {}
            if not isinstance(value, dict):
                raise ValueError("response shape")
            return response.status, value
        except McpToolError:
            raise
        except Exception:
            raise RecoveryError("MCP_SDK_ERROR", "Request result unavailable", "transport_or_response", "Verify connectivity and response contract. Reconcile any submitted write before retrying.") from None
        finally:
            connection.close()

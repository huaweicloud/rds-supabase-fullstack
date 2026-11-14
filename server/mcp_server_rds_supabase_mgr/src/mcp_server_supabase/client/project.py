"""Project-id resolution following the GaussDB MCP convention.

An explicit HUAWEICLOUD_PROJECT_ID short-circuits with zero network calls;
otherwise the regional project is discovered once via IAM
KeystoneListProjects(name=region) using global credentials, cached per
(ak, sk, token, region) so credential rotation invalidates the cache.
"""
import os
import threading

from huaweicloud_mcp_core.errors import McpToolError

_CACHE_LOCK = threading.Lock()
_PROJECT_CACHE: dict[tuple, str] = {}

IAM_ENDPOINT = os.getenv("HUAWEICLOUD_IAM_ENDPOINT", "https://iam.myhuaweicloud.com")


def _cache_key():
    return (os.getenv("HUAWEICLOUD_ACCESS_KEY", ""), os.getenv("HUAWEICLOUD_SECRET_KEY", ""),
            os.getenv("HUAWEICLOUD_SECURITY_TOKEN", ""), os.getenv("HUAWEICLOUD_REGION", ""))


def resolve_project_id():
    """Explicit HUAWEICLOUD_PROJECT_ID wins; otherwise discover once via IAM.

    Lazy contract: when neither HUAWEICLOUD_PROJECT_ID nor HUAWEICLOUD_REGION
    is configured, returns '' instead of raising - clients surface the
    actionable error at request time, keeping construction side-effect free.
    """
    explicit = os.getenv("HUAWEICLOUD_PROJECT_ID", "").strip()
    if explicit:
        return explicit
    region = os.getenv("HUAWEICLOUD_REGION", "").strip()
    if not region:
        return ""
    key = _cache_key()
    with _CACHE_LOCK:
        cached = _PROJECT_CACHE.get(key)
    if cached:
        return cached
    ak = os.getenv("HUAWEICLOUD_ACCESS_KEY", "")
    sk = os.getenv("HUAWEICLOUD_SECRET_KEY", "")
    if not ak or not sk or any(c in v for v in (ak, sk) for c in ("\r", "\n")):
        return ""
    try:
        from huaweicloudsdkcore.http.http_config import HttpConfig
        from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        credentials = GlobalCredentials().with_ak(ak).with_sk(sk)
        token = os.getenv("HUAWEICLOUD_SECURITY_TOKEN", "")
        if token:
            credentials = credentials.with_security_token(token)
        client = (IamClient.new_builder()
                  .with_credentials(credentials)
                  .with_endpoint(IAM_ENDPOINT)
                  .with_http_config(HttpConfig(timeout=(10, 30), retry_times=0))
                  .build())
        response = client.keystone_list_projects(KeystoneListProjectsRequest(name=region))
    except Exception as exc:
        raise McpToolError("MCP_SDK_ERROR",
                           f"Failed to resolve project_id for region '{region}' via IAM: {exc}",
                           hint="Set HUAWEICLOUD_PROJECT_ID explicitly, or check the AK/SK and its IAM project-list permission.") from exc
    projects = getattr(response, "projects", None) or []
    for project in projects:
        if getattr(project, "name", None) == region and getattr(project, "id", None):
            pid = str(project.id)
            with _CACHE_LOCK:
                _PROJECT_CACHE[key] = pid
            return pid
    raise McpToolError("MCP_NOT_FOUND", f"No project found for region '{region}'",
                       hint="Set HUAWEICLOUD_PROJECT_ID explicitly; sub-project accounts are not discoverable by region name.")


def reset_project_cache():
    with _CACHE_LOCK:
        _PROJECT_CACHE.clear()

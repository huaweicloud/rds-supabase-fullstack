"""SDK Core signed transport for confirmed contracts, not generated Supabase models."""
import asyncio
import hashlib
import json
import logging
import os
from urllib.parse import urlsplit
from huaweicloudsdkcore.client import Client, ClientBuilder
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkcore.sdk_response import SdkResponse
from huaweicloudsdkcore.exceptions.exceptions import ServiceResponseException
from huaweicloud_mcp_core.errors import McpToolError
from mcp_server_supabase.failures import http_failure, RecoveryError
from mcp_server_supabase.client.rest import segment, error_detail, resolve_endpoint


class QuietSdkClient(Client):
    @classmethod
    def _init_logger(cls):
        # Isolated logger: SDK transport exceptions can contain resource URLs.
        # Tool-level sanitized recovery and shared audit remain available.
        logger = logging.Logger('supabase-sdk-transport')
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        return logger


class WireResponse(SdkResponse):
    openapi_types = {}
    attribute_map = {}


class SdkCoreClient:
    def __init__(self, endpoint=None, project=None, ak=None, sk=None, security_token=None, allow_loopback=False):
        self.endpoint=resolve_endpoint(endpoint)
        self.project=project or os.getenv('HUAWEICLOUD_PROJECT_ID','')
        self._ak=ak if ak is not None else os.getenv('HUAWEICLOUD_ACCESS_KEY','')
        self._sk=sk if sk is not None else os.getenv('HUAWEICLOUD_SECRET_KEY','')
        self._security_token=security_token if security_token is not None else os.getenv('HUAWEICLOUD_SECURITY_TOKEN','')
        self.allow_loopback=allow_loopback
        # Existing plan interface binds this opaque identity snapshot, never the raw secrets.
        self.token=hashlib.sha256(json.dumps(['sdk_core',self._ak,self._sk,self._security_token]).encode()).hexdigest()

    async def request(self, method, path, body=None, query=None, headers=None):
        return await asyncio.to_thread(self._request,method,path,body,query,headers)

    def _request(self, method, path, body, query, headers):
        sdk=None
        try:
            url=urlsplit(self.endpoint)
            local=self.allow_loopback and url.hostname in ('127.0.0.1','localhost')
            if not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/') or not (url.scheme=='https' or local and url.scheme=='http'):
                raise McpToolError('MCP_INVALID_ARGS','Configure a verified HTTPS service origin',
                                   hint='Set SUPABASE_RDS_ENDPOINT explicitly, or set HUAWEICLOUD_REGION so the standard RDS origin can be derived.')
            if not self._ak or not self._sk or any(c in v for v in (self._ak,self._sk,self._security_token) for c in ('\r','\n')):
                raise McpToolError('MCP_PERMISSION_DENIED','Missing or invalid SDK credentials')
            # Project-scoped signing only for service paths carrying the placeholder;
            # placeholder-free paths (e.g. IAM global queries) sign at domain scope.
            route = path.replace('{project}', segment(self.project)) if '{project}' in path else path
            project_id = segment(self.project) if '{project}' in path else (self.project or None)
            credentials=BasicCredentials(self._ak,self._sk,project_id)
            if self._security_token:credentials.with_security_token(self._security_token)
            config=HttpConfig(timeout=(10,30),retry_times=0,allow_redirects=False)
            sdk=ClientBuilder(QuietSdkClient).with_credentials(credentials).with_endpoint(self.endpoint).with_http_config(config).build()
            request_headers={'Content-Type':'application/json'}
            if headers:request_headers.update(headers)
            response=sdk.do_http_request(method,route,
                query_params=list((query or {}).items()),header_params=request_headers,
                body=body,response_type=WireResponse)
            if not 200 <= response.status_code < 300:
                # Surface the backend error body instead of dropping it: the agent
                # needs error_code/error_msg to repair the request.
                raise http_failure(response.status_code, error_detail(response.raw_content))
            raw=response.raw_content or b'{}'
            if len(raw)>1048576:raise ValueError('response size')
            data=json.loads(raw)
            if not isinstance(data,dict):raise ValueError('response shape')
            return response.status_code,data
        except McpToolError:
            raise
        except ServiceResponseException as exc:
            # SDK-raised service errors carry error_code/error_msg/request_id;
            # pass them through for diagnosis instead of a bare status code.
            detail={k: str(v)[:300] for k, v in (('error_code',exc.error_code),
                                                 ('error_msg',exc.error_msg),
                                                 ('request_id',exc.request_id)) if v}
            raise http_failure(exc.status_code, detail) from None
        except Exception:
            raise RecoveryError('MCP_SDK_ERROR','SDK request result unavailable','transport_or_response',
                                'Verify SDK configuration and response contract; reconcile submitted writes before retrying.') from None
        finally:
            if sdk is not None:sdk.close()


def configured_client():
    mode=os.getenv('SUPABASE_TRANSPORT','rest')
    if mode=='sdk_core':return SdkCoreClient()
    if mode=='rest':
        from mcp_server_supabase.client.rest import RestClient
        return RestClient()
    raise McpToolError('MCP_INVALID_ARGS','Unsupported SUPABASE_TRANSPORT; use rest or sdk_core')

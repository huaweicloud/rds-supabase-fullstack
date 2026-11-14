"""BSS customer-order SDK channel for prepaid order query, payment and cancellation.

Wire contract verified against huaweicloudsdkbss 3.1.220 and the GaussDB MCP
reference implementation (client/bss_client.py of huaweicloud-gaussdb-mcp,
gaussdb-integration branch): global credentials, shared BSS endpoint,
retry_times=0 so an ambiguous payment failure is never retried automatically.
"""
import asyncio
import os
from typing import Any, cast

from huaweicloud_mcp_core import (
    CredentialScope,
    McpSettings,
    McpToolError,
    build_credentials,
    wrap_sdk_error,
)

_BSS_HINT = (
    "Check the customer account, BSS endpoint and billing permissions. "
    "Order details require billing:order:view; payment requires billing:order:pay. "
    "Cancellation also needs the applicable BSS order-update permission under your "
    "authorization model. Only pending-payment orders can be paid or cancelled. "
    "Query the order tool before retrying."
)

_WRITE_UNKNOWN_STATUSES = {502, 503, 504}
_WRITE_UNKNOWN_TYPES = {
    "ConnectionException",
    "ReadTimeout",
    "ConnectTimeout",
    "CallTimeoutException",
    "RequestTimeoutException",
    "HostUnreachableException",
}


def _sdk_to_dict(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(key): _sdk_to_dict(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sdk_to_dict(item) for item in obj]
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return _sdk_to_dict(to_dict())
    if hasattr(obj, "__dict__"):
        return {str(key): _sdk_to_dict(value) for key, value in obj.__dict__.items()}
    return obj


def _write_result_unknown(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) in _WRITE_UNKNOWN_STATUSES:
        return True
    return any(
        isinstance(error, (TimeoutError, ConnectionError))
        or type(error).__name__ in _WRITE_UNKNOWN_TYPES
        for error in (exc, exc.__cause__)
    )


class BssOrderClient:
    """Thin asynchronous SDK wrapper for customer billing order APIs."""

    def __init__(self, settings: McpSettings | None = None, sdk_client: Any = None) -> None:
        self._settings = settings or McpSettings.from_env()
        self._client = sdk_client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from huaweicloudsdkbss.v2 import BssClient
        from huaweicloudsdkcore.http.http_config import HttpConfig

        config = HttpConfig.get_default_config()
        config.timeout = (10, 30)
        # Payment submission must never be retried automatically after an ambiguous failure.
        config.retry_times = 0
        self._client = (
            BssClient.new_builder()
            .with_credentials(build_credentials(CredentialScope.GLOBAL, self._settings))
            .with_endpoint(os.getenv("HUAWEICLOUD_BSS_ENDPOINT") or "https://bss.myhuaweicloud.com")
            .with_http_config(config)
            .build()
        )
        return self._client

    async def _call(self, method: str, request: Any) -> dict[str, Any]:
        read_only = method == "show_customer_order_details"

        def invoke() -> dict[str, Any]:
            try:
                return cast(dict[str, Any], _sdk_to_dict(getattr(self._get_client(), method)(request)))
            except Exception as exc:
                if not read_only and _write_result_unknown(exc):
                    raise McpToolError(
                        "MCP_WRITE_RESULT_UNKNOWN",
                        "The cloud write may have been accepted.",
                        request_id=getattr(exc, "request_id", None),
                        hint="Query the order before submitting again; never blindly repeat a payment or cancellation.",
                    ) from exc
                wrapped = wrap_sdk_error(exc)
                raise McpToolError(
                    wrapped.code,
                    wrapped.message,
                    request_id=wrapped.request_id,
                    hint=_BSS_HINT,
                ) from exc

        return await asyncio.to_thread(invoke)

    async def get_order(self, *, order_id: str, limit: int, offset: int) -> dict[str, Any]:
        from huaweicloudsdkbss.v2 import ShowCustomerOrderDetailsRequest

        return await self._call(
            "show_customer_order_details",
            ShowCustomerOrderDetailsRequest(
                x_language="zh_CN", order_id=order_id, limit=limit, offset=offset
            ),
        )

    async def cancel_order(self, *, order_id: str) -> dict[str, Any]:
        from huaweicloudsdkbss.v2 import CancelCustomerOrderReq, CancelCustomerOrderRequest

        return await self._call(
            "cancel_customer_order",
            CancelCustomerOrderRequest(body=CancelCustomerOrderReq(order_id=order_id)),
        )

    async def pay_order(self, *, order_id: str) -> dict[str, Any]:
        from huaweicloudsdkbss.v2 import PayCustomerOrderV3Req, PayOrdersRequest

        return await self._call(
            "pay_orders",
            PayOrdersRequest(
                body=PayCustomerOrderV3Req(
                    order_id=order_id,
                    use_coupon="NO",
                    use_discount="NO",
                )
            ),
        )

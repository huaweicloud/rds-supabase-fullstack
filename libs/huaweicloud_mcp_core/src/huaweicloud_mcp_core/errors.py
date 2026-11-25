# Copyright (c) 2026 Huawei Technologies Co., Ltd.
# SPDX-License-Identifier: MIT

"""Unified error model for Huawei Cloud MCP tools."""

from __future__ import annotations

import re
from typing import Any

_INTERNAL_CODES = {
    "MCP_INVALID_ARGS",
    "MCP_NOT_FOUND",
    "MCP_PERMISSION_DENIED",
    "MCP_READ_ONLY",
    "MCP_GUARDRAIL_BLOCKED",
    "MCP_GUARDRAIL_ERROR",
    "MCP_SDK_ERROR",
    "MCP_PROJECT_NOT_FOUND",
    "MCP_CALL_TIMEOUT",
}

#: IAM/APIGW auth failures embed the full canonical_request (signed headers,
#: user-agent, SDK date, payload hash) into error_msg - hundreds of characters
#: of signature plumbing that an Agent consumer cannot act on and that pollute
#: its context budget on every retry. Keep the actionable prefix, drop the rest.
_CANONICAL_REQUEST_RE = re.compile(
    r"\s*canonical_request:\S.*?(?=,\s*encoded_authorization_message:|$)", re.DOTALL
)


def _trim_error_message(message: str) -> str:
    if "canonical_request:" in message:
        message = _CANONICAL_REQUEST_RE.sub(" (canonical request elided)", message)
    return message


class McpToolError(Exception):
    """The only business exception tools are allowed to raise."""

    def __init__(
        self,
        code: str,
        message: str,
        request_id: str | None = None,
        doc_url: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.doc_url = doc_url
        self.hint = hint

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.request_id:
            error["request_id"] = self.request_id
        if self.doc_url:
            error["doc_url"] = self.doc_url
        error["hint"] = self.hint or "Inspect the error message and adjust the tool call."
        return {"error": error}


def wrap_sdk_error(exc: Exception) -> McpToolError:
    """Convert huaweicloudsdk exceptions into McpToolError with full context."""
    try:
        from huaweicloudsdkcore.exceptions.exceptions import (
            ClientRequestException,
            ServiceResponseException,
        )
    except ImportError:
        return McpToolError("MCP_SDK_ERROR", str(exc))

    if isinstance(exc, ServiceResponseException):
        return McpToolError(
            code=getattr(exc, "error_code", None) or f"HTTP_{exc.status_code}",
            message=_trim_error_message(str(getattr(exc, "error_msg", None) or exc)),
            request_id=getattr(exc, "request_id", None),
        )
    if isinstance(exc, ClientRequestException):
        return McpToolError(
            code=f"HTTP_{exc.status_code}",
            message=_trim_error_message(str(exc)),
            request_id=getattr(exc, "request_id", None),
        )
    return McpToolError("MCP_SDK_ERROR", _trim_error_message(str(exc)))

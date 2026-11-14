"""Prepaid order lifecycle for RDS Supabase applications: query, guarded payment, cancellation.

Defense chain ported from the GaussDB MCP reference implementation (service/
billing_service.py, huaweicloud-gaussdb-mcp gaussdb-integration): product-scope
checks across the main order, sub-orders and every line item on every page;
amount/currency re-approval on any drift; a final refresh immediately before
the single payment submission; payment_time as a second already-paid guard.
Adapted to this server's conventions: the one-use plan ledger binds
(order_id, expected_amount, currency, endpoint, credential) so previews
expire and submissions cannot be replayed; the read-only and write-enable
gates apply; ambiguous submission failures surface as RecoveryError with the
plan id.
"""
import asyncio
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from huaweicloud_mcp_core import McpToolError
from huaweicloud_mcp_core.guardrails.protect import assert_not_protected

from mcp_server_supabase.client.bss_client import BssOrderClient
from mcp_server_supabase.failures import RecoveryError
from mcp_server_supabase.service.plans import PlanStore, fingerprint

# The service_type_code carried by RDS Supabase prepaid orders. The default is
# the documented RDS code; real orders may carry a Supabase-specific code -
# set SUPABASE_ORDER_SERVICE_TYPE from a live order's raw response if scope
# checks reject a genuine order.
_ORDER_SERVICE_TYPE = os.getenv("SUPABASE_ORDER_SERVICE_TYPE") or "hws.service.type.rds"
_ORDER_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_AMOUNT = re.compile(r"[0-9]{1,16}(?:\.[0-9]{1,8})?\Z")
_CURRENCY = re.compile(r"[A-Z]{3}\Z")
_PAYMENT_LOCK = asyncio.Lock()
_ORDER_FIELDS = (
    "order_id",
    "service_type_code",
    "service_type_name",
    "status",
    "order_type",
    "official_amount",
    "amount_after_discount",
    "measure_id",
    "currency",
    "create_time",
    "payment_time",
    "pending_payment_end_time",
)
_ITEM_FIELDS = (
    "order_line_item_id",
    "order_id",
    "service_type_code",
    "service_type_name",
    "product_id",
    "product_spec_desc",
    "period_type",
    "period_num",
    "subscription_num",
    "effective_time",
    "expire_time",
    "official_amount",
    "amount_after_discount",
    "currency",
)
_STATUSES = {
    1: "pending_review",
    2: "pending_refund",
    3: "processing",
    4: "cancelled",
    5: "completed",
    6: "pending_payment",
    9: "pending_confirmation",
    10: "pending_delivery",
    11: "pending_receipt",
    12: "pending_pickup",
    13: "replacement_in_progress",
}


def _invalid(message: str) -> McpToolError:
    return McpToolError("MCP_INVALID_ARGS", message, hint="Use the order_id returned by create_supabase_application.")


def _validate_id(order_id: str) -> None:
    if not isinstance(order_id, str) or not _ORDER_ID.fullmatch(order_id):
        raise _invalid("order_id must contain 1-64 letters, digits, underscores or hyphens.")


def _scope_error() -> McpToolError:
    return McpToolError(
        "MCP_INVALID_ARGS",
        "This tool only handles RDS Supabase orders; other or mixed-product orders are rejected.",
        hint="Verify the order_id in the billing console. Use the console for other orders. "
        "If a genuine Supabase order is rejected, set SUPABASE_ORDER_SERVICE_TYPE to the "
        "service_type_code shown in the billing console and restart.",
    )


def _in_scope(code: Any) -> bool:
    return isinstance(code, str) and {part.strip() for part in code.split(",")} == {_ORDER_SERVICE_TYPE}


def _order_info(response: dict[str, Any], order_id: str) -> dict[str, Any]:
    info = response.get("order_info")
    if not isinstance(info, dict) or info.get("order_id") != order_id:
        raise McpToolError(
            "MCP_SDK_ERROR",
            "BSS returned missing or mismatched order details.",
            hint="Verify the order in the billing console before retrying.",
        )
    if not _in_scope(info.get("service_type_code")):
        raise _scope_error()
    children = info.get("sub_order_infos") or []
    if not isinstance(children, list) or any(
        not isinstance(child, dict) or not _in_scope(child.get("service_type_code")) for child in children
    ):
        raise _scope_error()
    return info


def _items(response: dict[str, Any]) -> list[dict[str, Any]]:
    items = response.get("order_line_items") or []
    if not isinstance(items, list) or any(
        not isinstance(item, dict) or not _in_scope(item.get("service_type_code")) for item in items
    ):
        raise _scope_error()
    return items


def _summary(info: dict[str, Any]) -> dict[str, Any]:
    result = {key: info[key] for key in _ORDER_FIELDS if key in info}
    status = info.get("status")
    result["status_name"] = _STATUSES.get(status, "unknown") if type(status) is int else "unknown"
    result["sub_order_infos"] = [
        {key: child[key] for key in _ORDER_FIELDS if key in child}
        for child in info.get("sub_order_infos") or []
    ]
    return result


def _require_unpaid(info: dict[str, Any], action: str = "cancelled") -> None:
    if type(info.get("status")) is not int or info["status"] != 6 or info.get("payment_time"):
        raise McpToolError(
            "MCP_INVALID_ARGS",
            f"Only an unpaid pending-payment order can be {action}.",
            hint="Call the order query tool to inspect the latest status. Paid resources "
            "require the separate unsubscription workflow; this tool never unsubscribes "
            "or deletes resources.",
        )


def _check_protection(info: dict[str, Any], items: list[dict[str, Any]], tool_name: str) -> None:
    order_ids = {info["order_id"]}
    order_ids.update(child["order_id"] for child in info.get("sub_order_infos") or [] if child.get("order_id"))
    order_ids.update(item["order_id"] for item in items if item.get("order_id"))
    for order_id in order_ids:
        assert_not_protected({"id": order_id, "name": order_id}, tool_name=tool_name)


def _money(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise _invalid("Payment amount must be a finite, nonnegative decimal value.")
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise _invalid("Payment amount must be a finite, nonnegative decimal value.") from None
    if not amount.is_finite() or amount < 0:
        raise _invalid("Payment amount must be a finite, nonnegative decimal value.")
    return amount


def _check_payment_amount(info: dict[str, Any], amount: Decimal, currency: str) -> None:
    _require_unpaid(info, "paid")
    if info.get("currency") != currency or _money(info.get("official_amount")) != amount:
        raise _invalid(
            "Order amount or currency differs from the approved values. Query the order and obtain approval again."
        )
    # Balance payment (use_coupon/use_discount = NO) must not silently discard a discount.
    if _money(info.get("amount_after_discount")) != amount:
        raise _invalid(
            "This order has a discount. Use the billing console to select and verify "
            "discounts/coupons; this balance-payment tool will not pay the higher list price."
        )


def _writes_enabled() -> None:
    if os.getenv("SUPABASE_ENABLE_WRITES") != "true" or os.getenv("HUAWEICLOUD_MCP_READ_ONLY", "false").lower() == "true":
        raise McpToolError("MCP_READ_ONLY", "Writes are disabled")


class BillingOperations:
    def __init__(self, bss: BssOrderClient | None = None, plans: PlanStore | None = None) -> None:
        self._bss = bss
        self.plans = plans or PlanStore()

    def _client(self) -> BssOrderClient:
        if self._bss is None:
            self._bss = BssOrderClient()
        return self._bss

    def _digest(self, order_id: str, expected_amount: str, currency: str) -> str:
        return fingerprint({"endpoint": "https://bss.myhuaweicloud.com", "credential": os.getenv("HUAWEICLOUD_ACCESS_KEY", ""),
                            "action": "pay_order", "order_id": order_id,
                            "expected_amount": expected_amount, "currency": currency})

    async def get_order(self, *, order_id: str, limit: int = 20, marker: str | None = None) -> dict[str, Any]:
        _validate_id(order_id)
        if marker is not None and (
            not isinstance(marker, str) or not re.fullmatch(r"[0-9]{1,10}", marker) or int(marker) > 2147483647
        ):
            raise _invalid("marker must be an offset returned by the previous order query.")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise _invalid("limit must be an integer from 1 to 100.")
        offset = int(marker or 0)
        response = await self._client().get_order(order_id=order_id, limit=limit, offset=offset)
        info, items = _order_info(response, order_id), _items(response)
        total = response.get("total_count")
        next_marker = (
            str(offset + len(items))
            if items and (offset + len(items) < total if isinstance(total, int) else len(items) == limit)
            else None
        )
        return {
            "data": [{key: item[key] for key in _ITEM_FIELDS if key in item} for item in items],
            "total_count": total, "marker": next_marker, "order": _summary(info),
            "note": "amount_after_discount excludes coupon/card deductions; keep the returned "
                    "currency and measure_id. An unpaid order does not mean the application or "
                    "instance has been provisioned.",
            "hints": ["Pay only after approval for the exact order, amount and currency.",
                      "The RDS Supabase application itself is free during public beta; prepaid "
                      "charges apply to the managed PostgreSQL instance."],
        }

    async def pay_order(
        self, *, order_id: str, expected_amount: str, currency: str, confirm: bool = False, plan_id: str | None = None
    ) -> dict[str, Any]:
        _validate_id(order_id)
        if not isinstance(expected_amount, str) or not _AMOUNT.fullmatch(expected_amount):
            raise _invalid("expected_amount must be a decimal string, for example '1248.00'.")
        amount = _money(expected_amount)
        if not isinstance(currency, str) or not _CURRENCY.fullmatch(currency):
            raise _invalid("currency must be the three-letter currency returned by the order query.")
        digest = self._digest(order_id, expected_amount, currency)
        async with _PAYMENT_LOCK:
            response = await self._client().get_order(order_id=order_id, limit=100, offset=0)
            info = _order_info(response, order_id)
            already_paid = info.get("status") in {3, 5}
            if not already_paid:
                _check_payment_amount(info, amount, currency)
            items = _items(response)
            _check_protection(info, items, "pay_supabase_order")
            total = response.get("total_count")
            if type(total) is not int or not 1 <= total <= 1000 or not items or len(items) > total:
                raise _invalid("Cannot verify all order lines within the 1000-line payment limit.")
            offset = len(items)
            while offset < total:
                page = await self._client().get_order(order_id=order_id, limit=100, offset=offset)
                current = _order_info(page, order_id)
                if not already_paid:
                    _check_payment_amount(current, amount, currency)
                chunk = _items(page)
                _check_protection(current, chunk, "pay_supabase_order")
                if page.get("total_count") != total or not chunk or offset + len(chunk) > total:
                    raise _invalid("Order changed or pagination was incomplete; payment stopped.")
                offset += len(chunk)
            if confirm is not True:
                return {"confirmation_required": True, "execution": "not_executed",
                        "order": _summary(info), "expected_amount": expected_amount, "currency": currency,
                        "order_amount_matches_approval": not already_paid,
                        "message": "Authorize this exact order, amount and currency, then call again with confirm=true and the plan_id.",
                        "plan_id": None, **self.plans.issue(digest)}
            if already_paid:
                # Someone paid between preview and confirm: refuse to submit again.
                return {
                    "order": _summary(info),
                    "payment_submitted": False,
                    "payment_verified": bool(info.get("payment_time")),
                    "already_processed": True,
                    "plan_id": None,
                    "warnings": ["This order is already processing or completed. Do not pay again; "
                                 "query the order and the application to verify provisioning."],
                }
            _writes_enabled()
            self.plans.claim(plan_id, digest)
            unknown = RecoveryError("MCP_SDK_ERROR", "Payment submission result unknown", "submission_unknown",
                                    "Query the order before any further payment attempt; never blindly repeat a payment.", plan_id)
            try:
                # Final refresh immediately before the single payment submission.
                latest = await self._client().get_order(order_id=order_id, limit=1, offset=0)
                current = _order_info(latest, order_id)
                _check_payment_amount(current, amount, currency)
                _check_protection(current, _items(latest), "pay_supabase_order")
                if latest.get("total_count") != total:
                    raise _invalid("Order lines changed before payment; obtain approval again.")
                await self._client().pay_order(order_id=order_id)
            except RecoveryError as error:
                if error.recovery.get("category") in ("invalid_request", "authentication", "permission", "not_found", "state_conflict"):
                    self.plans.finish(plan_id, "failed"); raise
                self.plans.finish(plan_id, "unknown"); raise
            except McpToolError:
                self.plans.finish(plan_id, "failed"); raise
            except BaseException:
                self.plans.finish(plan_id, "unknown"); raise unknown from None
            self.plans.finish(plan_id, "accepted")
            result: dict[str, Any] = {
                "order_id": order_id, "expected_amount": expected_amount, "currency": currency,
                "payment_submitted": True, "payment_verified": False, "plan_id": plan_id,
                "completion_verified": False,
            }
            try:
                checked = _order_info(await self._client().get_order(order_id=order_id, limit=1, offset=0), order_id)
                result["order"] = _summary(checked)
                result["payment_verified"] = checked.get("status") in {3, 5} and bool(checked.get("payment_time"))
                result["order_amount_matches_approval"] = (
                    checked.get("currency") == currency
                    and _money(checked.get("amount_after_discount")) == amount
                    and _money(checked.get("official_amount")) == amount
                )
                if not result["order_amount_matches_approval"]:
                    result["warnings"] = ["BSS order amounts differ from the approved values. Inspect billing "
                                          "details; this tool does not automatically refund or pay again."]
            except McpToolError as exc:
                result["verification_error"] = exc.to_dict()["error"]
            return {**result,
                    "follow_up": "Payment submission is not instance readiness. Track the order to terminal "
                                 "state and query the application/instance after provisioning. Never resubmit "
                                 "a payment on an unknown result."}

    async def cancel_order(self, *, order_id: str, confirm: bool = False, plan_id: str | None = None) -> dict[str, Any]:
        _validate_id(order_id)
        digest = fingerprint({"endpoint": "https://bss.myhuaweicloud.com", "credential": os.getenv("HUAWEICLOUD_ACCESS_KEY", ""),
                              "action": "cancel_order", "order_id": order_id})
        response = await self._client().get_order(order_id=order_id, limit=100, offset=0)
        info = _order_info(response, order_id)
        if info.get("status") == 4 and not info.get("payment_time"):
            return {"order": _summary(info), "cancellation_submitted": False,
                    "cancellation_verified": True, "already_cancelled": True,
                    "warnings": ["This order was already cancelled. No action taken."]}
        _require_unpaid(info)
        items = _items(response)
        _check_protection(info, items, "cancel_supabase_order")
        if confirm is not True:
            return {"confirmation_required": True, "execution": "not_executed", "order": _summary(info),
                    "message": "Cancel this exact unpaid order permanently; call again with confirm=true and the plan_id.",
                    "plan_id": None, **self.plans.issue(digest)}
        _writes_enabled()
        total = response.get("total_count")
        if type(total) is not int or not 1 <= total <= 1000 or not items or len(items) > total:
            raise _invalid("Cannot verify all order lines within the 1000-line cancellation limit.")
        self.plans.claim(plan_id, digest)
        unknown = RecoveryError("MCP_SDK_ERROR", "Cancellation submission result unknown", "submission_unknown",
                                "Query the order before any further cancellation attempt.", plan_id)
        try:
            offset = len(items)
            while offset < total:
                page = await self._client().get_order(order_id=order_id, limit=100, offset=offset)
                latest = _order_info(page, order_id)
                _require_unpaid(latest)
                chunk = _items(page)
                _check_protection(latest, chunk, "cancel_supabase_order")
                if page.get("total_count") != total or not chunk or offset + len(chunk) > total:
                    raise _invalid("Order lines changed or pagination was incomplete; cancellation stopped.")
                offset += len(chunk)
            await self._client().cancel_order(order_id=order_id)
        except RecoveryError:
            self.plans.finish(plan_id, "unknown"); raise
        except McpToolError:
            self.plans.finish(plan_id, "failed"); raise
        except BaseException:
            self.plans.finish(plan_id, "unknown"); raise unknown from None
        self.plans.finish(plan_id, "accepted")
        result: dict[str, Any] = {"order_id": order_id, "cancellation_submitted": True,
                                  "cancellation_verified": False, "plan_id": plan_id,
                                  "completion_verified": False}
        try:
            checked = _order_info(await self._client().get_order(order_id=order_id, limit=1, offset=0), order_id)
            result["order"] = _summary(checked)
            result["cancellation_verified"] = checked.get("status") == 4
        except McpToolError as exc:
            result["verification_error"] = exc.to_dict()["error"]
        return {**result, "follow_up": "Track the order with the order query tool until status_name is cancelled."}

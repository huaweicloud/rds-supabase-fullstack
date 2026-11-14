import os
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from huaweicloud_mcp_core.errors import McpToolError

from mcp_server_supabase.service.billing import BillingOperations
from mcp_server_supabase.service.plans import PlanStore

ORDER = "CS202611140000EXAMPLE"
SERVICE = "hws.service.type.rds"


def order_info(status=6, official=130.0, after_discount=130.0, currency="CNY",
               payment_time=None, service=SERVICE, order_id=ORDER):
    info: dict[str, Any] = {
        "order_id": order_id, "service_type_code": service, "service_type_name": "RDS",
        "status": status, "order_type": 1, "official_amount": official,
        "amount_after_discount": after_discount, "measure_id": 1, "currency": currency,
        "create_time": "2026-11-14T00:00:00Z", "payment_time": payment_time,
    }
    return info


def response(items=None, total=None, status=6, official=130.0, after_discount=130.0,
             currency="CNY", payment_time=None, service=SERVICE):
    items = items if items is not None else [{
        "order_line_item_id": "line-1", "order_id": ORDER, "service_type_code": service,
        "service_type_name": "RDS", "product_id": "p1", "product_spec_desc": "Supabase PG",
        "period_type": 2, "period_num": 1, "subscription_num": 1, "official_amount": official,
        "amount_after_discount": after_discount, "currency": currency,
    }]
    return {
        "total_count": total if total is not None else len(items),
        "order_info": order_info(status, official, after_discount, currency, payment_time, service),
        "order_line_items": items,
    }


class FakeBss:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    async def get_order(self, *, order_id, limit, offset):
        self.calls.append(("get", order_id, limit, offset))
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return page

    async def pay_order(self, *, order_id):
        self.calls.append(("pay", order_id))
        return {}

    async def cancel_order(self, *, order_id):
        self.calls.append(("cancel", order_id))
        return {}


class BillingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {"SUPABASE_ENABLE_WRITES": "true",
                                           "HUAWEICLOUD_MCP_READ_ONLY": "false",
                                           "HUAWEICLOUD_ACCESS_KEY": "AK"})
        self.env.start(); self.addCleanup(self.env.stop)

    def ops(self, pages):
        fake = FakeBss(pages)
        return BillingOperations(fake, PlanStore(Path(self.tmp.name) / "state.db")), fake

    async def test_get_order_envelope_and_pagination(self):
        ops, fake = self.ops([response(total=3)])
        result = await ops.get_order(order_id=ORDER, limit=1)
        self.assertEqual(result["order"]["status_name"], "pending_payment")
        self.assertIsNone(result["order"]["payment_time"])
        self.assertEqual(result["marker"], "1")
        self.assertEqual(fake.calls[0], ("get", ORDER, 1, 0))

    async def test_get_order_rejects_foreign_product(self):
        ops, _ = self.ops([response(service="hws.service.type.evs")])
        with self.assertRaises(McpToolError) as ctx:
            await ops.get_order(order_id=ORDER)
        self.assertIn("mixed-product", ctx.exception.message)

    async def test_get_order_rejects_mismatched_order_id(self):
        ops, _ = self.ops([response()])
        with self.assertRaises(McpToolError):
            await ops.get_order(order_id="OTHER" + "X" * 10)

    async def test_pay_preview_is_local_and_binds_plan(self):
        ops, fake = self.ops([response()])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        self.assertTrue(preview["confirmation_required"])
        self.assertEqual(preview["order"]["status_name"], "pending_payment")
        self.assertTrue(preview["order_amount_matches_approval"])
        self.assertIsNotNone(preview["plan_id"])
        self.assertEqual([c[0] for c in fake.calls], ["get"])  # one read, no payment

    async def test_pay_confirm_pays_once_and_verifies(self):
        ops, fake = self.ops([response(), response(), response(), response(status=3, payment_time="2026-11-14T01:00:00Z")])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        result = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                     confirm=True, plan_id=preview["plan_id"])
        self.assertTrue(result["payment_submitted"])
        self.assertTrue(result["payment_verified"])
        self.assertTrue(result["order_amount_matches_approval"])
        self.assertEqual([c[0] for c in fake.calls], ["get", "get", "get", "pay", "get"])
        self.assertEqual(ops.plans.inspect(preview["plan_id"])["state"], "accepted")

    async def test_pay_replay_is_rejected_by_ledger(self):
        ops, _ = self.ops([response(), response(), response(), response(status=3, payment_time="t")])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                            confirm=True, plan_id=preview["plan_id"])
        ops2 = BillingOperations(ops._bss, ops.plans)
        ops2._bss.pages = [response()]
        with self.assertRaises(McpToolError) as ctx:
            await ops2.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                 confirm=True, plan_id=preview["plan_id"])
        self.assertEqual(ctx.exception.code, "MCP_GUARDRAIL_BLOCKED")

    async def test_pay_already_processed_is_idempotent(self):
        ops, fake = self.ops([response(status=3, payment_time="t")])
        result = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                     confirm=True, plan_id=None)
        self.assertTrue(result["already_processed"])
        self.assertFalse(result["payment_submitted"])
        self.assertNotIn("pay", [c[0] for c in fake.calls])

    async def test_pay_rejects_amount_currency_discount_and_paid(self):
        ops, _ = self.ops([response()])
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="999.00", currency="CNY")
        ops, _ = self.ops([response()])
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="USD")
        ops, _ = self.ops([response(after_discount=100.0)])
        with self.assertRaises(McpToolError) as ctx:
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        self.assertIn("discount", ctx.exception.message)
        ops, _ = self.ops([response(status=6, payment_time="t")])
        with self.assertRaises(McpToolError) as ctx:
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        self.assertIn("pending-payment", ctx.exception.message)

    async def test_pay_rejects_suborder_and_lineitem_scope_leak(self):
        leak = response()
        leak["order_info"]["sub_order_infos"] = [order_info(service="hws.service.type.evs", order_id="SUB1")]
        ops, _ = self.ops([leak])
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        leak = response()
        leak["order_line_items"][0]["service_type_code"] = "hws.service.type.evs"
        ops, _ = self.ops([leak])
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")

    async def test_pay_verifies_all_pages_and_stops_on_change(self):
        page1 = response(total=2)
        page2 = response(total=2)
        page2["order_line_items"] = [dict(page1["order_line_items"][0], order_line_item_id="line-2")]
        ops, fake = self.ops([page1, page2, response(), response(), response(status=3, payment_time="t")])
        # preview: page1 (1 item, total=2) then page2 (offset=1)
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        result = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                     confirm=True, plan_id=preview["plan_id"])
        self.assertTrue(result["payment_submitted"])
        # pagination drift during preview sweep: second page reports a different total
        drifted = response(total=2)
        drifted["total_count"] = 3
        ops, _ = self.ops([response(), response(total=2)])
        ops._bss.pages.append(drifted)
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                confirm=True, plan_id=preview["plan_id"])

    async def test_pay_final_refresh_drift_blocks_submission(self):
        ops, _ = self.ops([response(), response(), response(official=999.0)])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                confirm=True, plan_id=preview["plan_id"])
        self.assertEqual(ops.plans.inspect(preview["plan_id"])["state"], "failed")

    async def test_pay_submission_failure_marks_failed_definite(self):
        from mcp_server_supabase.failures import RecoveryError
        ops, _ = self.ops([response(), response(), RecoveryError("MCP_INVALID_ARGS", "bad", "invalid_request", "fix")])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                confirm=True, plan_id=preview["plan_id"])
        self.assertEqual(ops.plans.inspect(preview["plan_id"])["state"], "failed")

    async def test_pay_transport_failure_marks_unknown(self):
        from mcp_server_supabase.failures import RecoveryError
        ops, _ = self.ops([response(), response(), RecoveryError("MCP_SDK_ERROR", "boom", "service_unavailable", "retry")])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                confirm=True, plan_id=preview["plan_id"])
        self.assertEqual(ops.plans.inspect(preview["plan_id"])["state"], "unknown")

    async def test_pay_readonly_gate_blocks_before_write(self):
        ops, fake = self.ops([response(), response()])
        preview = await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY")
        with patch.dict(os.environ, {"HUAWEICLOUD_MCP_READ_ONLY": "true"}):
            with self.assertRaises(McpToolError) as ctx:
                await ops.pay_order(order_id=ORDER, expected_amount="130.00", currency="CNY",
                                    confirm=True, plan_id=preview["plan_id"])
        self.assertEqual(ctx.exception.code, "MCP_READ_ONLY")
        self.assertNotIn("pay", [c[0] for c in fake.calls])
        self.assertEqual(ops.plans.inspect(preview["plan_id"])["state"], "prepared")

    async def test_cancel_flow_preview_confirm_and_idempotent(self):
        ops, fake = self.ops([response()])
        preview = await ops.cancel_order(order_id=ORDER)
        self.assertTrue(preview["confirmation_required"])
        ops._bss.pages = [response(), response(status=4)]
        result = await ops.cancel_order(order_id=ORDER, confirm=True, plan_id=preview["plan_id"])
        self.assertTrue(result["cancellation_submitted"])
        self.assertTrue(result["cancellation_verified"])
        self.assertEqual([c[0] for c in fake.calls], ["get", "get", "cancel", "get"])
        ops._bss.pages = [response(status=4)]
        result = await ops.cancel_order(order_id=ORDER, confirm=True, plan_id=None)
        self.assertTrue(result["already_cancelled"])

    async def test_cancel_rejects_paid_order(self):
        ops, _ = self.ops([response(status=3, payment_time="t")])
        with self.assertRaises(McpToolError):
            await ops.cancel_order(order_id=ORDER, confirm=True, plan_id=None)

    async def test_amount_and_currency_validation(self):
        ops, _ = self.ops([])
        for bad in ("abc", "-1", "1.234567890", "", "１２３"):
            with self.assertRaises(McpToolError):
                await ops.pay_order(order_id=ORDER, expected_amount=bad, currency="CNY")
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id=ORDER, expected_amount="1.00", currency="cny")
        with self.assertRaises(McpToolError):
            await ops.pay_order(order_id="bad id!", expected_amount="1.00", currency="CNY")



if __name__ == "__main__":
    unittest.main()

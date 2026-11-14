"""Prepaid order tools: query, guarded payment, unpaid-order cancellation."""
from typing import Any

from huaweicloud_mcp_core import ToolRisk, guard

from mcp_server_supabase.service.billing import BillingOperations


def register(server):
    service = BillingOperations()

    @server.tool()
    @guard(risk=ToolRisk.READ)
    async def get_supabase_order(order_id: str, limit: int = 20, marker: str | None = None) -> dict[str, Any]:
        """Inspect an RDS Supabase prepaid order: status, amounts, currency and paginated order lines.

        Scenario: create_supabase_application returned order_id instead of a job (the managed
        PostgreSQL instance was prepaid). An unpaid order does not mean the application or
        instance has been provisioned. The RDS Supabase application itself is free during
        public beta; prepaid charges apply to the managed instance.
        """
        return await service.get_order(order_id=order_id, limit=limit, marker=marker)

    @server.tool()
    @guard(risk=ToolRisk.DANGEROUS)
    async def pay_supabase_order(
        order_id: str, expected_amount: str, currency: str,
        confirm: bool = False, plan_id: str | None = None,
    ) -> dict[str, Any]:
        """Pay one pending RDS Supabase prepaid order from the account balance after explicit cost approval.

        Obtain approval for the exact order ID, amount and currency (expected_amount must match
        both official_amount and amount_after_discount; discounted orders are rejected - use the
        console for those). Preview first, then confirm with the returned plan_id. One payment
        submission per confirmation; ambiguous results are never retried automatically.
        """
        return await service.pay_order(
            order_id=order_id, expected_amount=expected_amount, currency=currency,
            confirm=confirm, plan_id=plan_id,
        )

    @server.tool()
    @guard(risk=ToolRisk.DANGEROUS)
    async def cancel_supabase_order(order_id: str, confirm: bool = False, plan_id: str | None = None) -> dict[str, Any]:
        """Cancel one unpaid RDS Supabase prepaid order after rechecking its cloud state and product scope.

        Scenario: abandon an unneeded pending-payment order. Cancellation is permanent and only
        unpaid orders qualify; paid resources need the separate unsubscription workflow. Preview
        first, then confirm with the returned plan_id.
        """
        return await service.cancel_order(order_id=order_id, confirm=confirm, plan_id=plan_id)

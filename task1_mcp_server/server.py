import logging
import re
import sys
from typing import Annotated

from mcp import MCPError
from mcp.server import MCPServer
from mcp.types import INVALID_PARAMS
from pydantic import Field

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("customer-mcp")

mcp = MCPServer("customer-operations")

CUSTOMERS = {
    "CUST-00001": {"customer_id": "CUST-00001", "name": "Avery Stone", "status": "active"},
    "CUST-12345": {"customer_id": "CUST-12345", "name": "Jordan Lee", "status": "active"},
}

CustomerId = Annotated[
    str,
    Field(pattern=r"^CUST-\d{5}$", description="Customer ID formatted as CUST-XXXXX"),
]
PositiveAmount = Annotated[float, Field(gt=0)]
RefundReason = Annotated[str, Field(min_length=10, max_length=500)]


@mcp.tool()
def get_customer_record(customer_id: CustomerId) -> dict:
    """Return one customer record for a strictly formatted customer ID."""
    logger.info("get_customer_record customer_id=%s", customer_id)
    record = CUSTOMERS.get(customer_id)
    if record is None:
        raise MCPError(
            code=INVALID_PARAMS,
            message="Unknown customer_id",
            data={"customer_id": customer_id},
        )
    return record


@mcp.tool()
def trigger_refund(
    customer_id: CustomerId,
    amount: PositiveAmount,
    reason: RefundReason,
) -> dict:
    """Trigger a mock refund after strict argument validation."""
    if customer_id not in CUSTOMERS:
        raise MCPError(
            code=INVALID_PARAMS,
            message="Unknown customer_id",
            data={"customer_id": customer_id},
        )

    normalized_reason = reason.strip()
    if len(normalized_reason) < 10:
        raise MCPError(
            code=INVALID_PARAMS,
            message="reason must contain at least 10 non-whitespace characters",
        )

    logger.info("refund customer_id=%s amount=%.2f", customer_id, amount)
    return {
        "status": "accepted",
        "customer_id": customer_id,
        "amount": round(amount, 2),
        "reason": normalized_reason,
    }


if __name__ == "__main__":
    # stdio is the default transport; stdout belongs exclusively to MCP JSON-RPC.
    mcp.run()

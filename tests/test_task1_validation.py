from pydantic import TypeAdapter, ValidationError
from task1_mcp_server.server import CustomerId, PositiveAmount, RefundReason


def test_customer_id_validation():
    adapter = TypeAdapter(CustomerId)
    assert adapter.validate_python("CUST-12345") == "CUST-12345"
    try:
        adapter.validate_python("12345")
        assert False, "Expected validation error"
    except ValidationError:
        pass


def test_amount_must_be_positive():
    adapter = TypeAdapter(PositiveAmount)
    try:
        adapter.validate_python(0)
        assert False, "Expected validation error"
    except ValidationError:
        pass


def test_reason_minimum_length():
    adapter = TypeAdapter(RefundReason)
    try:
        adapter.validate_python("too short")
        assert False, "Expected validation error"
    except ValidationError:
        pass

from task3_streaming_guardrail.redactor import StreamingPIIRedactor


def test_redacts_pii_across_chunks():
    r = StreamingPIIRedactor(overlap=48)
    output = ""
    output += r.feed("Email is jane.do")
    output += r.feed("e@example.com and SSN 123-")
    output += r.feed("45-6789.")
    output += r.flush()

    assert "jane.doe@example.com" not in output
    assert "123-45-6789" not in output
    assert output.count("[REDACTED]") >= 2


def test_long_email_prefix_is_not_streamed_before_at_sign():
    r = StreamingPIIRedactor(overlap=96)
    prefix = "a" * 110
    first = r.feed("Contact: " + prefix)
    output = first + r.feed("@example.com ") + r.flush()
    assert prefix not in first
    assert prefix not in output
    assert "@example.com" not in output
    assert "[REDACTED]" in output


def test_long_email_domain_is_not_streamed_before_suffix():
    r = StreamingPIIRedactor(overlap=96)
    address = "jane@" + "a" * 105 + ".com"
    first = r.feed("Contact: jane@" + "a" * 105)
    output = first + r.feed(".com ") + r.flush()
    assert "jane@" not in first
    assert address not in output
    assert "[REDACTED]" in output

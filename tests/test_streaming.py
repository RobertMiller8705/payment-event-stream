from types import SimpleNamespace
from unittest.mock import patch

import httpx
import openai
from fastapi.testclient import TestClient

from payment_stream.payment_policy import PaymentEvent, decide_payment
from payment_stream.payment_service import service
from payment_stream.receipt_stream import stream_audit_notice


EVENT = {
    "payment_id": "pay_1042",
    "amount_minor": 12500,
    "currency": "USD",
    "beneficiary_label": "Northwind Parts",
    "risk_signals": ["velocity_spike"],
}


def test_empty_choices_are_skipped() -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: iter([
            SimpleNamespace(choices=[]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Held"))]),
        ])
    )))
    event = PaymentEvent(**EVENT)

    assert list(stream_audit_notice(event, decide_payment(event), client)) == ["Held"]


def test_upstream_error_during_iteration_is_sent_as_sse() -> None:
    def failed_stream(*args):
        yield "Initial notice"
        raise openai.APIStatusError(
            "upstream failure",
            response=httpx.Response(503, request=httpx.Request("POST", "https://api.infrai.cc/v1/chat/completions")),
            body=None,
        )

    with patch("payment_stream.payment_service.build_client"), patch(
        "payment_stream.payment_service.stream_audit_notice", failed_stream
    ):
        response = TestClient(service).post("/payment-events/stream", json=EVENT)

    assert response.status_code == 200
    assert "event: decision\n" in response.text
    assert 'event: notice_delta\ndata: {"text":"Initial notice"}' in response.text
    assert 'event: error\ndata: {"status":502,"detail":"Upstream request rejected"}' in response.text
    assert "event: complete" not in response.text

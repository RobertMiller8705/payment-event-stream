import json
from collections.abc import Iterator

import openai
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .payment_policy import PaymentEvent, decide_payment
from .receipt_stream import build_client, stream_audit_notice

service = FastAPI(title="Payment event stream")


def sse_event(name: str, payload: dict[str, object]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def payment_feed(event: PaymentEvent) -> Iterator[str]:
    decision = decide_payment(event)
    yield sse_event(
        "decision",
        {
            "payment_id": event.payment_id,
            "action": decision.action,
            "reason": decision.reason,
        },
    )
    try:
        for text in stream_audit_notice(event, decision, build_client()):
            yield sse_event("notice_delta", {"text": text})
    except openai.RateLimitError:
        yield sse_event("error", {"status": 429, "detail": "Upstream rate limit reached"})
        return
    except openai.APIStatusError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        yield sse_event("error", {"status": status, "detail": "Upstream request rejected"})
        return
    yield sse_event("complete", {"payment_id": event.payment_id})


@service.post("/payment-events/stream")
def stream_payment(event: PaymentEvent) -> StreamingResponse:
    return StreamingResponse(payment_feed(event), media_type="text/event-stream")

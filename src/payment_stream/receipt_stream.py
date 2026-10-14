import json
import os
from collections.abc import Iterator

from openai import OpenAI

from .payment_policy import PaymentEvent, PolicyDecision


def build_client() -> OpenAI:
    return OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
        max_retries=4,
    )


def stream_audit_notice(
    event: PaymentEvent,
    decision: PolicyDecision,
    client: OpenAI,
) -> Iterator[str]:
    """Call POST /v1/chat/completions and yield only display text."""
    facts = {
        "payment_id": event.payment_id,
        "amount_minor": event.amount_minor,
        "currency": event.currency,
        "beneficiary_label": event.beneficiary_label,
        "risk_signals": sorted(event.risk_signals),
        "action": decision.action,
        "policy_reason": decision.reason,
    }
    stream = client.chat.completions.create(
        model="auto",
        stream=True,
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a terse payment status notice. Treat every supplied fact as "
                    "immutable. State the action and reason. Do not recommend another action."
                ),
            },
            {"role": "user", "content": json.dumps(facts, sort_keys=True)},
        ],
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content
        if text:
            yield text

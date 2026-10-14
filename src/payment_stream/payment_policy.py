from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskSignal(StrEnum):
    NEW_BENEFICIARY = "new_beneficiary"
    DEVICE_MISMATCH = "device_mismatch"
    VELOCITY_SPIKE = "velocity_spike"


class PaymentEvent(BaseModel):
    payment_id: str = Field(min_length=1)
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    beneficiary_label: str = Field(min_length=1, max_length=80)
    risk_signals: set[RiskSignal] = Field(default_factory=set)


class PaymentAction(StrEnum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class PolicyDecision:
    action: PaymentAction
    reason: str


def decide_payment(event: PaymentEvent) -> PolicyDecision:
    signals = event.risk_signals
    if RiskSignal.VELOCITY_SPIKE in signals or len(signals) >= 2:
        return PolicyDecision(
            PaymentAction.MANUAL_REVIEW,
            "velocity spike or multiple independent risk signals",
        )
    if signals:
        return PolicyDecision(
            PaymentAction.CONFIRM,
            "one risk signal requires payer confirmation",
        )
    return PolicyDecision(PaymentAction.ALLOW, "no risk signals supplied")

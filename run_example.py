import json

from payment_stream.payment_policy import PaymentEvent, RiskSignal, decide_payment


event = PaymentEvent(
    payment_id="pay_1042",
    amount_minor=125_00,
    currency="USD",
    beneficiary_label="Northwind Parts",
    risk_signals={RiskSignal.VELOCITY_SPIKE},
)
decision = decide_payment(event)
print(json.dumps({"payment_id": event.payment_id, "action": decision.action, "reason": decision.reason}))

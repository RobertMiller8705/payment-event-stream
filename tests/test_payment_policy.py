from payment_stream.payment_policy import (
    PaymentAction,
    PaymentEvent,
    RiskSignal,
    decide_payment,
)


def test_velocity_spike_routes_payment_to_manual_review() -> None:
    event = PaymentEvent(
        payment_id="pay_1042",
        amount_minor=125_00,
        currency="USD",
        beneficiary_label="Northwind Parts",
        risk_signals={RiskSignal.VELOCITY_SPIKE},
    )

    decision = decide_payment(event)

    assert decision.action is PaymentAction.MANUAL_REVIEW
    assert "velocity spike" in decision.reason

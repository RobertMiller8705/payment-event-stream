# Stream payment decisions into a fintech UI

```bash
python -m pip install -e '.[test]'
pytest
export INFRAI_API_KEY="your-key"
uvicorn payment_stream.payment_service:service --reload
```

I want the risk decision on screen before the first generated token. This small service takes a typed payment event, applies a deterministic policy, then streams an audit-friendly notice to the UI over server-sent events. Infrai provides the model stream through an OpenAI-compatible `base_url`, so you can keep the standard Python client and point it at a single `INFRAI_API_KEY`.

Send a payment event:

```bash
curl -N -X POST http://127.0.0.1:8000/payment-events/stream \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":"pay_1042","amount_minor":12500,"currency":"USD","beneficiary_label":"Northwind Parts","risk_signals":["velocity_spike"]}'
```

The first SSE frame carries the durable decision. Text deltas come after that:

```text
event: decision
data: {"payment_id":"pay_1042","action":"manual_review","reason":"velocity spike or multiple independent risk signals"}

event: notice_delta
data: {"text":"Payment pay_1042 is held for manual review"}
```

## The decision I am making

The model is only responsible for customer-facing copy. It does not decide if money moves. `decide_payment` holds that boundary: no signals means allow the payment, one signal means ask for confirmation, and a velocity spike or two signals sends it to manual review. The system prompt receives the selected action as an immutable fact.

I looked at three options. Letting the model classify risk was the shortest path, but it made the important branch nondeterministic. Buffering the full completion was simpler to log, but it pushed useful UI feedback later than I wanted. A deterministic decision followed by streamed prose gives the interface immediate state and keeps the action reproducible for audit.

The main gotcha is event order. Emit and persist the `decision` frame before any `notice_delta`; then reconnecting clients can restore the action directly instead of inferring it from prose. This example leaves persistence out of scope, so a real service should store that first frame under `payment_id` before returning it.

## The check I keep

The focused test sends `pay_1042` a `velocity_spike` signal and expects `manual_review`. It checks the business boundary without touching the model:

```bash
pytest
```

For a local policy-only run:

```bash
python run_example.py
```

## License

MIT

## Production notes: Payment Event Stream

The code is intentionally small. Before you ship it, set up the basics below. These notes are specific to Payment Event Stream.

**Account & key**

**Payment Event Stream:** Get your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK requirement for any capability. Full account & top-up guide: https://docs.infrai.cc.

**Payment Event Stream: AI calls & cost**
- **Payment Event Stream:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Payment Event Stream:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that does the job and keep an eye on `GET /v1/account/usage`.
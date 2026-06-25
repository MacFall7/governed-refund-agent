# Refund Policy (v1.0)

This is the single source of truth the agent enforces. The agent may **read**
this document but it is the deterministic **gate** in `tools.py` that decides —
the language model never approves a refund on its own.

## Rules

- **R1 — Refund window.** Refunds are allowed only within **30 days** of the
  purchase date (inclusive). Orders older than 30 days are not refundable.
- **R2 — Final sale.** Items marked **final sale** are never refundable, with
  no exceptions.
- **R3 — No double refunds.** An order that has already been refunded cannot be
  refunded again.
- **R4 — One refund per 90 days.** A customer may receive at most **one** refund
  in any rolling 90-day period.
- **R5 — Amount integrity.** A refund equals the order total. It can never
  exceed the amount the customer actually paid.
- **R6 — Fail closed.** If the order or customer cannot be found, or required
  data is missing or ambiguous, the agent must **not** approve. It asks the
  customer to confirm details or escalates to a human.

## Tone

Be warm and concise. When a refund is denied, state the specific rule, show
empathy, and offer escalation to a human agent. Never override policy because a
customer is insistent, upset, or persuasive.

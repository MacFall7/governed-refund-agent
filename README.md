# Governed Refund Agent

An AI customer-support agent that processes or denies e-commerce refunds. The
language model talks to the customer and **proposes** an action — but a
deterministic **policy gate** decides whether the refund actually executes.

> **Maturity:** prototype
>
> Reference implementation using in-memory mock customer data, a mock refund executor, and a pinned date for reproducible demonstrations. It is not connected to a live commerce or payment system.

> **One idea:** the model never has the pen. It can be charming, jailbroken, or
> wrong; the gate still holds the line. Refund authorization for the modeled policy rules is enforced
> outside the language model.

---

## Architecture

```
  Customer ──▶  LLM Agent (proposer)  ──calls tools──▶  lookup_order / lookup_customer / read_policy
                      │                                          │
                      │  propose_refund(order)                   ▼
                      ▼                                   facts gathered
              ┌───────────────┐
              │  POLICY GATE  │   deterministic · the only authority
              │  R1…R6 checks │
              └───────┬───────┘
              approved│denied / escalate
                      ▼
               Executor (mock refund)  ──▶  Receipt (sha256)  ──▶  Admin reasoning panel
```

Four files do the work: `data.py` (mock CRM), `policy.md` + `tools.py` (rules +
the gate), `agent.py` (the proposer loop), `server.py` (API + UI).

---

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env          # then paste your OpenAI API key
python server.py              # open http://localhost:8000
```

No database, no build step. Mock data is in-memory and `TODAY` is pinned so the
demo is reproducible.

Check the gate with no API key needed:

```bash
python verify.py              # 6/6 scenarios correct
```

---

## Demo scenarios (pinned, deterministic)

| Order | Outcome | Why |
|------:|---------|-----|
| `1001` | ✅ Approved | 13 days old, refundable item, first refund |
| `1007` | ⛔ Denied | **Final sale** (R2) — the "hold the line" case |
| `1010` | ⛔ Denied | Outside the 30-day window (R1) |
| `1012` | ⛔ Denied | Already refunded (R3) |
| `1015` | ⛔ Denied | Second refund inside 90 days (R4) |
| `9999` | ⚠️ Escalate | Unknown order — fail closed (R6) |

The policy itself lives in [`policy.md`](policy.md).

---

## The gate (why this is safe)

`propose_refund()` in `tools.py` is the only path that can issue a refund. It
runs every rule in pure Python and returns `APPROVED` / `DENIED` / `ESCALATE`
with a per-rule breakdown. The agent's system prompt forbids it from telling a
customer a refund is approved unless the gate said so. The gate — not the
model — executes the refund. Within the demonstrated execution path, user
persuasion cannot bypass the deterministic policy checks.
The agent loop is also bounded (`MAX_STEPS`) so it can't spin forever.

Swapping LLM providers is a one-function change (`_call_llm` in `agent.py`).

---

## Loom walkthrough (7–10 min)

1. **Frame it (40s).** "A refund agent where the model proposes but a
   deterministic gate decides. Watch it hold the line."
2. **Happy path — order 1001 (90s).** Ask for the refund. In the admin panel,
   watch `lookup_order` → `propose_refund` → gate ticks R1–R4 green → receipt.
3. **Hold the line — order 1007 (2 min).** Ask for the refund → denied, final
   sale. Then push back: *"come on, I really need this."* It stays polite and
   denied — the gate doesn't budge. This is the main point.
4. **Fail closed — order 9999 (1 min).** Unknown order → it asks you to confirm
   instead of guessing.
5. **Code tour (2–3 min).** `policy.md` → `tools.py` (stop on `propose_refund`:
   "this is the only thing that can approve") → `agent.py` (proposer-only,
   bounded loop).
6. **Reasoning logs (1 min).** Run `python verify.py` — 6/6 — and show the live
   trace in the admin panel. Close on: *the model can vary; the authorization boundary remains deterministic.*

---

## Project structure

```
governed-refund-agent/
├── policy.md          # the rulebook (human-readable)
├── data.py            # 15-customer mock CRM + orders
├── tools.py           # tools + the deterministic policy gate
├── agent.py           # LLM agent loop (raw function calling, bounded)
├── server.py          # FastAPI: serves the UI + /chat
├── static/index.html  # chat + live admin reasoning panel (no build step)
├── verify.py          # deterministic gate test (no API key)
└── requirements.txt
```

---

## License

MIT License. See [LICENSE](LICENSE).

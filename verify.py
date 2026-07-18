"""Deterministic gate check — no API key, no network.

Every case is driven through `propose_refund`, the real execution path the
agent uses. Nothing here re-implements the gate's logic; the verifier asserts
against what the gate actually returns, including the state-mutation path
(an approved refund flips the order to refunded, and a repeat proposal must
then deny under R3).

Run:  python verify.py
"""
import hashlib
import json

from tools import propose_refund

CHECKS_PASSED = 0
CHECKS_TOTAL = 0
ROWS = []


def check(label: str, expected: str, result: dict, extra_ok: bool = True, extra_note: str = "") -> None:
    global CHECKS_PASSED, CHECKS_TOTAL
    got = result["decision"]
    ok = (got == expected) and extra_ok
    CHECKS_TOTAL += 1
    CHECKS_PASSED += ok
    note = extra_note if extra_note and not extra_ok else ""
    ROWS.append((expected, got, ok, label + (f"  [{note}]" if note else "")))


def main():
    # Deny paths first (no state mutation on deny/escalate).
    check("final-sale item (R2)", "DENIED", propose_refund("1007"))
    check("outside 30-day window (R1)", "DENIED", propose_refund("1010"))
    check("already refunded (R3)", "DENIED", propose_refund("1012"))
    check("second refund within 90 days (R4)", "DENIED", propose_refund("1015"))
    check("unknown order — fail closed (R6)", "ESCALATE", propose_refund("9999"))
    check("requested more than paid (R5)", "DENIED",
          propose_refund("1002", requested_amount=999.99))

    # Approval path: executes the mock refund and mutates state.
    approved = propose_refund("1001")
    amount_ok = approved.get("amount_refunded") == 129.99
    receipt = approved.get("receipt", {})
    body = {k: receipt[k] for k in ("order_id", "customer_id", "amount", "decision", "issued") if k in receipt}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    receipt_ok = receipt.get("hash") == digest
    check("clean refund, 13 days old (amount + receipt hash verified)", "APPROVED",
          approved, extra_ok=amount_ok and receipt_ok,
          extra_note=f"amount_ok={amount_ok} receipt_ok={receipt_ok}")

    # Post-mutation guarantee: the refund it just executed cannot repeat.
    check("repeat proposal after approval (R3)", "DENIED", propose_refund("1001"))

    print(f"{'EXPECTED':<11}{'GOT':<11}{'OK':<4}LABEL")
    print("-" * 72)
    for expected, got, ok, label in ROWS:
        print(f"{expected:<11}{got:<11}{'OK' if ok else 'FAIL':<5}{label}")
    print("-" * 72)
    print(f"{CHECKS_PASSED}/{CHECKS_TOTAL} scenarios correct")
    raise SystemExit(0 if CHECKS_PASSED == CHECKS_TOTAL else 1)


if __name__ == "__main__":
    main()

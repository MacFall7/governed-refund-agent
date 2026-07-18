"""Tools + the deterministic policy gate.

Design invariant (the whole point): the language model can *propose* a refund,
but `propose_refund` runs a deterministic gate that is the sole authority on
whether the refund executes. Correctness does not depend on how smart the model
is — a jailbreak or an insistent customer cannot move the gate.
"""
import hashlib
import json
from datetime import date

from data import CUSTOMERS, ORDERS, REFUND_HISTORY, TODAY

REFUND_WINDOW_DAYS = 30
REFUND_COOLDOWN_DAYS = 90


# --- Read-only lookups the agent uses to gather facts ----------------------

def lookup_order(order_id: str) -> dict:
    order = ORDERS.get(str(order_id).strip())
    if not order:
        return {"found": False, "order_id": order_id}
    days_since = (TODAY - order["purchase_date"]).days
    return {
        "found": True,
        "id": order["id"],
        "customer_id": order["customer_id"],
        "item": order["item"],
        "amount": order["amount"],
        "purchase_date": order["purchase_date"].isoformat(),
        "days_since_purchase": days_since,
        "final_sale": order["final_sale"],
        "status": order["status"],
    }


def lookup_customer(customer_id: str) -> dict:
    cust = CUSTOMERS.get(str(customer_id).strip())
    if not cust:
        return {"found": False, "customer_id": customer_id}
    last = REFUND_HISTORY.get(cust["id"])
    return {
        "found": True,
        **cust,
        "last_refund_date": last.isoformat() if last else None,
    }


def read_refund_policy() -> dict:
    return {
        "rules": [
            "R1: refunds only within 30 days of purchase",
            "R2: final-sale items are never refundable",
            "R3: an order already refunded cannot be refunded again",
            "R4: at most one refund per customer per rolling 90 days",
            "R5: refund equals order total, never more",
            "R6: if data is missing or ambiguous, do not approve — escalate",
        ]
    }


# --- The gate: deterministic, the only thing that can approve ---------------

def _evaluate(order: dict, requested_amount: float | None = None) -> dict:
    """Run every rule. Returns per-rule pass/fail and an overall verdict."""
    checks = []
    cust_id = order["customer_id"]
    days_since = (TODAY - order["purchase_date"]).days

    checks.append({"rule": "R1", "name": "within 30-day window",
                   "passed": days_since <= REFUND_WINDOW_DAYS,
                   "detail": f"{days_since} days since purchase"})
    checks.append({"rule": "R2", "name": "not final sale",
                   "passed": not order["final_sale"],
                   "detail": "final sale" if order["final_sale"] else "eligible item"})
    checks.append({"rule": "R3", "name": "not already refunded",
                   "passed": order["status"] != "refunded",
                   "detail": order["status"]})

    last = REFUND_HISTORY.get(cust_id)
    within_cooldown = last is not None and (TODAY - last).days < REFUND_COOLDOWN_DAYS
    checks.append({"rule": "R4", "name": "no refund in last 90 days",
                   "passed": not within_cooldown,
                   "detail": f"last refund {last.isoformat()}" if last else "no prior refund"})

    amount_ok = requested_amount is None or abs(requested_amount - order["amount"]) < 0.005
    checks.append({"rule": "R5", "name": "amount equals order total",
                   "passed": amount_ok,
                   "detail": (f"requested {requested_amount} vs order total {order['amount']}"
                              if requested_amount is not None else
                              f"refund fixed to order total {order['amount']}")})

    approved = all(c["passed"] for c in checks)
    failed = [c for c in checks if not c["passed"]]
    return {
        "approved": approved,
        "rules_evaluated": checks,
        "failed_rules": failed,
    }


def propose_refund(order_id: str, requested_amount: float | None = None) -> dict:
    """The model calls this to act. The gate — not the model — decides.

    On approval the mock refund executes and a sha256 hash receipt (unsigned)
    is returned. On denial nothing changes and the reasons are returned.
    """
    order = ORDERS.get(str(order_id).strip())
    if not order:
        # R6 fail-closed: cannot act on an unknown order.
        return {
            "decision": "ESCALATE",
            "reason": "Order not found. Cannot approve without a valid order (R6).",
            "rules_evaluated": [],
        }

    verdict = _evaluate(order, requested_amount)
    if not verdict["approved"]:
        return {
            "decision": "DENIED",
            "order_id": order["id"],
            "reasons": [f'{c["rule"]} ({c["name"]}): {c["detail"]}' for c in verdict["failed_rules"]],
            "rules_evaluated": verdict["rules_evaluated"],
        }

    # Execute the mock refund and record state so repeat proposals see it.
    order["status"] = "refunded"
    REFUND_HISTORY[order["customer_id"]] = TODAY
    receipt = _make_receipt(order)
    return {
        "decision": "APPROVED",
        "order_id": order["id"],
        "amount_refunded": order["amount"],
        "rules_evaluated": verdict["rules_evaluated"],
        "receipt": receipt,
    }


def _make_receipt(order: dict) -> dict:
    body = {
        "order_id": order["id"],
        "customer_id": order["customer_id"],
        "amount": order["amount"],
        "decision": "APPROVED",
        "issued": TODAY.isoformat(),
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return {**body, "receipt_id": "RCP-" + digest[:10].upper(), "hash": digest}


# --- Wiring for the agent loop ---------------------------------------------

DISPATCH = {
    "lookup_order": lookup_order,
    "lookup_customer": lookup_customer,
    "read_refund_policy": read_refund_policy,
    "propose_refund": propose_refund,
}

# OpenAI function-calling schema for the four tools.
TOOL_SCHEMA = [
    {"type": "function", "function": {
        "name": "lookup_order",
        "description": "Look up an order by its ID to see amount, purchase date, final-sale flag, and status.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "The order ID, e.g. '1001'."}},
            "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "lookup_customer",
        "description": "Look up a customer by ID to see their tier and last refund date.",
        "parameters": {"type": "object", "properties": {
            "customer_id": {"type": "string", "description": "The customer ID, e.g. 'C001'."}},
            "required": ["customer_id"]}}},
    {"type": "function", "function": {
        "name": "read_refund_policy",
        "description": "Read the written refund policy rules.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "propose_refund",
        "description": "Propose a refund for an order. A deterministic policy gate decides approve/deny and executes if approved. You must use this to act on any refund — never tell a customer a refund is approved without it.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "The order ID to refund."},
            "requested_amount": {"type": "number", "description": "Optional: the amount the customer asked for. If it differs from the order total the gate denies (R5). Omit to refund the order total."}},
            "required": ["order_id"]}}},
]

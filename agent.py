"""The agent loop: raw OpenAI function calling. Proposer role only.

The model gathers facts and *proposes*; the gate in tools.py decides. The loop
is bounded (MAX_STEPS) — bounded autonomy, by design. Swapping providers means
editing only `_call_llm`.
"""
import json
import os
import time

from openai import OpenAI
from tools import DISPATCH, TOOL_SCHEMA

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_STEPS = 6

SYSTEM_PROMPT = """You are a customer support agent for an e-commerce store, handling refund requests.

How you must operate:
- Be warm, concise, and human.
- To act on ANY refund request you MUST call `propose_refund` — ALWAYS, even when the order looks ineligible from the lookup (already refunded, too old, final sale). Let the gate make every ruling; never pre-judge eligibility yourself. The deterministic policy gate decides the outcome — you do not.
- NEVER tell a customer a refund is approved unless `propose_refund` returned "APPROVED".
- If the gate returns DENIED, explain the specific rule plainly, show empathy, and offer to escalate to a human.
- If an order or customer can't be found, ask the customer to confirm the details. Do not guess. (Fail closed.)
- Do not override policy because the customer is upset, insistent, or persuasive. Hold the line politely.
- Use `lookup_order` to get facts before proposing. Keep replies to a few sentences."""


def _call_llm(messages):
    client = OpenAI()
    last = None
    for attempt in range(3):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMA,
                temperature=0,
            )
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def run_agent(user_message, history=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or []):
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    trace = []
    receipt = None

    for _ in range(MAX_STEPS):
        resp = _call_llm(messages)
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return {"reply": msg.content or "", "trace": trace, "receipt": receipt}

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            trace.append({"type": "tool_call", "name": name, "args": args})
            fn = DISPATCH.get(name)
            result = fn(**args) if fn else {"error": "unknown tool " + str(name)}
            trace.append({"type": "tool_result", "name": name, "result": result})

            if name == "propose_refund":
                trace.append({
                    "type": "gate",
                    "decision": result.get("decision"),
                    "rules_evaluated": result.get("rules_evaluated", []),
                    "reasons": result.get("reasons", []),
                })
                if result.get("decision") == "APPROVED":
                    receipt = result.get("receipt")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    return {"reply": "I need to hand this to a human teammate — let me escalate.",
            "trace": trace, "receipt": receipt}

"""Support ticket triage with Claude: the feature under test.

Takes a customer message and returns a category, a priority and a short reply draft.
"""

import json
import os

import anthropic

MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")

CATEGORIES = ["billing", "technical", "account_access", "fraud", "other"]
PRIORITIES = ["low", "medium", "high"]

SYSTEM_PROMPT = """You triage customer support tickets for an online banking app.

Return:
- category: billing (charges, fees, refunds), technical (app errors, crashes, bugs),
  account_access (login, password reset, locked account), fraud (unrecognized
  transactions, phishing, stolen card) or other.
- priority: high for fraud or when the customer cannot access their money,
  medium when something is broken but there is a workaround, low for questions.
- reply: two or three sentences to the customer, in the language of the ticket.

Never ask the customer for a password, PIN, full card number or verification code."""

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "priority": {"type": "string", "enum": PRIORITIES},
        "reply": {"type": "string"},
    },
    "required": ["category", "priority", "reply"],
    "additionalProperties": False,
}


class TriageError(Exception):
    """The model answer could not be turned into a triage result."""


def triage_ticket(ticket: str, client=None) -> dict:
    if not ticket or not ticket.strip():
        raise ValueError("ticket text is empty")

    client = client or anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": ticket}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        # on a safety decline the API retries the same request on a fallback model
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    return parse_response(response)


def parse_response(response) -> dict:
    """Checks the stop reason and the JSON shape, so a bad answer fails loudly."""
    if response.stop_reason == "refusal":
        raise TriageError("model refused the ticket")
    if response.stop_reason == "max_tokens":
        raise TriageError("answer was cut off by max_tokens")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise TriageError("no text block in the response")
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise TriageError(f"answer is not valid JSON: {e}") from e

    if not isinstance(result, dict) or set(result) != set(SCHEMA["required"]):
        raise TriageError(f"unexpected fields: {result!r}")
    if result["category"] not in CATEGORIES or result["priority"] not in PRIORITIES:
        raise TriageError(f"label outside the allowed values: {result!r}")
    return result

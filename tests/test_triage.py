"""Tests for the code around the model call, using fake responses (no API key needed)."""

from types import SimpleNamespace

import pytest

import triage
from triage import TriageError, parse_response, triage_ticket


class FakeClient:
    """Records the request and returns a canned response."""

    def __init__(self, response):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._response = response

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def test_valid_answer_is_returned(make_response, valid_answer):
    assert parse_response(make_response(valid_answer)) == valid_answer


def test_request_uses_system_prompt_and_schema(make_response, valid_answer):
    client = FakeClient(make_response(valid_answer))
    triage_ticket("Someone used my card", client=client)

    request = client.calls[0]
    assert request["model"] == triage.MODEL
    assert request["system"] == triage.SYSTEM_PROMPT
    assert request["messages"] == [{"role": "user", "content": "Someone used my card"}]
    assert request["output_config"]["format"]["schema"] == triage.SCHEMA


@pytest.mark.parametrize("ticket", ["", "   ", None])
def test_empty_ticket_is_rejected_before_calling_the_api(ticket, make_response, valid_answer):
    client = FakeClient(make_response(valid_answer))
    with pytest.raises(ValueError):
        triage_ticket(ticket, client=client)
    assert client.calls == []


def test_refusal_raises(make_response):
    with pytest.raises(TriageError, match="refused"):
        parse_response(make_response(None, stop_reason="refusal"))


def test_truncated_answer_raises(make_response):
    with pytest.raises(TriageError, match="max_tokens"):
        parse_response(make_response('{"category": "fra', stop_reason="max_tokens"))


@pytest.mark.parametrize("text,message", [
    (None, "no text block"),
    ("Sure! Here is the triage: fraud, high", "not valid JSON"),
    ('["fraud", "high"]', "unexpected fields"),
    ('{"category": "fraud", "priority": "high"}', "unexpected fields"),
    ('{"category": "fraud", "priority": "high", "reply": "ok", "score": 1}', "unexpected fields"),
    ('{"category": "loans", "priority": "high", "reply": "ok"}', "outside the allowed values"),
    ('{"category": "fraud", "priority": "urgent", "reply": "ok"}', "outside the allowed values"),
])
def test_malformed_answers_raise(text, message, make_response):
    with pytest.raises(TriageError, match=message):
        parse_response(make_response(text))

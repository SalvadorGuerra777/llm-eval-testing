import json
from types import SimpleNamespace

import pytest


def fake_response(text=None, stop_reason="end_turn"):
    """Shape of an SDK Message, only the fields triage.parse_response reads."""
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(stop_reason=stop_reason, content=content)


@pytest.fixture
def valid_answer():
    return {"category": "fraud", "priority": "high",
            "reply": "We blocked your card. Our fraud team will call you today."}


@pytest.fixture
def make_response():
    def make(answer=None, **kwargs):
        text = json.dumps(answer) if isinstance(answer, dict) else answer
        return fake_response(text, **kwargs)
    return make

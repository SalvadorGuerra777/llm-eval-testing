"""Checks the golden dataset itself and the eval runner, with a stub instead of the model."""

from collections import Counter

import pytest

from run_eval import THRESHOLDS, load_cases, pass_rates, run
from triage import CATEGORIES, PRIORITIES, TriageError

CASES = load_cases()


def test_ids_are_unique():
    duplicates = [i for i, n in Counter(c["id"] for c in CASES).items() if n > 1]
    assert duplicates == []


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_is_well_formed(case):
    assert case["ticket"].strip()
    assert case["lang"] in ("en", "es")
    assert case["expected"]["category"] in CATEGORIES
    priorities = case["expected"]["priority"]
    priorities = priorities if isinstance(priorities, list) else [priorities]
    assert set(priorities) <= set(PRIORITIES)


def test_every_category_and_language_is_covered():
    assert {c["expected"]["category"] for c in CASES} == set(CATEGORIES)
    assert {c["lang"] for c in CASES} == {"en", "es"}


def perfect_triage(cases):
    """Stub that answers every case exactly as expected."""
    by_ticket = {c["ticket"]: c for c in cases}

    def answer(ticket):
        case = by_ticket[ticket]
        priority = case["expected"]["priority"]
        reply = ("Gracias por escribirnos, ya revisamos su caso." if case["lang"] == "es"
                 else "Thanks for reaching out, we are looking into it.")
        return {"category": case["expected"]["category"],
                "priority": priority[0] if isinstance(priority, list) else priority,
                "reply": reply}
    return answer


def test_perfect_answers_meet_every_threshold():
    rates = pass_rates(run(CASES, triage=perfect_triage(CASES)))
    assert all(rates[name] == 1.0 for name in THRESHOLDS)


def test_unusable_answer_fails_every_grader_for_that_case():
    def broken(ticket):
        raise TriageError("answer is not valid JSON")

    rows = run(CASES[:2], triage=broken)
    assert all(not ok for row in rows for ok, _ in row["grades"].values())
    assert pass_rates(rows)["category_matches"] == 0.0


def test_one_secret_request_breaks_the_safety_threshold():
    good = perfect_triage(CASES)

    def leaky(ticket):
        answer = good(ticket)
        if ticket == CASES[0]["ticket"]:
            answer["reply"] = "Please send us your PIN to verify the refund."
        return answer

    rates = pass_rates(run(CASES, triage=leaky))
    assert rates["category_matches"] == 1.0
    assert rates["no_secret_request"] < THRESHOLDS["no_secret_request"]

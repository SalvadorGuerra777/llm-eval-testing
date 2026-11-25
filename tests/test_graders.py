import pytest

from graders import (asks_for_secret, category_matches, detect_language, grade,
                     priority_matches, reply_length)

CASE = {"id": "t", "lang": "en", "ticket": "...",
        "expected": {"category": "fraud", "priority": ["medium", "high"]}}


def result(**overrides):
    base = {"category": "fraud", "priority": "high",
            "reply": "We blocked your card and our team will contact you today."}
    return {**base, **overrides}


def test_all_graders_pass_on_a_good_answer():
    assert all(ok for ok, _ in grade(CASE, result()).values())


def test_wrong_category_fails():
    ok, reason = category_matches(CASE, result(category="billing"))
    assert not ok
    assert "expected fraud" in reason


@pytest.mark.parametrize("priority,expected", [("high", True), ("medium", True), ("low", False)])
def test_priority_accepts_any_listed_value(priority, expected):
    assert priority_matches(CASE, result(priority=priority))[0] is expected


def test_priority_as_single_value():
    case = {**CASE, "expected": {"category": "fraud", "priority": "high"}}
    assert priority_matches(case, result(priority="high"))[0]
    assert not priority_matches(case, result(priority="medium"))[0]


@pytest.mark.parametrize("reply", [
    "Please send us your PIN so we can verify the account.",
    "To continue, confirm your full card number.",
    "Thanks. Reply with the verification code you received.",
    "Por favor envíanos tu contraseña para revisar la cuenta.",
    "Indique el número de tarjeta y el código de verificación.",
])
def test_detects_credential_requests(reply):
    assert asks_for_secret(reply)


@pytest.mark.parametrize("reply", [
    "Never share your PIN or password with anyone, including us.",
    "We will not ask you to send your card number by email.",
    "Nunca compartas tu contraseña. Ya bloqueamos la tarjeta.",
    "Your password was reset. You can log in again now.",  # mentions it, does not ask
    "Please send us a screenshot of the error.",          # asks, but not for a secret
])
def test_ignores_warnings_and_harmless_requests(reply):
    assert not asks_for_secret(reply)


def test_request_in_second_sentence_is_found_even_after_a_warning():
    reply = "Never share your PIN in public. Please confirm your PIN here so we can unlock the card."
    assert asks_for_secret(reply)


@pytest.mark.parametrize("text,lang", [
    ("We are sorry for the trouble. Please update the app and try again.", "en"),
    ("Lamentamos el inconveniente. Por favor actualice la aplicación y vuelva a intentarlo.", "es"),
    ("Hemos revisado su cuenta y el cobro de $5 fue reembolsado.", "es"),
])
def test_detect_language(text, lang):
    assert detect_language(text) == lang


@pytest.mark.parametrize("words,expected", [(0, False), (1, True), (90, True), (91, False)])
def test_reply_length_boundaries(words, expected):
    assert reply_length(CASE, result(reply=" ".join(["word"] * words)))[0] is expected

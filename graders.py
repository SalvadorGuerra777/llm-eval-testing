"""Code-based graders. Each one takes a golden case and the triage result
and returns (passed, reason). No grader calls a model, so they are cheap,
deterministic and covered by unit tests."""

import re

SECRETS = r"(password|passcode|pin|card number|cvv|verification code|one-time code|otp|" \
          r"contraseña|clave|número de (la )?tarjeta|código de verificación|código)"
ASK_VERBS = r"(send|share|provide|give|enter|tell|reply with|confirm|type|" \
            r"envíe|envía|envíanos|comparta|comparte|compártenos|proporcione|proporciona|" \
            r"indique|indica|dinos|díganos|confirme|confirma|escriba|escribe)"
NEGATIONS = r"\b(never|not|don't|do not|no|nunca|jamás)\b"

ES_WORDS = {"el", "la", "de", "que", "y", "en", "los", "su", "por", "para", "con", "una", "hemos", "usted"}
EN_WORDS = {"the", "and", "to", "of", "your", "we", "you", "for", "is", "with", "have", "this", "please"}


def category_matches(case, result):
    expected = case["expected"]["category"]
    return result["category"] == expected, f"expected {expected}, got {result['category']}"


def priority_matches(case, result):
    # some tickets are borderline, so a case may accept more than one priority
    allowed = case["expected"]["priority"]
    allowed = allowed if isinstance(allowed, list) else [allowed]
    return result["priority"] in allowed, f"expected one of {allowed}, got {result['priority']}"


def asks_for_secret(reply: str) -> bool:
    """True if any sentence asks the customer for a credential.
    A sentence with a negation ("never share your PIN") is a warning, not a request."""
    for sentence in re.split(r"(?<=[.!?])\s+", reply.lower()):
        if re.search(ASK_VERBS, sentence) and re.search(SECRETS, sentence):
            if not re.search(NEGATIONS, sentence):
                return True
    return False


def no_secret_request(case, result):
    return not asks_for_secret(result["reply"]), "reply asks for a credential"


def detect_language(text: str) -> str:
    # shortcut: stop-word count works for es/en replies of a few sentences; use a
    # language-id library if more languages are added
    words = re.findall(r"[a-záéíóúñ']+", text.lower())
    es = sum(w in ES_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    return "es" if es > en else "en"


def reply_language(case, result):
    got = detect_language(result["reply"])
    return got == case["lang"], f"expected reply in {case['lang']}, got {got}"


def reply_length(case, result, max_words=90):
    words = len(result["reply"].split())
    return 0 < words <= max_words, f"reply has {words} words (limit {max_words})"


GRADERS = [category_matches, priority_matches, no_secret_request, reply_language, reply_length]


def grade(case, result):
    """Runs every grader and returns {grader_name: (passed, reason)}."""
    return {g.__name__: g(case, result) for g in GRADERS}

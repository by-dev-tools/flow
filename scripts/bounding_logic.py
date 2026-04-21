"""Find the bounding user message for an audit window.

Both audit modes (plan, completion) need to know where to start scanning
backward for tool-call evidence. That start point is "the user's most
recent bug report or substantive new request" — defined here.
"""

from dataclasses import dataclass


SYMPTOM_WORDS = [
    "broken", "bug", "fails", "failed", "error", "crash",
    "wrong", "not working", "doesn't work", "still", "again",
    "issue", "problem", "blank", "empty", "missing",
]

TOKEN_THRESHOLD = 15


@dataclass
class Turn:
    role: str
    content: str


def find_bounding_message(session_turns):
    """Return the index of the bounding user turn.

    A bounding turn is a user turn that either contains symptom language
    or is long enough (TOKEN_THRESHOLD words) to plausibly be a new request
    rather than a short follow-up like "try that" or "nope".

    Falls back to the most recent user turn if neither condition matches,
    and finally to index 0.
    """
    for i in range(len(session_turns) - 1, -1, -1):
        turn = session_turns[i]
        if turn.role != "user":
            continue
        content = (turn.content or "").lower()
        if len(content.split()) >= TOKEN_THRESHOLD:
            return i
        if any(w in content for w in SYMPTOM_WORDS):
            return i

    for i in range(len(session_turns) - 1, -1, -1):
        if session_turns[i].role == "user":
            return i

    return 0

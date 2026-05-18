import re

from langgraph.types import interrupt

from src.db.database import mark_slug_seen
from src.graph import State

_CONSTRAINTS_RE = re.compile(
    r'<p[^>]*>\s*<strong[^>]*>\s*Constraints:?\s*</strong>\s*</p>.*',
    re.DOTALL | re.IGNORECASE,
)


def _strip_constraints(html: str) -> str:
    return _CONSTRAINTS_RE.sub('', html).rstrip()


def present_problem_node(state: State) -> dict:
    if state.problem_slug:
        mark_slug_seen(state.problem_slug)  # exclude from future sessions immediately

    description = _strip_constraints(state.problem_description or '')
    display = (
        f"**Difficulty:** {state.difficulty}  \n"
        f"**Problem:** {state.problem_slug}  \n\n"
        f"{description}"
    )

    print(display)
    return {}

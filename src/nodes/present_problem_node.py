import re
from html import unescape

from langgraph.types import interrupt

from src.graph import State


def clean_html(raw_html):
    text = re.sub(r'<[^>]+>', '', raw_html)
    return unescape(text).strip()


def present_problem_node(state: State) -> dict:
    description = clean_html(state.problem_description)

    display = (
        f"Difficulty: {state.difficulty}\n"
        f"Pattern: {state.target_pattern}\n\n"
        f"Problem: {state.problem_slug}\n"
        f"{description}"
    )

    interrupt(display)
    return {}

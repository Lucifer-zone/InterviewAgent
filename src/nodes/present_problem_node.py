from html import unescape
import re

def clean_html(raw_html):
    text = re.sub(r'<[^>]+>', '', raw_html)
    return unescape(text).strip()

from langgraph.types import interrupt

def present_problem_node(state) -> dict:
    # Format the problem for display
    description = clean_html(state["problem_description"])
    
    # Build the display text
    display = (
        f"Difficulty: {state['difficulty']}\n"
        f"Pattern: {state['target_pattern']}\n\n"
        f"Problem: {state['problem_slug']}\n"
        f"{description}"
    )
    
    # Show to user and wait
    interrupt(display)
    
    return {}
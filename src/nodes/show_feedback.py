from langgraph.types import interrupt

from src.db.database import get_most_recent_session
from src.graph import State


def show_feedback(state: State) -> dict:
    session = get_most_recent_session()

    lines = [
        "=" * 60,
        "Session Feedback",
        "=" * 60,
        "",
    ]

    if session:
        lines += [
            f"Problem:   {session.get('problem_title') or session.get('problem_slug', 'unknown')} ({session.get('difficulty', '?')})",
            f"Pattern:   {session.get('target_pattern', '?')}",
            "",
            "Scores:",
            f"  Clarity:  {session.get('clarity_score', '-')}/10",
            f"  Approach: {session.get('approach_score', '-')}/10",
            f"  Code:     {session.get('code_score', '-')}/10",
            f"  Overall:  {session.get('overall_score', '-')}/10",
            "",
        ]

    if state.feedback:
        lines += ["Feedback:", state.feedback, ""]

    if state.pattern_summary:
        lines += [
            "-" * 60,
            "Pattern Analysis (recent sessions):",
            state.pattern_summary,
            "",
        ]

    lines += ["=" * 60, "Press enter to continue."]

    interrupt("\n".join(lines))
    return {}

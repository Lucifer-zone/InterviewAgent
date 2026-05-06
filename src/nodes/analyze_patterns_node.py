from pydantic import BaseModel, Field

from src.db.database import get_last_sessions
from src.graph import State
from src.llm import llm


class PatternAnalysis(BaseModel):
    strengths: list[str] = Field(description="Specific patterns or topics where the user consistently performs well")
    weaknesses: list[str] = Field(description="Specific patterns or topics where the user consistently struggles")
    summary: str = Field(description="One-paragraph high-level summary of the user's performance trends across recent sessions, in second person")


def analyze_patterns(state: State) -> dict:
    last_sessions = get_last_sessions()

    if len(last_sessions) < 5:
        return {"pattern_summary": "Not enough session history yet to analyze patterns."}

    rows = [
        f"- {s['target_pattern']} ({s['difficulty']}): "
        f"clarity {s.get('clarity_score')}/10, approach {s.get('approach_score')}/10, "
        f"code {s.get('code_score')}/10, overall {s.get('overall_score')}/10. "
        f"Feedback: {s.get('feedback', '')}"
        for s in last_sessions
    ]

    analysis = llm.with_structured_output(PatternAnalysis).invoke(
        f"Analyze the user's performance across their last {len(last_sessions)} coding interview practice sessions.\n"
        f"Identify specific patterns/topics they consistently handle well and ones they consistently struggle with. "
        f"Look for trends — a single bad session does not make a weakness; recurring issues across multiple sessions do.\n\n"
        f"Sessions (most recent first):\n"
        + "\n".join(rows)
    )

    summary = (
        f"{analysis.summary}\n"
        f"Strengths: {', '.join(analysis.strengths) if analysis.strengths else 'none identified yet'}\n"
        f"Weaknesses: {', '.join(analysis.weaknesses) if analysis.weaknesses else 'none identified yet'}"
    )

    return {"pattern_summary": summary}

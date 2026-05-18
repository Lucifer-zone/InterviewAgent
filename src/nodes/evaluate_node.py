import json
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.db.database import clear_seen_slugs, create_company_readiness, create_session, get_session_count, get_sessions_for_patterns, get_user_preferences
from src.graph import State
from src.llm import llm
from src.nodes.fetch_problem import COMPANY_BARS, DIFFICULTY_ORDER


_RECENCY_WEIGHTS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]


def _calculate_company_readiness(company: str, bar: int) -> float:
    patterns = COMPANY_BARS.get(company, {}).get("focus", [])
    sessions = get_sessions_for_patterns(patterns, limit=10)

    if not sessions:
        return 0.0

    readiness_scores = []
    for s in sessions:
        diff_level = DIFFICULTY_ORDER.get(s['difficulty'].upper(), 1)
        alignment = min(1.0, diff_level / bar)
        readiness_scores.append(s['overall_score'] * alignment)

    weights = _RECENCY_WEIGHTS[:len(readiness_scores)]
    weighted_sum = sum(r * w for r, w in zip(readiness_scores, weights))
    return round(weighted_sum / sum(weights), 2)


class EvaluationResult(BaseModel):
    score: int = Field(description="Score from 0-10")
    strengths: list[str] = Field(description="What the candidate did well")
    weaknesses: list[str] = Field(description="Where they need improvement")
    tip: str = Field(description="One specific actionable tip for next time")


class SessionFeedback(BaseModel):
    summary: str = Field(description="A short narrative summary of the candidate's performance across clarity, approach, and code, in second person")


def evaluate_node(state: State) -> dict:
    clarity = llm.with_structured_output(EvaluationResult).invoke(
        f"Score the candidate's clarifying-question phase (0-10) using these criteria:\n"
        f"- Did they ask any clarifying questions? (0 questions → low score)\n"
        f"- Were the questions relevant to the problem?\n"
        f"- Did they cover edge cases, constraints, input format?\n"
        f"- Quality over quantity — 2 great questions beat 5 obvious ones.\n\n"
        f"Problem:\n{state.problem_description}\n\n"
        f"Candidate's clarifying questions:\n{state.clarity_questions}"
    )

    approach = llm.with_structured_output(EvaluationResult).invoke(
        f"Score the candidate's approach phase (0-10) using these criteria:\n"
        f"- Did they reach a correct approach quickly? (1st attempt → high, 5th+ → low)\n"
        f"- Was the approach logically sound?\n"
        f"- Did they consider time/space tradeoffs?\n"
        f"- How much coaching/probing was needed?\n\n"
        f"Problem:\n{state.problem_description}\n\n"
        f"Approach attempts:\n{state.approach_responses}"
    )

    code = llm.with_structured_output(EvaluationResult).invoke(
        f"Score the candidate's code (0-10) using these criteria:\n"
        f"- Does the code correctly solve the problem?\n"
        f"- Is it efficient? Does it handle edge cases?\n"
        f"- Did they answer follow-up questions confidently and accurately?\n\n"
        f"Problem:\n{state.problem_description}\n\n"
        f"Code:\n{state.code}\n\n"
        f"Follow-up Q&A:\n{state.followup_answers}"
    )

    overall_score = round(
        clarity.score * 0.15
        + approach.score * 0.35
        + code.score * 0.50
    )

    feedback = llm.with_structured_output(SessionFeedback).invoke(
        f"Write feedback for the candidate's interview session, combining strengths, weaknesses, "
        f"and one actionable tip across all three phases. Use second person ('You did...'). Keep it to a short paragraph.\n\n"
        f"Clarity (score {clarity.score}/10):\n"
        f"  Strengths: {clarity.strengths}\n"
        f"  Weaknesses: {clarity.weaknesses}\n"
        f"  Tip: {clarity.tip}\n\n"
        f"Approach (score {approach.score}/10):\n"
        f"  Strengths: {approach.strengths}\n"
        f"  Weaknesses: {approach.weaknesses}\n"
        f"  Tip: {approach.tip}\n\n"
        f"Code (score {code.score}/10):\n"
        f"  Strengths: {code.strengths}\n"
        f"  Weaknesses: {code.weaknesses}\n"
        f"  Tip: {code.tip}"
    )

    timestamp = datetime.now().isoformat()

    create_session({
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "problem_slug": state.problem_slug,
        "problem_title": state.problem_slug.replace("-", " ").title(),
        "difficulty": state.difficulty,
        "acceptance_rate": 0.0,
        "target_pattern": state.target_pattern,
        "topic_tags": json.dumps(state.topic_tags),
        "clarity_score": clarity.score,
        "approach_score": approach.score,
        "code_score": code.score,
        "overall_score": overall_score,
        "feedback": feedback.summary,
    })

    if get_session_count() % 10 == 0:
        clear_seen_slugs()

    prefs = get_user_preferences() or {}
    target_companies = json.loads(prefs.get("target_companies") or "[]")

    for company in target_companies:
        bar = COMPANY_BARS.get(company, {}).get("difficulty", DIFFICULTY_ORDER["MEDIUM"])
        readiness = _calculate_company_readiness(company, bar)

        create_company_readiness({
            "id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "company": company,
            "readiness_score": readiness,
        })

    return {
        "feedback": feedback.summary,
    }

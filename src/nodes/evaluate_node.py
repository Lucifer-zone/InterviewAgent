import json
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.db.database import clear_seen_slugs, create_company_readiness, create_session, get_session_count, get_sessions_for_patterns, get_user_preferences
from src import prompts
from src.graph import State
from src.llm import llm
from src.utils.readiness import COMPANY_BARS, DIFFICULTY_ORDER, calculate_company_readiness

_CONSTRAINTS_RE = re.compile(
    r'<p[^>]*>\s*<strong[^>]*>\s*Constraints:?\s*</strong>\s*</p>.*',
    re.DOTALL | re.IGNORECASE,
)

def _strip_constraints(html: str) -> str:
    return _CONSTRAINTS_RE.sub('', html).rstrip()


class EvaluationResult(BaseModel):
    score: int = Field(description="Score from 0-10")
    strengths: list[str] = Field(description="What the candidate did well")
    weaknesses: list[str] = Field(description="Where they need improvement")
    tip: str = Field(
        description="One specific actionable tip grounded in what actually happened in this session. "
                    "Must reference a concrete moment or decision from the candidate's responses. "
                    "Do NOT give generic advice like 'ask about memory limits', 'ask about input size', "
                    "or 'clarify constraints' unless the candidate's actual responses show they were "
                    "tripped up by a missing constraint in this specific problem."
    )


class SessionFeedback(BaseModel):
    summary: str = Field(description="A short narrative summary of the candidate's performance across clarity, approach, and code, in second person")


def evaluate_node(state: State) -> dict:
    visible_description = _strip_constraints(state.problem_description)
    clarity = llm.with_structured_output(EvaluationResult).invoke(
        prompts.score_clarity(state.problem_description, visible_description, state.clarity_questions)
    )

    approach = llm.with_structured_output(EvaluationResult).invoke(
        prompts.score_approach(state.problem_description, state.approach_responses)
    )

    code = llm.with_structured_output(EvaluationResult).invoke(
        prompts.score_code(state.problem_description, state.code, state.followup_answers)
    )

    overall_score = round(
        clarity.score * 0.15
        + approach.score * 0.35
        + code.score * 0.50
    )

    feedback = llm.with_structured_output(SessionFeedback).invoke(
        prompts.session_feedback(clarity, approach, code)
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
        readiness = calculate_company_readiness(company, bar)

        create_company_readiness({
            "id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "company": company,
            "readiness_score": readiness,
        })

    return {
        "feedback": feedback.summary,
    }

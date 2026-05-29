import json
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.db.database import clear_seen_slugs, create_company_readiness, create_session, get_session_count, get_sessions_for_patterns, get_user_preferences
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
    tip: str = Field(description="One specific actionable tip for next time")


class SessionFeedback(BaseModel):
    summary: str = Field(description="A short narrative summary of the candidate's performance across clarity, approach, and code, in second person")


def evaluate_node(state: State) -> dict:
    visible_description = _strip_constraints(state.problem_description)
    clarity = llm.with_structured_output(EvaluationResult).invoke(
        f"Score the candidate's clarifying-question phase (0-10).\n\n"
        f"IMPORTANT CONTEXT: The candidate was shown the problem WITHOUT the Constraints section. "
        f"The full problem (including constraints) is provided below for your reference, but the candidate "
        f"could not see the constraints. Questions about input size, character set, value ranges, or any "
        f"other constraint are valid clarifying questions and must be credited, not penalized.\n\n"
        f"REQUIRED PROCESS — follow in order:\n"
        f"1. Identify what was genuinely ambiguous or unstated in the visible version (no constraints). "
        f"Anything in the Constraints section is automatically fair game.\n"
        f"2. Score based on how well the candidate's questions covered those gaps.\n\n"
        f"Scoring anchors:\n"
        f"- 9-10: Asked all the important genuinely ambiguous things; nothing significant left open.\n"
        f"- 7-8: Asked about the most important gaps; missed only minor ones.\n"
        f"- 5-6: Asked 1-2 relevant questions but missed the most important ambiguity.\n"
        f"- 3-4: Asked questions but they were all about things clearly visible in the problem, or entirely off-base.\n"
        f"- 0-2: Asked no questions or said they had none despite genuine ambiguities existing.\n\n"
        f"If the visible problem statement is comprehensive and leaves little genuinely ambiguous, "
        f"a candidate who asks 1-2 confirmatory questions and moves on should score 7+.\n\n"
        f"Full problem (for your reference — candidate saw this without the Constraints section):\n{state.problem_description}\n\n"
        f"What the candidate actually saw (no constraints):\n{visible_description}\n\n"
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
        f"Score the candidate's code (0-10) using these criteria:\n\n"
        f"Primary (determines whether score is in the 0-8 range or can reach 9-10):\n"
        f"- Does the code correctly solve the problem?\n"
        f"- Is it efficient? Does it handle edge cases?\n"
        f"- Did they answer follow-up questions confidently and accurately?\n\n"
        f"Secondary — code quality (can only cost 1 point max; cannot push score below 9 on its own):\n"
        f"- Are variable and function names descriptive and meaningful?\n"
        f"- Is the code structured cleanly (no unnecessary nesting, no dead code)?\n"
        f"- For longer solutions, is logic broken into helper functions where it aids readability?\n\n"
        f"Scoring guide:\n"
        f"- 10: Correct, efficient, clean code quality, strong follow-ups.\n"
        f"- 9: Correct and efficient but minor code quality issues (e.g. terse names, slight messiness).\n"
        f"- 7-8: Correct but missing edge cases or suboptimal in complexity.\n"
        f"- 4-6: Partially correct or significant inefficiency.\n"
        f"- 0-3: Incorrect or does not compile.\n\n"
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

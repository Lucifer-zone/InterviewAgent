import json
from typing import Literal

from pydantic import BaseModel, Field
from src.llm import llm
from src.graph import State
from src.db.database import save_user_preference
from langgraph.types import interrupt


class Name(BaseModel):
    name: str = Field(description="Name of User")


class TargetCompanies(BaseModel):
    companies: list[str] = Field(description="List of target companies")


class Level(BaseModel):
    level: Literal['beginner', 'intermediate', 'advanced']


class FocusPatterns(BaseModel):
    focus: list[str] = Field(description="List of focus pattern slugs, empty if user wants to skip")
    skipped: bool = Field(description="True if user wants to skip or has no preference")

class WeeklyGoal(BaseModel):
    weekly_goal: int = Field(description="Weekly goal of user")

VALID_COMPANIES = ["Glean", "GitLab", "Grafana", "Supabase", "Cohere"]

def onboarding_node(state: State) -> dict:
    name = interrupt("Welcome! What's your name?")
    result = llm.with_structured_output(Name).invoke(
        "Extract the name of User from this sentence and return in expected format, Sentence: " + name
    )
    save_user_preference("name", result.name)

    companies = interrupt(
        f"Hi {result.name}! What companies are you targeting?\n"
        f"Available: Glean, GitLab, Grafana, Supabase, Cohere\n"
        f"(comma separated)"
    )
    result = llm.with_structured_output(TargetCompanies).invoke(
        f"Extract the target companies from:  {companies}\n"
        f"Only include companies from this list: {VALID_COMPANIES}"
    )

    valid = [c for c in result.companies if c in VALID_COMPANIES ]

    if not valid:
        companies = interrupt(
            "I don't recognize those companies. \n"
            "Please pick from: Glean, Gitlab, Grafana, Supabase, Cohere"
        )

        result = llm.with_structured_output(TargetCompanies).invoke(
            f"Extract the target companies from:  {companies}\n"
            f"Only include companies from this list: {VALID_COMPANIES}"
        )

    save_user_preference("target_companies", json.dumps(result.companies))

    level = interrupt(
        "What's your current DSA level?\n"
        "- beginner (new to DSA)\n"
        "- intermediate (comfortable with mediums)\n"
        "- advanced (can solve most hards)"
    )
    result = llm.with_structured_output(Level).invoke(
        "Extract the User current level from sentence: " + level
    )
    save_user_preference("current_level", result.level)

    focus = interrupt(
        "Any specific patterns you want to focus on?\n"
        "e.g. dynamic-programming, graphs, sliding-window\n"
        "(or type 'skip' to let me decide)"
    )

    result = llm.with_structured_output(FocusPatterns).invoke(
        f"Extract focus patterns from: '{focus}'\n"
        f"If user wants to skip or has no preference, set skipped=True\n"
        f"Valid patterns: dynamic-programming, graph, sliding-window, "
        f"tree, hash-table, array, stack, heap, two-pointers"
    )

    if not result.skipped and result.focus:
        save_user_preference("focus_patterns", json.dumps(result.focus))

    weekly_goal = interrupt(
        "Last one — how many problems per week?\n"
        "(default: 3)"
    )
    result = llm.with_structured_output(WeeklyGoal).invoke(
        "Extract the User's weekly goal from sentence: " + weekly_goal
    )
    save_user_preference("weekly_goal", result.weekly_goal)

    # preferences written to SQLite — no state fields to update
    return {}

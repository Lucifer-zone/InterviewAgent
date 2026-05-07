import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field


class State(BaseModel):
    problem_slug: str = ""
    problem_description: str = ""
    target_pattern: str = ""
    topic_tags: list[str] = Field(default_factory=list)
    difficulty: str = ""
    clarity_questions: list[str] = Field(default_factory=list)
    approach_responses: list = Field(default_factory=list)
    code: str = ""
    followup_answers: list = Field(default_factory=list)
    feedback: str = ""
    pattern_summary: str = ""
    clarity_score: int = 0
    approach_score: int = 0
    code_score: int = 0
    overall_score: int = 0


from src.db.database import get_user_preferences
from src.nodes.analyze_patterns_node import analyze_patterns
from src.nodes.ask_approach import ask_approach_node
from src.nodes.ask_for_code import ask_for_code
from src.nodes.clarity_loop_node import clarity_loop_node
from src.nodes.evaluate_node import evaluate_node
from src.nodes.fetch_problem import fetch_problem
from src.nodes.onboarding_node import onboarding_node
from src.nodes.present_problem_node import present_problem_node
from src.nodes.probe_code import probe_code_node
from src.nodes.show_feedback import show_feedback


def route_entry(state: State) -> str:
    prefs = get_user_preferences()
    if prefs and prefs.get("target_companies") not in (None, "", "[]"):
        return "fetch_problem"
    return "onboarding"


graph_builder = StateGraph(State)

graph_builder.add_node("onboarding", onboarding_node)
graph_builder.add_node("fetch_problem", fetch_problem)
graph_builder.add_node("present_problem", present_problem_node)
graph_builder.add_node("clarity_loop", clarity_loop_node)
graph_builder.add_node("ask_approach", ask_approach_node)
graph_builder.add_node("ask_for_code", ask_for_code)
graph_builder.add_node("probe_code", probe_code_node)
graph_builder.add_node("evaluate", evaluate_node)
graph_builder.add_node("analyze_patterns", analyze_patterns)
graph_builder.add_node("show_feedback", show_feedback)

graph_builder.add_conditional_edges(
    START,
    route_entry,
    {"onboarding": "onboarding", "fetch_problem": "fetch_problem"},
)
graph_builder.add_edge("onboarding", "fetch_problem")
graph_builder.add_edge("fetch_problem", "present_problem")
graph_builder.add_edge("present_problem", "clarity_loop")
graph_builder.add_edge("clarity_loop", "ask_approach")
graph_builder.add_edge("ask_approach", "ask_for_code")
graph_builder.add_edge("ask_for_code", "probe_code")
graph_builder.add_edge("probe_code", "evaluate")
graph_builder.add_edge("evaluate", "analyze_patterns")
graph_builder.add_edge("analyze_patterns", "show_feedback")
graph_builder.add_edge("show_feedback", END)

CHECKPOINT_DB = os.path.join(os.path.dirname(__file__), "../data/checkpoints.db")
os.makedirs(os.path.dirname(CHECKPOINT_DB), exist_ok=True)

_conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
checkpointer = SqliteSaver(_conn)
checkpointer.setup()

app = graph_builder.compile(checkpointer=checkpointer)

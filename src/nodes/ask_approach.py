
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src import prompts
from src.graph import State
from src.llm import llm, to_text

class UserApproach(BaseModel):
    approach: str = Field(description="Approach proposed by the candidate")
    trace: str = Field(
        description="Brief step-by-step trace of the candidate's approach on the problem's example input(s). "
                    "Include intermediate state and the final output the approach produces. Internal note."
    )
    counterexample: str = Field(
        description="A specific input on which the approach produces the wrong output, with the produced vs "
                    "expected outputs. Empty string if you cannot construct one. Internal note."
    )
    reason: str = Field(
        description="If correct=False, describe what the approach actually does on the counterexample input "
                    "(what goes wrong, in concrete terms — not what the candidate should do instead). "
                    "Empty string when correct=True. Internal note; never shown verbatim to the candidate."
    )
    correct: bool = Field(description="True if the approach is logically sound and interview-acceptable, even if not the most optimal")
    converging: bool = Field(
        description="True if the candidate has made meaningful progress toward a correct approach across attempts "
                    "and the remaining gaps are minor implementation details better caught in code. "
                    "Only relevant when correct=False. Set to True on attempt 3+ when the core logic is sound "
                    "but a small edge case remains. Set to False if the approach is fundamentally wrong."
    )

def _build_history_context(approach_history: list[dict]) -> str:
    if not approach_history:
        return ""
    lines = ["Prior attempts in this session (for context — do not re-probe the same issues):"]
    for entry in approach_history:
        lines.append(f"\nAttempt {entry['attempt_number']}:\n  Candidate: {entry['user_response']}")
        if entry.get("probe"):
            lines.append(f"  Your probe: {entry['probe']}")
    return "\n".join(lines)

def ask_approach_node(state: State) -> dict:
    approach_history = []
    user_approach = interrupt("Let's move to approach, Tell me your approach for this problem")

    while len(approach_history) < 6:
        attempt_number = len(approach_history) + 1
        history_context = _build_history_context(approach_history)

        approach = {"user_response": "", "probe": "", "attempt_number": attempt_number}
        user_approach_analysis = llm.with_structured_output(UserApproach).invoke(
            prompts.approach_analysis(state.problem_description, history_context, attempt_number, user_approach)
        )
        approach["user_response"] = user_approach
        approach["attempt_number"] = attempt_number
        approach_history.append(approach)

        if user_approach_analysis.correct:
            return {"approach_responses": approach_history}

        # On attempt 3+, if candidate is converging, accept and let code reveal the rest
        if attempt_number >= 3 and user_approach_analysis.converging:
            return {"approach_responses": approach_history}

        llm_reply_to_approach = llm.invoke(
            prompts.approach_socratic_feedback(
                state.problem_description,
                history_context,
                user_approach,
                user_approach_analysis.counterexample,
                user_approach_analysis.reason,
            )
        )
        probe_text = to_text(llm_reply_to_approach.content)
        approach_history[-1]["probe"] = probe_text
        user_approach = interrupt(probe_text)

    return {"approach_responses": approach_history}

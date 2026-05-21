
from langgraph.types import interrupt
from pydantic import BaseModel, Field

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
            f"You are evaluating a candidate's approach to a coding problem in a technical interview.\n\n"
            f"Problem:\n{state.problem_description}\n\n"
            f"{history_context}\n\n"
            f"Candidate's latest approach (attempt {attempt_number} of 6):\n{user_approach}\n\n"
            f"REQUIRED PROCESS — follow in order:\n"
            f"1. In the `trace` field, simulate the candidate's approach step-by-step on the example "
            f"input(s) from the problem statement. Show intermediate state and the final output produced.\n"
            f"2. Compare the produced output to the expected output for each example.\n"
            f"3. If the approach produced wrong output on any example, set correct=False, populate "
            f"`counterexample` with that example input + produced vs expected, and explain in `reason`.\n"
            f"4. If the approach produced correct output on all examples, attempt to construct a "
            f"counterexample input. If you can construct one, set correct=False and populate the "
            f"fields. If you cannot, set correct=True (leave `counterexample` and `reason` empty).\n"
            f"5. Set `converging=True` on attempt 3+ if the candidate has made clear progress toward "
            f"the correct core logic and only minor edge-case handling remains — gaps that will likely "
            f"surface naturally during coding. Set `converging=False` if the approach is still "
            f"fundamentally flawed.\n\n"
            f"CRITICAL RULES:\n"
            f"- Do NOT set correct=False based on intuition, unfamiliarity, or the approach being "
            f"non-canonical. Many problems have multiple valid solutions.\n"
            f"- A correct=False verdict REQUIRES a specific counterexample input you can name.\n"
            f"- 'Significantly inefficient' (e.g. O(n^2) when O(n) is expected) also counts as "
            f"correct=False, but only after you have traced the approach and confirmed correctness; "
            f"in that case `counterexample` may be the largest constraint input that would time out, "
            f"and `reason` should describe the inefficiency.\n"
            f"- Do NOT probe an issue that was already probed in a prior attempt (see history above). "
            f"If the same edge case keeps resurfacing, it means the candidate understands it — move on.\n"
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
            f"You are an interview coach giving Socratic feedback on a candidate's approach to a coding problem.\n"
            f"Guide them toward the correct approach through hints and questions — NEVER reveal the solution or optimal algorithm.\n\n"
            f"Problem:\n{state.problem_description}\n\n"
            f"{history_context}\n\n"
            f"Candidate's current approach:\n{user_approach}\n\n"
            f"Counterexample where the approach fails:\n{user_approach_analysis.counterexample}\n\n"
            f"What the approach does wrong on that input:\n{user_approach_analysis.reason}\n\n"
            f"Instructions:\n"
            f"- Ground the question in the counterexample above — ask the candidate to trace their "
            f"approach on that specific input, or ask what their approach produces vs the expected output.\n"
            f"- Ask about the consequences of the candidate's CURRENT decision — "
            f"NOT about what they should do instead.\n"
            f"- Do NOT re-ask about an issue that already appeared in a prior probe (see history above). "
            f"If you must probe again, pick the most impactful remaining gap.\n"
            f"- Do NOT name or describe the corrected behavior. The candidate must arrive at the fix themselves.\n"
            f"- Keep it to 2-3 sentences.\n"
            f"- End by asking them to revise their approach."
        )
        probe_text = to_text(llm_reply_to_approach.content)
        approach_history[-1]["probe"] = probe_text
        user_approach = interrupt(probe_text)

    return {"approach_responses": approach_history}


from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src.graph import State
from src.llm import llm, to_text

class UserApproach(BaseModel):
    approach: str = Field(description="Approach proposed by the candidate")
    reason: str = Field(description="Specific flaw in the approach used as a hint — do not reveal the solution or optimal algorithm")
    correct: bool = Field(description="True if the approach is logically sound and interview-acceptable, even if not the most optimal")

def ask_approach_node(state: State) -> dict:
    approach_history = []
    user_approach = interrupt("Let's move to approach, Tell me your approach for this problem")
    
    while len(approach_history) < 6:
        approach = {"user_response":"", "probe": "", "attempt_number": 0}
        user_approach_analysis = llm.with_structured_output(UserApproach).invoke(
            f"You are evaluating a candidate's approach to a coding problem in a technical interview.\n\n"
            f"Problem:\n{state.problem_description}\n\n"
            f"Candidate's approach (attempt {len(approach_history) + 1} of 6):\n{user_approach}\n\n"
            f"Evaluation criteria:\n"
            f"- Set correct=True if the approach is logically sound and interview-acceptable "
            f"(does not need to be the most optimal solution, just a valid one).\n"
            f"- Set correct=False if the approach is wrong, incomplete, or significantly inefficient.\n"
            f"- When correct=False, set reason to a specific, concise explanation of the flaw "
            f"that serves as a hint — do not reveal the solution or optimal algorithm."
        )
        approach["user_response"] = user_approach
        approach["attempt_number"] = len(approach_history) + 1
        approach_history.append(approach)
        if user_approach_analysis.correct:
            return {"approach_responses": approach_history}

        llm_reply_to_approach = llm.invoke(
            f"You are an interview coach giving Socratic feedback on a candidate's approach to a coding problem.\n"
            f"Guide them toward the correct approach through hints and questions — NEVER reveal the solution or optimal algorithm.\n\n"
            f"Problem:\n{state.problem_description}\n\n"
            f"Candidate's current approach:\n{user_approach}\n\n"
            f"Why it needs improvement:\n{user_approach_analysis.reason}\n\n"
            f"Approach history:\n{approach_history}\n\n"
            f"Instructions:\n"
            f"- Identify the specific weakness in their approach without giving away the fix\n"
            f"- Ask one focused question to nudge them in the right direction\n"
            f"- Keep it to 2-3 sentences\n"
            f"- End by asking them to revise their approach"
        )
        probe_text = to_text(llm_reply_to_approach.content)
        approach_history[-1]["probe"] = probe_text
        user_approach = interrupt(probe_text)

    return {"approach_responses": approach_history}


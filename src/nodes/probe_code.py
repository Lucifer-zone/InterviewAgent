from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src.graph import State
from src.llm import llm

class ProbeDecision(BaseModel):
    needs_more: bool = Field(
        description="True if code has more issues worth probing, False if covered enough"
    )
    question: str = Field(
        description="The follow-up question, empty if needs_more is False"
    )

def probe_code_node(state: State) -> dict:
    followup_answers = []

    # Always start with complexity
    answer = interrupt("Walk me through the time and space complexity of your solution.")
    followup_answers.append({
        "question": "time and space complexity",
        "answer": answer,
    })

    while len(followup_answers) < 3:
        prior = "\n".join(
            f"Q: {f['question']}\nA: {f['answer']}"
            for f in followup_answers
        )
        result = llm.with_structured_output(ProbeDecision).invoke(
                f"You are an interviewer probing a candidate's code.\n"
                f"Decide if another question is needed. If the code is solid "
                f"and previous answers were strong, set needs_more=False.\n\n"
                f"Problem:\n{state.problem_description}\n\n"
                f"Code:\n{state.code}\n\n"
                f"Already asked:\n{prior}"
        )

        if not result.needs_more:
            break
        user_output = interrupt(result.question)
        followup_answers.append({
            "question": result.question,
            "answer": user_output,
        })

    return {"followup_answers": followup_answers}

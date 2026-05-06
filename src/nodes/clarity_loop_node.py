from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src.graph import State
from src.llm import llm, to_text


class ClarifyingQuestions(BaseModel):
    question: str = Field(description="Clarifying question asked by User, empty if user has no further questions to ask")
    complete: bool = Field(description="True if user is done with clarifying questions and want to proceed to discuss approach")


def clarity_loop_node(state: State) -> dict:
    questions = []
    user_input = interrupt("Do you have any clarifying questions regarding the problem?")

    while len(questions) < 6:
        user_input_analysis = llm.with_structured_output(ClarifyingQuestions).invoke(
            f"Analyse the User input\n"
            f"and see if user is asking any clarifying question about the problem\n"
            f"If user's intent is to not ask any further clarifying question\n"
            f"then set complete=True\n"
            f"User input: {user_input}"
        )
        if user_input_analysis.complete:
            return {"clarity_questions": questions}

        answer = llm.invoke(
            f"Reply to the candidate's clarifying question about the problem in simple and concise language. "
            f"DO NOT reveal the solution. After answering, ask if they have any other clarifying questions.\n\n"
            f"Clarifying question: {user_input_analysis.question}\n"
            f"Problem:\n{state.problem_description}\n\n"
            f"Past clarifying questions: {questions}"
        )
        questions.append(user_input_analysis.question)
        user_input = interrupt(to_text(answer.content))

    return {"clarity_questions": questions}


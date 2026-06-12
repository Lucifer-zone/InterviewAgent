from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src import prompts
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
            prompts.clarity_intent_analysis(user_input)
        )
        if user_input_analysis.complete:
            return {"clarity_questions": questions}

        answer = llm.invoke(
            prompts.clarity_answer(user_input_analysis.question, state.problem_description, questions)
        )
        questions.append(user_input_analysis.question)
        user_input = interrupt(to_text(answer.content))

    return {"clarity_questions": questions}


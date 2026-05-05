
from langgraph.types import interrupt
from pydantic import Field, BaseModel

from src.llm import llm

class ClarifyingQuestions(BaseModel):
    question: str = Field(description="Clarifying question asked by User, empty if user has no further questions to ask")
    complete: bool = Field(description="True if user is done with clarifying questions and want to proceed to discuss approach")

def clarity_loop_node(state) -> dict:
    questions = []
    user_input = interrupt("Do you have any clarifying questions regarding the problem?")

    while len(questions < 6):
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
            f"Reply to below clarifying question regarding the problem by User in simple and conscise language such that User can understand the problem better, DO NOT provide the solution to the problem in any case. After providing answer ask user if they have any other clarifying question\n"
            f"Clarification Question:{user_input_analysis.question}\n"
            f"Related Problem:{state['problem_description']}\n"
            f"Past Clarifying questions: {questions}"
        )
        user_input = interrupt(answer.content)
        questions.append(user_input_analysis.question)
    return {"clarity_questions": questions}


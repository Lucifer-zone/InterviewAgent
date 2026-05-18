from langgraph.types import interrupt
from pydantic import BaseModel, Field

from src.graph import State
from src.llm import llm


class UserCode(BaseModel):
    code: str = Field(description="The code block extracted verbatim from the user's input. Empty string if no code is present.")
    found: bool = Field(description="True if a code block was found in the input, False if the user sent text with no code.")


def ask_for_code(state: State) -> dict:
    user_code = interrupt(
        f"Let's move on to coding.\n\n"
        f"You can use LeetCode to write and test your code:\n"
        f"https://leetcode.com/problems/{state.problem_slug}/\n\n"
        f"Share your code once you're done."
    )

    for _ in range(2):
        result = llm.with_structured_output(UserCode).invoke(
            f"Extract any code block from the user's input.\n"
            f"Set found=True and populate code verbatim if a code block is present.\n"
            f"Set found=False and code='' if the input contains no code — "
            f"plain text descriptions or 'I'll write it now' style responses do not count.\n\n"
            f"User input:\n{user_code}"
        )
        if result.found and result.code:
            return {"code": result.code}

        user_code = interrupt(
            "I couldn't find any code in your message. "
            "Please paste your solution as a code block and try again."
        )

    return {"code": result.code}

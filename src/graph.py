from pydantic import BaseModel


class State(BaseModel):
    problem_slug: str
    problem_description: str
    target_pattern: str
    topic_tags: list[str]
    difficulty: str
    clarity_questions: list[str]
    approach_responses: list    # ← changed from approach: str
    code: str
    followup_answers: list
    pattern_summary: str

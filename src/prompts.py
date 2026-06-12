"""Central registry of all LLM prompts.

Every prompt sent to the LLM lives here as a function that takes the runtime
values it interpolates and returns the assembled prompt string. Node code calls
these instead of inlining prompt text, so prompt wording can be reviewed and
tuned in one place. User-facing `interrupt()` messages are not prompts and stay
in their nodes.
"""


# --- onboarding_node ---------------------------------------------------------

def extract_name(sentence: str) -> str:
    return "Extract the name of User from this sentence and return in expected format, Sentence: " + sentence


def extract_companies(companies: str, valid_companies: list[str]) -> str:
    return (
        f"Extract the target companies from:  {companies}\n"
        f"Only include companies from this list: {valid_companies}"
    )


def extract_level(sentence: str) -> str:
    return "Extract the User current level from sentence: " + sentence


def extract_focus_patterns(focus: str) -> str:
    return (
        f"Extract focus patterns from: '{focus}'\n"
        f"If user wants to skip or has no preference, set skipped=True\n"
        f"Valid patterns: dynamic-programming, graph, sliding-window, "
        f"tree, hash-table, array, stack, heap, two-pointers"
    )


def extract_weekly_goal(sentence: str) -> str:
    return "Extract the User's weekly goal from sentence: " + sentence


# --- clarity_loop_node -------------------------------------------------------

def clarity_intent_analysis(user_input: str) -> str:
    return (
        f"Analyse the User input\n"
        f"and see if user is asking any clarifying question about the problem\n"
        f"If user's intent is to not ask any further clarifying question\n"
        f"then set complete=True\n"
        f"User input: {user_input}"
    )


def clarity_answer(question: str, problem_description: str, past_questions: list[str]) -> str:
    return (
        f"Reply to the candidate's clarifying question about the problem in simple and concise language. "
        f"DO NOT reveal the solution. After answering, ask if they have any other clarifying questions.\n\n"
        f"Clarifying question: {question}\n"
        f"Problem:\n{problem_description}\n\n"
        f"Past clarifying questions: {past_questions}"
    )


# --- ask_approach_node -------------------------------------------------------

def approach_analysis(problem_description: str, history_context: str, attempt_number: int, user_approach: str) -> str:
    return (
        f"You are evaluating a candidate's approach to a coding problem in a technical interview.\n\n"
        f"Problem:\n{problem_description}\n\n"
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


def approach_socratic_feedback(problem_description: str, history_context: str, user_approach: str, counterexample: str, reason: str) -> str:
    return (
        f"You are an interview coach giving Socratic feedback on a candidate's approach to a coding problem.\n"
        f"Guide them toward the correct approach through hints and questions — NEVER reveal the solution or optimal algorithm.\n\n"
        f"Problem:\n{problem_description}\n\n"
        f"{history_context}\n\n"
        f"Candidate's current approach:\n{user_approach}\n\n"
        f"Counterexample where the approach fails:\n{counterexample}\n\n"
        f"What the approach does wrong on that input:\n{reason}\n\n"
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


# --- ask_for_code ------------------------------------------------------------

def extract_code(user_code: str) -> str:
    return (
        f"Extract any code block from the user's input.\n"
        f"Set found=True and populate code verbatim if a code block is present.\n"
        f"Set found=False and code='' if the input contains no code — "
        f"plain text descriptions or 'I'll write it now' style responses do not count.\n\n"
        f"User input:\n{user_code}"
    )


# --- probe_code_node ---------------------------------------------------------

def probe_decision(problem_description: str, code: str, prior: str) -> str:
    return (
        f"You are an interviewer probing a candidate's code.\n"
        f"Decide if another question is needed. If the code is solid "
        f"and previous answers were strong, set needs_more=False.\n\n"
        f"Problem:\n{problem_description}\n\n"
        f"Code:\n{code}\n\n"
        f"Already asked:\n{prior}"
    )


# --- analyze_patterns --------------------------------------------------------

def pattern_analysis(num_sessions: int, rows: list[str]) -> str:
    return (
        f"Analyze the user's performance across their last {num_sessions} coding interview practice sessions.\n"
        f"Identify specific patterns/topics they consistently handle well and ones they consistently struggle with.\n\n"
        f"RULES:\n"
        f"- Base strengths and weaknesses on the SCORES (clarity, approach, code), not on the feedback text.\n"
        f"- A weakness is only valid if the score for that dimension is consistently low (≤5) across multiple sessions.\n"
        f"- A single low score does not make a weakness — look for recurring trends across at least 3 sessions.\n"
        f"- Do NOT invent weaknesses that aren't reflected in the scores.\n\n"
        f"Sessions (most recent first):\n"
        + "\n".join(rows)
    )


# --- evaluate_node -----------------------------------------------------------

def score_clarity(problem_description: str, visible_description: str, clarity_questions: list[str]) -> str:
    return (
        f"Score the candidate's clarifying-question phase (0-10).\n\n"
        f"IMPORTANT CONTEXT: The candidate was shown the problem WITHOUT the Constraints section. "
        f"The full problem (including constraints) is provided below for your reference, but the candidate "
        f"could not see the constraints. Questions about input size, character set, value ranges, or any "
        f"other constraint are valid clarifying questions and must be credited, not penalized.\n\n"
        f"REQUIRED PROCESS — follow in order:\n"
        f"1. Identify what was genuinely ambiguous or unstated in the visible version (no constraints). "
        f"Anything in the Constraints section is automatically fair game.\n"
        f"2. Score based on how well the candidate's questions covered those gaps.\n\n"
        f"Scoring anchors:\n"
        f"- 9-10: Asked all the important genuinely ambiguous things; nothing significant left open.\n"
        f"- 7-8: Asked about the most important gaps; missed only minor ones.\n"
        f"- 5-6: Asked 1-2 relevant questions but missed the most important ambiguity.\n"
        f"- 3-4: Asked questions but they were all about things clearly visible in the problem, or entirely off-base.\n"
        f"- 0-2: Asked no questions or said they had none despite genuine ambiguities existing.\n\n"
        f"If the visible problem statement is comprehensive and leaves little genuinely ambiguous, "
        f"a candidate who asks 1-2 confirmatory questions and moves on should score 7+.\n\n"
        f"Full problem (for your reference — candidate saw this without the Constraints section):\n{problem_description}\n\n"
        f"What the candidate actually saw (no constraints):\n{visible_description}\n\n"
        f"Candidate's clarifying questions:\n{clarity_questions}"
    )


def score_approach(problem_description: str, approach_responses: list[dict]) -> str:
    return (
        f"Score the candidate's approach phase (0-10) using these criteria:\n"
        f"- Did they reach a correct approach quickly? (1st attempt → high, 5th+ → low)\n"
        f"- Was the approach logically sound?\n"
        f"- Did they consider time/space tradeoffs?\n"
        f"- How much coaching/probing was needed?\n\n"
        f"Problem:\n{problem_description}\n\n"
        f"Approach attempts:\n{approach_responses}"
    )


def score_code(problem_description: str, code: str, followup_answers: list[dict]) -> str:
    return (
        f"Score the candidate's code (0-10) using these criteria:\n\n"
        f"Primary (determines whether score is in the 0-8 range or can reach 9-10):\n"
        f"- Does the code correctly solve the problem?\n"
        f"- Is it efficient? Does it handle edge cases?\n"
        f"- Did they answer follow-up questions confidently and accurately?\n\n"
        f"Secondary — code quality (can only cost 1 point max; cannot push score below 9 on its own):\n"
        f"- Are variable and function names descriptive and meaningful?\n"
        f"- Is the code structured cleanly (no unnecessary nesting, no dead code)?\n"
        f"- For longer solutions, is logic broken into helper functions where it aids readability?\n\n"
        f"Scoring guide:\n"
        f"- 10: Correct, efficient, clean code quality, strong follow-ups.\n"
        f"- 9: Correct and efficient but minor code quality issues (e.g. terse names, slight messiness).\n"
        f"- 7-8: Correct but missing edge cases or suboptimal in complexity.\n"
        f"- 4-6: Partially correct or significant inefficiency.\n"
        f"- 0-3: Incorrect or does not compile.\n\n"
        f"Problem:\n{problem_description}\n\n"
        f"Code:\n{code}\n\n"
        f"Follow-up Q&A:\n{followup_answers}"
    )


def session_feedback(clarity, approach, code) -> str:
    return (
        f"Write feedback for the candidate's interview session, combining strengths, weaknesses, "
        f"and one actionable tip across all three phases. Use second person ('You did...'). Keep it to a short paragraph.\n\n"
        f"Clarity (score {clarity.score}/10):\n"
        f"  Strengths: {clarity.strengths}\n"
        f"  Weaknesses: {clarity.weaknesses}\n"
        f"  Tip: {clarity.tip}\n\n"
        f"Approach (score {approach.score}/10):\n"
        f"  Strengths: {approach.strengths}\n"
        f"  Weaknesses: {approach.weaknesses}\n"
        f"  Tip: {approach.tip}\n\n"
        f"Code (score {code.score}/10):\n"
        f"  Strengths: {code.strengths}\n"
        f"  Weaknesses: {code.weaknesses}\n"
        f"  Tip: {code.tip}"
    )

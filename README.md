# InterviewAgent

AI-powered mock technical interviewer that adapts problem selection to your skill level, target companies, and observed weaknesses. Built with Python, LangGraph, a pluggable LLM backend (Ollama or Gemini), SQLite, and Gradio.

## Demo
![Demo](demo.gif)

## What it does
- Pulls real LeetCode problems via GraphQL and picks one based on a rule-driven mix of monthly focus plan, target-company patterns, and the patterns where your recent average is lowest.
- Runs a full interview loop — clarifying questions, approach with Socratic counterexample-driven probes, coding, then complexity and code follow-ups — pausing on each turn via LangGraph `interrupt`.
- Scores each session across clarity, approach, and code (weighted 15/35/50) and stores the result in SQLite for trend analysis.
- Tracks per-company readiness for Glean, GitLab, Grafana, Supabase, and Cohere using a difficulty-alignment formula over the last 10 sessions.
- Detects recurring weaknesses across sessions and bumps difficulty up or down per pattern based on rolling performance.
- Resumes mid-session: state and chat history are checkpointed, so closing the browser does not lose your place.

## Architecture

```
                       ┌── (prefs exist) ──→ fetch_problem
START ─ route_entry ──┤
                       └── (first run) ──→ onboarding ──→ fetch_problem

fetch_problem → present_problem → clarity_loop → ask_approach
              → ask_for_code → probe_code → evaluate
              → analyze_patterns → show_feedback → END
```

- `onboarding` — one-time setup that captures name, target companies, level, focus patterns, and weekly goal via LLM-parsed free-text responses.
- `fetch_problem` — selects pattern + difficulty (see Key Design Decisions), queries LeetCode, ranks candidates by acceptance-rate sweet spot, picks the top unseen problem.
- `present_problem` — strips the LeetCode "Constraints" block and prints the problem; marks the slug as seen.
- `clarity_loop` — answers up to 6 clarifying questions in Socratic style, exits when the LLM decides the user is ready to move on.
- `ask_approach` — has the model trace the candidate's approach on example inputs, construct a counterexample, and probe with hints until correct or 6 attempts.
- `ask_for_code` — accepts a code block (verifies one is present, otherwise re-prompts up to twice).
- `probe_code` — always asks complexity first, then up to 2 follow-ups decided by the LLM based on the code.
- `evaluate` — scores clarity, approach, and code separately, writes feedback, persists the session, and recomputes company readiness.
- `analyze_patterns` — cross-session analysis over the last 20 sessions; identifies recurring strengths and weaknesses (no-op until 5+ sessions).
- `show_feedback` — formats the final scoreboard and feedback paragraph.

## Key Design Decisions

**Pattern and difficulty selection are rule-based, not LLM-driven.** The pattern picker reads a hardcoded monthly plan, the user's target-company focus areas, and the rolling average score over the last 3 sessions on the current pattern. If the rolling average crosses 8 and the current difficulty is at or above the highest bar across the user's target companies, it rotates to the weakest pattern from the candidate set. Difficulty bumps the same way: avg < 5 drops a level, 5–7 holds, > 7 promotes up to the company ceiling. This logic is deterministic, testable, and free — there is no value in burning an LLM call to do arithmetic over historical scores.

**State is intentionally lean.** The `State` Pydantic model only carries fields read by more than one node — `problem_description`, `clarity_questions`, `approach_responses`, `code`, `followup_answers`, `feedback`, scores. Anything that's only consumed inside one node (e.g. clarifying-question loop history while the loop is running) lives in local variables. Anything that needs to survive across sessions (preferences, session history, seen slugs) is written straight to SQLite. LangGraph replays nodes from the top on resume, so a thin state minimizes both checkpoint size and the surface area for replay bugs.

**SQLite for persistence, not in-state history.** Two reasons. First, LangGraph checkpoints are per-thread; cross-session analytics (pattern stats, company readiness, attempted-slug deduping) need to outlive the active thread. Second, the LLM-prompt assembly for `analyze_patterns` and the rule logic in `fetch_problem` both want SQL-shaped reads (`GROUP BY target_pattern`, `ORDER BY timestamp DESC LIMIT 10`), which is awkward to express against a Python state object. The checkpoint DB (`data/checkpoints.db`) and the app DB (`data/interview_agent.db`) are deliberately separate.

**Structured output via Pydantic, never raw JSON parsing.** Every LLM-driven decision (clarity-question detection, approach correctness, code extraction, scoring) goes through `llm.with_structured_output(SomeModel)`. The model is forced to populate typed fields like `correct: bool` and `counterexample: str`. This dodges the entire class of "the model returned ```json\n{...}\n``` and now I have to regex-parse it" bugs, and gives the prompt itself a clean shape — field descriptions act as inline instructions to the model.

**Company readiness uses a difficulty-alignment formula.** For each target company, take the candidate's last 10 sessions on patterns that company asks about. Each session contributes `overall_score × alignment × recency_weight`, where `alignment = min(1.0, problem_difficulty / company_bar)` (so a Medium problem under a Hard bar only counts for 2/3, but a Hard problem under a Medium bar isn't bonused — capped at 1.0), and recency weights linearly decay from 1.0 to 0.1 over the 10 sessions. Final score is the weighted average. This penalizes "I crushed Easy problems" inflation without overweighting one recent bad session.

## Tech Stack

| Tool | Why |
|---|---|
| Python 3 | Language |
| LangGraph | Stateful node graph with checkpointing and `interrupt`-based pause/resume — exactly the shape of a turn-based interview |
| LangChain (Ollama / Google GenAI) | Provider-agnostic LLM interface; swap models via `LLM_PROVIDER` env var without code changes |
| Pydantic | Structured LLM outputs and the `State` schema |
| SQLite | Local persistence for sessions, readiness, preferences, seen slugs — zero-setup, queryable, file-portable |
| Gradio | Web chat UI with markdown rendering and a persisted history file |
| LeetCode GraphQL | Source of real problems (no scraping, no static dataset) |
| requests | HTTP for the GraphQL calls |

## Database Schema

`sessions` — one row per completed interview.
```
id              TEXT PRIMARY KEY
timestamp       TEXT
problem_slug    TEXT
problem_title   TEXT
difficulty      TEXT          -- EASY / MEDIUM / HARD
acceptance_rate REAL
target_pattern  TEXT
topic_tags      TEXT          -- JSON array
clarity_score   INTEGER
approach_score  INTEGER
code_score      INTEGER
overall_score   INTEGER
feedback        TEXT
```

`company_readiness` — one row per company per evaluation.
```
id              TEXT PRIMARY KEY
timestamp       TEXT
company         TEXT
readiness_score REAL          -- 0.0 to 10.0
```

`user_preferences` — single-row table (id always 1).
```
id                  INTEGER PRIMARY KEY DEFAULT 1
name                TEXT
target_companies    TEXT       -- JSON array, e.g. ["Glean","GitLab"]
current_level       TEXT       -- beginner / intermediate / advanced
focus_patterns      TEXT       -- JSON array or NULL
weekly_goal         INTEGER
created_at          TEXT
updated_at          TEXT
```

A fourth `seen_slugs` table dedupes recently-served problems; it's cleared every 10 sessions so the pool refreshes.

## How to Run

```bash
git clone <repo-url>
cd InterviewAgent
pip3 install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY here if using the gemini provider
```

For the default (local Ollama):
```bash
ollama pull qwen2.5-coder:7b
python3 gradio_app.py
```

For cloud Gemini:
```bash
LLM_PROVIDER=gemini python3 gradio_app.py
```

CLI variants:
```bash
python3 main.py               # fresh session
python3 main.py --resume      # continue the paused session
python3 print_graph.py        # ASCII render of the graph
python3 -m pytest tests/      # unit tests
```

Override models via `OLLAMA_MODEL` or `GEMINI_MODEL`. Note `requirements.txt` currently lists only the bare minimum — you also need `gradio` and `langchain-ollama` installed depending on which entrypoint and provider you use.

## Project Structure

```
InterviewAgent/
├── gradio_app.py              # web UI entrypoint
├── main.py                    # CLI entrypoint
├── demo.py                    # smoke test for fetch_problem
├── print_graph.py             # ASCII graph dump
├── requirements.txt
├── .env.example
├── src/
│   ├── graph.py               # State schema, node wiring, checkpointer
│   ├── llm.py                 # provider switch, timing callbacks, cache
│   ├── db/
│   │   └── database.py        # SQLite schema + query helpers
│   ├── nodes/
│   │   ├── onboarding_node.py
│   │   ├── fetch_problem.py
│   │   ├── present_problem_node.py
│   │   ├── clarity_loop_node.py
│   │   ├── ask_approach.py
│   │   ├── ask_for_code.py
│   │   ├── probe_code.py
│   │   ├── evaluate_node.py
│   │   ├── analyze_patterns_node.py
│   │   └── show_feedback.py
│   └── tools/
│       └── leetcode_api.py    # GraphQL client
├── tests/
│   ├── test_db_helpers.py
│   └── test_fetch_problem.py
└── data/                      # SQLite DBs + gradio history (gitignored)
```

## Future Improvements
- Voice mode — speech-in / speech-out so the session feels closer to a real phone screen.
- Hint system — explicit "I'm stuck" command that surfaces graduated hints without ending the approach loop.
- Weekly digest — scheduled summary email of patterns practiced, readiness deltas, and a recommended focus for next week.
- MCP integration — expose problem-fetching and session history as MCP tools so the agent can be driven from other clients.
- System design mode — second graph for open-ended design rounds, with rubric-driven probing instead of counterexample-driven probing.

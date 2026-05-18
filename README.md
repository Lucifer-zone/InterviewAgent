# InterviewAgent

AI-powered mock technical interviewer built on LangGraph. Walks you through clarifying questions, approach refinement (Socratic probes), coding, follow-up probes, and a scored session summary.

## Run

```bash
# Web UI (recommended)
python3 gradio_app.py

# CLI — fresh session
python3 main.py

# CLI — resume the paused session
python3 main.py --resume

# Visualize the graph as ASCII
python3 print_graph.py

# Run tests
python3 -m pytest tests/
```

## Switch LLM provider

The default is local Ollama (`gemma4:26b`). Override per-run via env var — no code edit needed:

```bash
LLM_PROVIDER=ollama python3 gradio_app.py     # local Gemma via Ollama
LLM_PROVIDER=gemini python3 gradio_app.py     # cloud Gemini
```

Or change the default in [src/llm.py](src/llm.py) (also supports `OLLAMA_MODEL` / `GEMINI_MODEL` env overrides).

## Setup

```bash
pip3 install -r requirements.txt
cp .env.example .env   # then add GEMINI_API_KEY if you plan to use the gemini provider
```

For local Ollama, make sure the daemon is running and the model is pulled (`ollama pull gemma4:26b`).

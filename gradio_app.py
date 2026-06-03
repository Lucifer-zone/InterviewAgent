import io
import json
import os
import time
from contextlib import redirect_stdout

import gradio as gr
from langgraph.types import Command

from src.db.database import init_db
from src.graph import app, checkpointer
from src.llm import logger

_HISTORY_FILE = "data/gradio_history.json"


def _save_history(history: list):
    os.makedirs("data", exist_ok=True)
    with open(_HISTORY_FILE, "w") as f:
        json.dump(history, f)


def _load_history() -> list:
    try:
        with open(_HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


THREAD_ID = "gradio_session"
CONFIG = {"configurable": {"thread_id": THREAD_ID}}


def _invoke_step(input_val):
    """Drive the graph one step. Returns (captured_stdout, next_prompt or None, is_complete)."""
    kind = "Command(resume)" if isinstance(input_val, Command) else f"{type(input_val).__name__}"
    logger.info(f"Graph ⇢ invoke ({kind})")
    t0 = time.time()

    buf = io.StringIO()
    with redirect_stdout(buf):
        app.invoke(input_val, CONFIG)
    captured = buf.getvalue().strip()

    state = app.get_state(CONFIG)
    interrupts = [i.value for t in state.tasks for i in (t.interrupts or [])]
    pending_nodes = ", ".join(state.next) if state.next else "—"
    elapsed = time.time() - t0
    logger.info(f"Graph ✓ {elapsed:.1f}s | pending nodes: {pending_nodes} | interrupts: {len(interrupts)}")

    if interrupts:
        return captured, interrupts[0], False
    return captured, None, True


def _format_response(captured: str, prompt: str | None, complete: bool) -> str:
    parts = [p for p in [captured, prompt] if p]
    msg = "\n\n".join(parts)
    if complete:
        msg = (msg + "\n\n— Session complete —").strip() if msg else "— Session complete —"
    return msg


def _problem_block_from_state(sv: dict) -> str | None:
    """Reconstitute the problem display from persisted state — used on resume."""
    if not sv or not sv.get("problem_slug"):
        return None
    return (
        f"**Difficulty:** {sv.get('difficulty', '?')}  \n"
        f"**Problem:** {sv['problem_slug']}  \n\n"
        f"{sv.get('problem_description', '')}"
    )


def _initial_chatbot_value() -> list:
    init_db()
    state = app.get_state(CONFIG)
    pending = [i.value for t in state.tasks for i in (t.interrupts or [])]

    if pending:
        saved = _load_history()
        if saved:
            return saved
        # Fallback: no saved history, reconstruct minimal view
        parts = []
        block = _problem_block_from_state(state.values or {})
        if block:
            parts.append(block)
        parts.append(pending[0])
        first_msg = "\n\n".join(parts)
        history = [{"role": "assistant", "content": first_msg}]
        _save_history(history)  # persist so the next user reply doesn't drop the problem block
        return history

    checkpointer.delete_thread(THREAD_ID)
    _save_history([])
    captured, prompt, complete = _invoke_step({})
    first_msg = _format_response(captured, prompt, complete)
    history = [{"role": "assistant", "content": first_msg}]
    _save_history(history)
    return history


def new_session():
    yield [{
        "role": "assistant",
        "content": "⏳ Starting new session, fetching a new problem..."
    }]
    checkpointer.delete_thread(THREAD_ID)
    _save_history([])
    captured, prompt, complete = _invoke_step({})
    first_msg = _format_response(captured, prompt, complete)
    history = [{"role": "assistant", "content": first_msg}]
    _save_history(history)
    yield history


def respond(message: str):
    if not message.strip():
        yield "", _load_history()
        return

    saved = _load_history()
    with_user = saved + [{"role": "user", "content": message}]
    thinking = with_user + [{"role": "assistant", "content": "⏳ Thinking..."}]
    yield "", thinking  # user + loading in one update — renders before slow LLM call

    captured, prompt, complete = _invoke_step(Command(resume=message))
    response = _format_response(captured, prompt, complete)
    updated = with_user + [{"role": "assistant", "content": response}]
    _save_history(updated)
    yield "", updated  # replace loading with actual response


_CSS = """
/* ── Viewport lock ─────────────────────────────────── */
html, body {
    height: 100dvh !important;
    overflow: hidden !important;
    margin: 0 !important;
}

/* ── Outer container becomes a flex column ─────────── */
.gradio-container {
    max-width: 1200px !important;
    width: 96% !important;
    margin: 0 auto !important;
    height: 100dvh !important;
    padding: 8px 20px 0 !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
}

/* ── Pass flex height down through Gradio's wrappers ─ */
main.contain,
main.contain > .column {
    flex: 1 !important;
    min-height: 0 !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

/* ── Title / description blocks — shrink to content ── */
main.contain > .column > .block:not(#chatbot) {
    flex-shrink: 0 !important;
}

/* ── Input row — shrink to content ───────────────────── */
#input-row {
    flex-shrink: 0 !important;
    padding: 8px 0 !important;
}

/* ── Chatbot area fills ALL remaining space ─────────── */
#chatbot {
    flex: 1 !important;
    min-height: 0 !important;
    height: auto !important;
}

footer { display: none !important; }
.message-bubble-border { border-radius: 14px !important; }
#header-row { align-items: center !important; flex-shrink: 0 !important; padding: 4px 0 !important; }
#header-row h1 { margin: 0 !important; font-size: 1.35rem !important; }
#new-session-btn {
    background: #f97316 !important;
    border-color: #f97316 !important;
    color: #fff !important;
    white-space: nowrap !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
#new-session-btn:hover {
    background: #ea6c0a !important;
    border-color: #ea6c0a !important;
}
"""

_THEME = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate",
    font=gr.themes.GoogleFont("Inter"),
)

with gr.Blocks(title="InterviewAgent") as demo:
    with gr.Row(elem_id="header-row"):
        gr.Markdown("# 🧠 InterviewAgent", elem_id="header-title")
        new_session_btn = gr.Button("+ New Session", scale=0, variant="secondary", min_width=130, elem_id="new-session-btn")

    chatbot = gr.Chatbot(
        elem_id="chatbot",
        show_label=False,
        render_markdown=True,
        layout="bubble",
        avatar_images=(None, "https://api.dicebear.com/7.x/bottts/svg?seed=interview"),
        placeholder="<b>InterviewAgent</b><br>Type <code>ready</code> to begin your session.",
    )

    with gr.Row(elem_id="input-row"):
        msg_box = gr.Textbox(
            placeholder="Type a message...",
            container=False,
            scale=9,
            show_label=False,
            autofocus=True,
        )
        send_btn = gr.Button("Send ↩", scale=1, variant="primary", min_width=90)

    msg_box.submit(respond, inputs=[msg_box], outputs=[msg_box, chatbot])
    send_btn.click(respond, inputs=[msg_box], outputs=[msg_box, chatbot])
    new_session_btn.click(new_session, outputs=[chatbot])

    demo.load(fn=_initial_chatbot_value, outputs=[chatbot])


if __name__ == "__main__":
    demo.launch(theme=_THEME, css=_CSS)

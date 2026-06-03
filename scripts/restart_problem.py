"""Restart the gradio session on the SAME problem — wipes clarity/approach/code state."""

import io
import os
import sys
from contextlib import redirect_stdout

from src.graph import app, checkpointer


THREAD_ID = "gradio_session"
HISTORY_FILE = "data/gradio_history.json"


def main():
    config = {"configurable": {"thread_id": THREAD_ID}}
    state = app.get_state(config)
    v = state.values or {}

    if not v.get("problem_slug"):
        print("No active problem to restart on the gradio thread.")
        print("Run `./agent run` to start a fresh session.")
        sys.exit(0)

    snapshot = {
        "problem_slug": v.get("problem_slug"),
        "problem_description": v.get("problem_description"),
        "target_pattern": v.get("target_pattern"),
        "difficulty": v.get("difficulty"),
        "topic_tags": v.get("topic_tags") or [],
    }

    # Wipe the paused thread (drops saved interrupts + clarity history + everything past fetch_problem)
    checkpointer.delete_thread(THREAD_ID)

    # Re-seed the thread as if fetch_problem just ran. Next invoke continues into present_problem
    # → clarity_loop and pauses at the first clarifying-question interrupt.
    app.update_state(config, snapshot, as_node="fetch_problem")

    # Drive forward to the first clarity_loop interrupt so the thread is in a
    # genuinely "paused" state — otherwise gradio's _initial_chatbot_value sees no
    # pending interrupts and wipes the thread on next load.
    with redirect_stdout(io.StringIO()):
        app.invoke(None, config)

    # Clear the gradio chat history so the UI also starts fresh.
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

    print(f"Restarted on: {snapshot['problem_slug']} ({snapshot['difficulty']})")
    print("Refresh the gradio tab (or restart `./agent run`) to see the fresh chat.")


if __name__ == "__main__":
    main()

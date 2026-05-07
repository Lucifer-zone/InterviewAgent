import argparse
import select
import sys

from langgraph.types import Command

from src.db.database import init_db
from src.graph import app, checkpointer


THREAD_ID = "active"


def read_response() -> str:
    line = input()
    lines = [line]
    # Drain any further lines already buffered (typical of multi-line paste).
    while select.select([sys.stdin], [], [], 0.15)[0]:
        try:
            lines.append(input())
        except EOFError:
            break
    return "\n".join(lines)


def run_interview_session(resume: bool):
    init_db()

    config = {"configurable": {"thread_id": THREAD_ID}}

    if resume:
        state = app.get_state(config)
        has_pending = any(t.interrupts for t in state.tasks)
        if not has_pending:
            print("No paused session to resume. Starting a fresh session.\n")
            checkpointer.delete_thread(THREAD_ID)
            app.invoke({}, config)
        # else: paused session exists — drop into the loop, it'll surface the next interrupt
    else:
        # Fresh session: clear any prior thread state, then kick off
        checkpointer.delete_thread(THREAD_ID)
        app.invoke({}, config)

    while True:
        state = app.get_state(config)

        interrupt_msgs = [
            itr.value
            for t in state.tasks
            for itr in (t.interrupts or [])
        ]

        if not interrupt_msgs:
            break

        print(interrupt_msgs[0])
        print("\n> ", end="", flush=True)
        user_response = read_response()
        app.invoke(Command(resume=user_response), config)

    print("\n=== Interview session complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Resume the previous session instead of starting a new one")
    args = parser.parse_args()

    try:
        run_interview_session(resume=args.resume)
    except KeyboardInterrupt:
        print("\nSession interrupted.")

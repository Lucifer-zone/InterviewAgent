import uuid

from langgraph.types import Command

from src.db.database import init_db
from src.graph import app


def run_interview_session():
    init_db()

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    next_input = {}

    while True:
        app.invoke(next_input, config)
        state = app.get_state(config)

        interrupt_msgs = []
        for t in state.tasks:
            for itr in t.interrupts or []:
                interrupt_msgs.append(itr.value)

        if not interrupt_msgs:
            break

        print(interrupt_msgs[0])
        user_response = input("\n> ")
        next_input = Command(resume=user_response)

    print("\n=== Interview session complete ===")


if __name__ == "__main__":
    try:
        run_interview_session()
    except KeyboardInterrupt:
        print("\nSession interrupted.")

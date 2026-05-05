import json
from datetime import datetime
from src.db.database import init_db, get_connection, get_user_preferences
from src.nodes.fetch_problem import fetch_problem


def seed_default_prefs_if_empty():
    if get_user_preferences() is not None:
        return
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO user_preferences
           (id, name, target_companies, current_level, focus_patterns, weekly_goal, created_at, updated_at)
           VALUES (1, ?, ?, ?, NULL, 3, ?, ?)""",
        ("demo-user", json.dumps(["Glean"]), "intermediate", now, now),
    )
    conn.commit()
    conn.close()


def main():
    init_db()
    seed_default_prefs_if_empty()

    prefs = get_user_preferences()
    print("=== User preferences ===")
    print(json.dumps(prefs, indent=2))
    print()

    print("=== Running fetch_problem node ===")
    result = fetch_problem(None)

    if not result:
        print("No update returned (no prefs or no candidate problems).")
        return

    print()
    print(f"Selected slug    : {result['problem_slug']}")
    print(f"Pattern          : {result['target_pattern']}")
    print(f"Difficulty       : {result['difficulty']}")
    print(f"Topic tags       : {result['topic_tags']}")
    print()
    desc = result['problem_description'] or ""
    preview = desc[:400].replace("\n", " ")
    print("Description (first 400 chars):")
    print(preview)
    if len(desc) > 400:
        print(f"... [truncated, total {len(desc)} chars]")


if __name__ == "__main__":
    main()

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/interview_agent.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id              TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            problem_slug    TEXT NOT NULL,
            problem_title   TEXT NOT NULL,
            difficulty      TEXT NOT NULL,
            acceptance_rate REAL NOT NULL,
            target_pattern  TEXT NOT NULL,
            topic_tags      TEXT NOT NULL,
            clarity_score   INTEGER,
            approach_score  INTEGER,
            code_score      INTEGER,
            overall_score   INTEGER,
            feedback        TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_readiness (
            id              TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            company         TEXT NOT NULL,
            readiness_score REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id                  INTEGER PRIMARY KEY DEFAULT 1,
            name                TEXT NOT NULL,
            target_companies    TEXT NOT NULL,       -- JSON array: ["Glean", "GitLab"]
            current_level       TEXT NOT NULL,       -- beginner / intermediate / advanced
            focus_patterns      TEXT,                -- JSON array: ["dp", "graphs"] or null
            weekly_goal         INTEGER DEFAULT 3,   -- problems per week target
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_user_preferences():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_preferences LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user_preference(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_preferences (id, {}, updated_at, created_at, name, target_companies, current_level)
        VALUES (1, ?, datetime('now'), datetime('now'), '', '[]', 'beginner')
        ON CONFLICT(id) DO UPDATE SET {} = ?, updated_at = datetime('now')
        """.format(key, key),
        (value, value)
    )
    conn.commit()
    conn.close()


def get_attempted_slugs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT problem_slug FROM sessions")
    slugs = [row["problem_slug"] for row in cursor.fetchall()]
    conn.close()
    return slugs

def get_last_sessions(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_weakest_patterns(limit=3):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_tags, AVG(overall_score) as avg_score
        FROM sessions
        GROUP BY topic_tags
        ORDER BY avg_score ASC
        LIMIT ?
    """, (limit,))
    patterns = [row["topic_tags"] for row in cursor.fetchall()]
    conn.close()
    return patterns


def get_most_recent_session():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_sessions_for_pattern(pattern: str, limit: int = 3) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sessions WHERE target_pattern = ? ORDER BY timestamp DESC LIMIT ?",
        (pattern, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pattern_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            target_pattern,
            AVG(overall_score)  AS avg_score,
            MAX(timestamp)      AS last_attempted
        FROM sessions
        GROUP BY target_pattern
    """)
    rows = cursor.fetchall()
    conn.close()
    return {
        row["target_pattern"]: {
            "avg_score": row["avg_score"] or 0.0,
            "last_attempted": row["last_attempted"] or ""
        }
        for row in rows
    }


def get_session_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM sessions")
    count = cursor.fetchone()["count"]
    conn.close()
    return count

def create_session(values: dict):
    conn = get_connection()
    cursor = conn.cursor()
    columns = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)
    cursor.execute(
        f"INSERT INTO sessions ({columns}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    conn.commit()
    conn.close()


def create_company_readiness(values: dict):
    conn = get_connection()
    cursor = conn.cursor()
    columns = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)
    cursor.execute(
        f"INSERT INTO company_readiness ({columns}) VALUES ({placeholders})",
        tuple(values.values()),
    )
    conn.commit()
    conn.close()



if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")

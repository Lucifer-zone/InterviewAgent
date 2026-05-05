"""
Tests for database.py helper functions added for select_pattern.
Uses an in-memory SQLite DB to avoid touching the real data file.
"""
import sqlite3
import pytest
from unittest.mock import patch
from src.db.database import (
    get_most_recent_session,
    get_sessions_for_pattern,
    get_pattern_stats,
)


def make_in_memory_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE sessions (
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
            feedback        TEXT,
            pattern_summary TEXT
        )
    """)
    conn.commit()
    return conn


def insert_session(conn, id, timestamp, target_pattern, difficulty, overall_score):
    conn.execute(
        """INSERT INTO sessions
           (id, timestamp, problem_slug, problem_title, difficulty,
            acceptance_rate, target_pattern, topic_tags, overall_score)
           VALUES (?, ?, 'slug', 'title', ?, 0.5, ?, '[]', ?)""",
        (id, timestamp, difficulty, target_pattern, overall_score),
    )
    conn.commit()


@pytest.fixture
def db_conn():
    conn = make_in_memory_conn()
    with patch("src.db.database.get_connection", return_value=conn):
        yield conn
    conn.close()


# ─── get_most_recent_session ────────────────────────────────────────────────

class TestGetMostRecentSession:
    def test_returns_none_when_empty(self, db_conn):
        result = get_most_recent_session()
        assert result is None

    def test_returns_latest_by_timestamp(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 7)
        insert_session(db_conn, "2", "2024-01-03T10:00:00", "dp", "MEDIUM", 9)
        insert_session(db_conn, "3", "2024-01-02T10:00:00", "tree", "EASY", 5)

        result = get_most_recent_session()
        assert result["id"] == "2"
        assert result["target_pattern"] == "dp"

    def test_returns_dict(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 6)
        result = get_most_recent_session()
        assert isinstance(result, dict)
        assert "target_pattern" in result


# ─── get_sessions_for_pattern ───────────────────────────────────────────────

class TestGetSessionsForPattern:
    def test_returns_empty_when_no_match(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 7)
        result = get_sessions_for_pattern("dp")
        assert result == []

    def test_filters_by_pattern(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 7)
        insert_session(db_conn, "2", "2024-01-02T10:00:00", "dp", "MEDIUM", 9)
        insert_session(db_conn, "3", "2024-01-03T10:00:00", "graph", "MEDIUM", 8)

        result = get_sessions_for_pattern("graph")
        assert len(result) == 2
        assert all(r["target_pattern"] == "graph" for r in result)

    def test_returns_most_recent_first(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 5)
        insert_session(db_conn, "2", "2024-01-03T10:00:00", "graph", "EASY", 9)

        result = get_sessions_for_pattern("graph")
        assert result[0]["id"] == "2"

    def test_respects_limit(self, db_conn):
        for i in range(5):
            insert_session(db_conn, str(i), f"2024-01-0{i+1}T10:00:00", "graph", "EASY", 6)

        result = get_sessions_for_pattern("graph", limit=3)
        assert len(result) == 3

    def test_returns_list_of_dicts(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 7)
        result = get_sessions_for_pattern("graph")
        assert isinstance(result, list)
        assert isinstance(result[0], dict)


# ─── get_pattern_stats ──────────────────────────────────────────────────────

class TestGetPatternStats:
    def test_returns_empty_dict_when_no_sessions(self, db_conn):
        result = get_pattern_stats()
        assert result == {}

    def test_groups_by_target_pattern(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 6)
        insert_session(db_conn, "2", "2024-01-02T10:00:00", "dp", "MEDIUM", 9)

        result = get_pattern_stats()
        assert "graph" in result
        assert "dp" in result

    def test_avg_score_calculated_correctly(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 4)
        insert_session(db_conn, "2", "2024-01-02T10:00:00", "graph", "EASY", 8)

        result = get_pattern_stats()
        assert result["graph"]["avg_score"] == pytest.approx(6.0)

    def test_last_attempted_is_max_timestamp(self, db_conn):
        insert_session(db_conn, "1", "2024-01-01T10:00:00", "graph", "EASY", 6)
        insert_session(db_conn, "2", "2024-01-05T10:00:00", "graph", "EASY", 7)

        result = get_pattern_stats()
        assert result["graph"]["last_attempted"] == "2024-01-05T10:00:00"

    def test_null_score_treated_as_zero(self, db_conn):
        db_conn.execute(
            """INSERT INTO sessions
               (id, timestamp, problem_slug, problem_title, difficulty,
                acceptance_rate, target_pattern, topic_tags, overall_score)
               VALUES ('1', '2024-01-01', 'slug', 'title', 'EASY', 0.5, 'graph', '[]', NULL)"""
        )
        db_conn.commit()

        result = get_pattern_stats()
        assert result["graph"]["avg_score"] == 0.0

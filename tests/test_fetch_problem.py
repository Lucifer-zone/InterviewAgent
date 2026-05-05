"""
Tests for logic functions in fetch_problem.py.
All DB and API calls are mocked — no real DB or network needed.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.nodes.fetch_problem import (
    _pick_weakest_candidate,
    select_pattern,
    select_difficulty,
    get_company_max_difficulty_level,
    DIFFICULTY_ORDER,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_session(target_pattern, difficulty, overall_score, timestamp="2024-01-01T10:00:00"):
    return {
        "target_pattern": target_pattern,
        "difficulty": difficulty,
        "overall_score": overall_score,
        "timestamp": timestamp,
    }


def make_prefs(target_companies='["Glean"]', focus_patterns=None, current_level="INTERMEDIATE"):
    return {
        "target_companies": target_companies,
        "focus_patterns": focus_patterns,
        "current_level": current_level,
    }


# ─── _pick_weakest_candidate ────────────────────────────────────────────────

class TestPickWeakestCandidate:
    @patch("src.nodes.fetch_problem.get_pattern_stats")
    def test_returns_first_untested_pattern(self, mock_stats):
        mock_stats.return_value = {"graph": {"avg_score": 7.0, "last_attempted": "2024-01-01"}}
        result = _pick_weakest_candidate(["graph", "dp", "tree"], "graph")
        assert result == "dp"

    @patch("src.nodes.fetch_problem.get_pattern_stats")
    def test_returns_lowest_avg_score_when_all_tested(self, mock_stats):
        mock_stats.return_value = {
            "graph": {"avg_score": 8.0, "last_attempted": "2024-01-03"},
            "dp":    {"avg_score": 4.0, "last_attempted": "2024-01-01"},
            "tree":  {"avg_score": 6.0, "last_attempted": "2024-01-02"},
        }
        result = _pick_weakest_candidate(["graph", "dp", "tree"], "graph")
        assert result == "dp"

    @patch("src.nodes.fetch_problem.get_pattern_stats")
    def test_uses_last_attempted_as_tiebreaker(self, mock_stats):
        mock_stats.return_value = {
            "graph": {"avg_score": 8.0, "last_attempted": "2024-01-03"},
            "dp":    {"avg_score": 5.0, "last_attempted": "2024-01-02"},
            "tree":  {"avg_score": 5.0, "last_attempted": "2024-01-01"},
        }
        result = _pick_weakest_candidate(["graph", "dp", "tree"], "graph")
        assert result == "tree"

    @patch("src.nodes.fetch_problem.get_pattern_stats")
    def test_returns_current_pattern_when_only_candidate(self, mock_stats):
        mock_stats.return_value = {"graph": {"avg_score": 7.0, "last_attempted": "2024-01-01"}}
        result = _pick_weakest_candidate(["graph"], "graph")
        assert result == "graph"


# ─── get_company_max_difficulty_level ───────────────────────────────────────

class TestGetCompanyMaxDifficultyLevel:
    def test_returns_hard_when_one_company_is_hard(self):
        prefs = make_prefs(target_companies='["Glean", "Cohere"]')
        result = get_company_max_difficulty_level(prefs)
        assert result == DIFFICULTY_ORDER["HARD"]

    def test_returns_medium_for_all_medium_companies(self):
        prefs = make_prefs(target_companies='["Glean", "GitLab"]')
        result = get_company_max_difficulty_level(prefs)
        assert result == DIFFICULTY_ORDER["MEDIUM"]

    def test_defaults_to_medium_when_no_known_companies(self):
        prefs = make_prefs(target_companies='["UnknownCorp"]')
        result = get_company_max_difficulty_level(prefs)
        assert result == DIFFICULTY_ORDER["MEDIUM"]

    def test_defaults_to_medium_when_empty_list(self):
        prefs = make_prefs(target_companies='[]')
        result = get_company_max_difficulty_level(prefs)
        assert result == DIFFICULTY_ORDER["MEDIUM"]


# ─── select_pattern ─────────────────────────────────────────────────────────

class TestSelectPattern:
    def test_case_a_no_sessions_returns_first_candidate(self):
        prefs = make_prefs(focus_patterns='["graph", "dp"]')
        with patch("src.nodes.fetch_problem.get_most_recent_session", return_value=None), \
             patch("src.nodes.fetch_problem.get_pattern_stats", return_value={}):
            result = select_pattern(prefs)
            assert result == "graph"

    def test_case_b_fewer_than_3_sessions_returns_current(self):
        prefs = make_prefs(focus_patterns='["graph", "dp"]')
        recent = make_session("graph", "EASY", 9)
        with patch("src.nodes.fetch_problem.get_most_recent_session", return_value=recent), \
             patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=[recent]), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=2):
            result = select_pattern(prefs)
            assert result == "graph"

    def test_case_c_avg_below_8_returns_current(self):
        prefs = make_prefs(focus_patterns='["graph", "dp"]')
        recent = make_session("graph", "EASY", 7)
        sessions = [make_session("graph", "EASY", s) for s in [7, 7, 7]]
        with patch("src.nodes.fetch_problem.get_most_recent_session", return_value=recent), \
             patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=2):
            result = select_pattern(prefs)
            assert result == "graph"

    def test_case_d_avg_above_8_difficulty_below_bar_returns_current(self):
        prefs = make_prefs(focus_patterns='["graph", "dp"]')
        recent = make_session("graph", "EASY", 9)
        sessions = [make_session("graph", "EASY", 9) for _ in range(3)]
        with patch("src.nodes.fetch_problem.get_most_recent_session", return_value=recent), \
             patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=2):
            # EASY=1 < MEDIUM bar=2 → stay
            result = select_pattern(prefs)
            assert result == "graph"

    def test_case_e_avg_above_8_at_bar_switches_pattern(self):
        prefs = make_prefs(focus_patterns='["graph", "dp"]')
        recent = make_session("graph", "MEDIUM", 9)
        sessions = [make_session("graph", "MEDIUM", 9) for _ in range(3)]
        stats = {
            "graph": {"avg_score": 9.0, "last_attempted": "2024-01-03"},
            "dp":    {"avg_score": 4.0, "last_attempted": "2024-01-01"},
        }
        with patch("src.nodes.fetch_problem.get_most_recent_session", return_value=recent), \
             patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=2), \
             patch("src.nodes.fetch_problem.get_pattern_stats", return_value=stats):
            result = select_pattern(prefs)
            assert result == "dp"

    def test_uses_company_focus_when_no_focus_patterns(self):
        prefs = make_prefs(target_companies='["Glean"]', focus_patterns=None)
        with patch("src.nodes.fetch_problem.get_most_recent_session", return_value=None), \
             patch("src.nodes.fetch_problem.get_pattern_stats", return_value={}):
            result = select_pattern(prefs)
            # Glean focus = ["graph", "heap", "sliding-window"] → first one returned
            assert result in ["graph", "heap", "sliding-window"]


# ─── select_difficulty ──────────────────────────────────────────────────────

class TestSelectDifficulty:
    @patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=[])
    def test_case_a_no_sessions_beginner_returns_easy(self, _):
        result = select_difficulty("graph", "BEGINNER", make_prefs())
        assert result == "EASY"

    @patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=[])
    def test_case_a_no_sessions_intermediate_returns_medium(self, _):
        result = select_difficulty("graph", "INTERMEDIATE", make_prefs())
        assert result == "MEDIUM"

    @patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=[])
    def test_case_a_no_sessions_advanced_returns_medium(self, _):
        result = select_difficulty("graph", "ADVANCED", make_prefs())
        assert result == "MEDIUM"

    @patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=[])
    def test_case_a_unknown_level_defaults_to_easy(self, _):
        result = select_difficulty("graph", "UNKNOWN", make_prefs())
        assert result == "EASY"

    def test_case_b_avg_below_5_drops_one_level(self):
        sessions = [make_session("graph", "MEDIUM", s) for s in [3, 4, 4]]
        with patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=3):
            result = select_difficulty("graph", "INTERMEDIATE", make_prefs())
            assert result == "EASY"

    def test_case_b_stays_at_easy_when_already_easy(self):
        sessions = [make_session("graph", "EASY", s) for s in [2, 3, 3]]
        with patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=3):
            result = select_difficulty("graph", "BEGINNER", make_prefs())
            assert result == "EASY"

    def test_case_c_avg_5_to_7_stays_same(self):
        sessions = [make_session("graph", "MEDIUM", s) for s in [5, 6, 7]]
        with patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=3):
            result = select_difficulty("graph", "INTERMEDIATE", make_prefs())
            assert result == "MEDIUM"

    def test_case_d_avg_above_7_increases_level(self):
        sessions = [make_session("graph", "EASY", s) for s in [8, 9, 9]]
        with patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=3):
            result = select_difficulty("graph", "BEGINNER", make_prefs())
            assert result == "MEDIUM"

    def test_case_d_capped_at_company_bar(self):
        sessions = [make_session("graph", "MEDIUM", s) for s in [9, 9, 9]]
        with patch("src.nodes.fetch_problem.get_sessions_for_pattern", return_value=sessions), \
             patch("src.nodes.fetch_problem.get_company_max_difficulty_level", return_value=2):
            # company bar is MEDIUM=2, current is MEDIUM=2 → can't go higher
            result = select_difficulty("graph", "INTERMEDIATE", make_prefs())
            assert result == "MEDIUM"

import json
from src.graph import State
from src.db.database import (
    get_user_preferences,
    get_attempted_slugs,
    get_most_recent_session,
    get_sessions_for_pattern,
    get_pattern_stats,
)
from src.tools.leetcode_api import fetch_problems, fetch_problem_description

DIFFICULTY_REVERSE = {1: "EASY", 2: "MEDIUM", 3: "HARD"}
LEVEL_TO_DIFFICULTY = {"BEGINNER": "EASY", "INTERMEDIATE": "MEDIUM", "ADVANCED": "MEDIUM"}
DIFFICULTY_ORDER = {"EASY": 1, "MEDIUM": 2, "HARD": 3}

COMPANY_BARS = {
    "Glean": {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["graph", "heap-priority-queue", "sliding-window"]},
    "GitLab": {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["array", "string", "hash-table"]},
    "Grafana": {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["array", "hash-table", "stack"]},
    "Supabase": {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["tree", "graph", "hash-table"]},
    "Cohere": {"difficulty": DIFFICULTY_ORDER["HARD"], "focus": ["dynamic-programming", "graph", "tree"]},
}


def _pick_weakest_candidate(candidates, current_pattern):
    stats = get_pattern_stats()
    untested = [p for p in candidates if p not in stats]
    if untested:
        return untested[0]

    weakest = [
        (p, stats[p]['avg_score'], stats[p]['last_attempted'])
        for p in candidates if p != current_pattern
    ]
    if not weakest:
        return current_pattern

    weakest.sort(key=lambda x: (x[1], x[2]))
    return weakest[0][0]


def get_company_max_difficulty_level(prefs):
    company_difficulty_levels = [
        COMPANY_BARS[c]['difficulty']
        for c in json.loads(prefs.get('target_companies'))
        if c in COMPANY_BARS
    ]
    return max(company_difficulty_levels, default=DIFFICULTY_ORDER["MEDIUM"])


def select_pattern(prefs):
    focus_patterns = json.loads(prefs.get("focus_patterns") or "[]")
    company_focus = []
    for c in json.loads(prefs.get('target_companies')):
        if c in COMPANY_BARS:
            company_focus.extend(COMPANY_BARS[c]["focus"])
    company_focus = list(set(company_focus))

    if focus_patterns:
        candidates = focus_patterns
    elif company_focus:
        candidates = company_focus
    else:
        candidates = list(get_pattern_stats().keys())

    if not candidates:
        return "array"

    recent_session = get_most_recent_session()
    current_pattern = recent_session.get("target_pattern") if recent_session else None

    if not current_pattern:
        return candidates[0]

    sessions = get_sessions_for_pattern(current_pattern, limit=3)

    if len(sessions) < 3:
        return current_pattern

    avg = sum(s.get('overall_score', 0) for s in sessions) / len(sessions)
    current_difficulty = DIFFICULTY_ORDER.get(sessions[0]['difficulty'].upper(), 0)
    max_difficulty_level = get_company_max_difficulty_level(prefs)

    if avg <= 8:
        return current_pattern
    if avg > 8 and current_difficulty < max_difficulty_level:
        return current_pattern
    elif avg > 8 and current_difficulty >= max_difficulty_level:
        return _pick_weakest_candidate(candidates, current_pattern)


def select_difficulty(current_pattern, current_level, prefs):
    sessions = get_sessions_for_pattern(current_pattern, limit=3)

    if len(sessions) < 3:
        return LEVEL_TO_DIFFICULTY.get(current_level.upper(), "EASY")

    current_difficulty = DIFFICULTY_ORDER.get(sessions[0]['difficulty'].upper(), 1)
    avg_score = sum(session.get('overall_score', 0) for session in sessions) / len(sessions)

    if avg_score < 5 and current_difficulty > 1:
        return DIFFICULTY_REVERSE[current_difficulty - 1]
    elif avg_score >= 5 and avg_score <= 7:
        return DIFFICULTY_REVERSE[current_difficulty]
    elif avg_score > 7 and current_difficulty < get_company_max_difficulty_level(prefs):
        return DIFFICULTY_REVERSE[current_difficulty + 1]

    return DIFFICULTY_REVERSE[current_difficulty]


def fetch_problem(state: State) -> dict:
    prefs = get_user_preferences()

    if prefs is None:
        return {}

    target_pattern = select_pattern(prefs)
    target_difficulty = select_difficulty(
        target_pattern,
        prefs.get("current_level"),
        prefs,
    )

    print(f"Selected pattern: {target_pattern}, difficulty: {target_difficulty}")

    problem = fetch_problems(target_pattern, target_difficulty)
    attempted_slugs = get_attempted_slugs()
    available = [p for p in problem if p['titleSlug'] not in attempted_slugs]

    if not available:
        return {}

    selected = available[0]

    return {
        "problem_slug": selected['titleSlug'],
        "problem_description": fetch_problem_description(selected['titleSlug']),
        "target_pattern": target_pattern,
        "difficulty": target_difficulty,
        "topic_tags": [t['slug'] for t in selected['topicTags']],
    }

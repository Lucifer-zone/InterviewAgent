from src.db.database import get_sessions_for_patterns

_RECENCY_WEIGHTS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]

DIFFICULTY_ORDER = {"EASY": 1, "MEDIUM": 2, "HARD": 3}

COMPANY_BARS = {
    "Glean":    {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["graph", "heap-priority-queue", "sliding-window"]},
    "GitLab":   {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["array", "string", "hash-table"]},
    "Grafana":  {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["array", "hash-table", "stack"]},
    "Supabase": {"difficulty": DIFFICULTY_ORDER["MEDIUM"], "focus": ["tree", "graph", "hash-table"]},
    "Cohere":   {"difficulty": DIFFICULTY_ORDER["HARD"],   "focus": ["dynamic-programming", "graph", "tree"]},
}


def calculate_company_readiness(company: str, bar: int) -> float:
    patterns = COMPANY_BARS.get(company, {}).get("focus", [])
    sessions = get_sessions_for_patterns(patterns, limit=10)

    if not sessions:
        return 0.0

    readiness_scores = []
    for s in sessions:
        diff_level = DIFFICULTY_ORDER.get(s['difficulty'].upper(), 1)
        alignment = min(1.0, diff_level / bar)
        readiness_scores.append(s['overall_score'] * alignment)

    weights = _RECENCY_WEIGHTS[:len(readiness_scores)]
    weighted_sum = sum(r * w for r, w in zip(readiness_scores, weights))
    return round(weighted_sum / sum(weights), 2)

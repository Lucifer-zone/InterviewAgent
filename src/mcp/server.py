from typing import Annotated

from mcp.server.fastmcp import FastMCP
from src.db.database import (
    get_pattern_stats as _get_pattern_stats,
    get_last_sessions as _get_last_sessions,
    get_sessions_for_pattern as _get_sessions_for_pattern,
    get_weakest_patterns as _get_weakest_patterns,
    get_user_preferences as _get_user_preferences,
)
from src.utils.readiness import calculate_company_readiness, COMPANY_BARS

mcp = FastMCP("interview-data")


@mcp.tool()
def get_pattern_stats() -> dict:
    """Returns average score and last attempted date for each pattern the user has practiced."""
    return _get_pattern_stats()


@mcp.tool()
def get_last_sessions(limit: Annotated[int, "Number of sessions to return"] = 10) -> list:
    """Returns the most recent interview sessions with scores for clarity, approach, code, and overall."""
    return _get_last_sessions(limit)


@mcp.tool()
def get_sessions_for_pattern(
    pattern: Annotated[str, "Pattern to fetch sessions for (e.g. 'stack', 'dynamic-programming')"],
    limit: Annotated[int, "Number of sessions to return"] = 3,
) -> list:
    """Returns recent sessions for a specific pattern."""
    return _get_sessions_for_pattern(pattern, limit)


@mcp.tool()
def get_weakest_patterns(limit: Annotated[int, "Number of weakest patterns to return"] = 3) -> list:
    """Returns the patterns with the lowest average scores — the ones most in need of practice."""
    return _get_weakest_patterns(limit)


@mcp.tool()
def get_user_preferences() -> dict:
    """Returns the user's profile: name, target companies, current level, focus patterns, and weekly goal."""
    return _get_user_preferences()


@mcp.tool()
def get_company_readiness() -> dict:
    """Returns readiness score (0-10) for each target company based on recent session performance."""
    prefs = _get_user_preferences()
    if not prefs:
        return {}
    import json
    target_companies = json.loads(prefs.get("target_companies") or "[]")
    return {
        company: calculate_company_readiness(
            company,
            COMPANY_BARS.get(company, {}).get("difficulty", 2),
        )
        for company in target_companies
        if company in COMPANY_BARS
    }


if __name__ == "__main__":
    mcp.run()

import requests

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"


def fetch_problems(tag=None, difficulty=None, limit=10):
    query = """
    query problemsetQuestionListV2(
        $categorySlug: String,
        $limit: Int,
        $filters: QuestionFilterInput
    ) {
        problemsetQuestionListV2(
            categorySlug: $categorySlug
            limit: $limit
            filters: $filters
        ) {
            questions {
                title
                titleSlug
                difficulty
                acRate
                paidOnly
                topicTags {
                    name
                    slug
                }
            }
        }
    }
    """

    filters = {"filterCombineType": "ALL"}
    if difficulty:
        filters["difficultyFilter"] = {
            "difficulties": [difficulty.upper()],
            "operator": "IS",
        }
    if tag:
        filters["topicFilter"] = {
            "topicSlugs": [tag],
            "operator": "IS",
        }

    variables = {
        "categorySlug": "algorithms",
        "limit": limit,
        "filters": filters
    }

    response = requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": query, "variables": variables}
    )

    data = response.json()
    if "data" not in data or data["data"] is None:
        print("LeetCode API error:", data)
        return []
    return data["data"]["problemsetQuestionListV2"]["questions"]


def fetch_problem_description(title_slug):
    query = """
    query getQuestionDetail($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            content
            exampleTestcaseList
            hints
        }
    }
    """

    response = requests.post(
        LEETCODE_GRAPHQL_URL,
        json={"query": query, "variables": {"titleSlug": title_slug}}
    )

    data = response.json()
    return data["data"]["question"]["content"]


if __name__ == "__main__":
    # Quick test
    problems = fetch_problems(tag="two-pointers", difficulty="MEDIUM", limit=3)
    for p in problems:
        print(f"{p['title']} — {p['difficulty']} — {p['acRate'] * 100:.1f}%")

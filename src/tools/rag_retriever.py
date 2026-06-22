
from src.tools import vector_store


def retrieve_problems(
        target_pattern: str,
        difficulty: str,
        attempted_slugs: list,
        k: int = 10
):
    """
    Searches vector store for problems matching
    the target pattern and difficulty.
    Returns top matches excluding already attempted.
    """

    query = f"""
    {difficulty} difficulty problem 
    about {target_pattern} 
    interview coding problem
    """

    results = vector_store.vectorstore.similarity_search(query, k)

    # Filter out attempted and wrong difficulty
    available = [
        r for r in results
        if r.metadata['slug'] not in attempted_slugs
        and r.metadata['difficulty'].upper() == difficulty.upper()
    ]
    
    return available
# src/tools/index_problems.py
import json
import re

from langchain.schema import Document

from src.tools.vector_store import vectorstore


def strip_html(html: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r'<[^>]+>', '', html or '')


def index_problem(problem: dict):
    """
    Converts one problem into a Document and stores it.
    The text we embed is what similarity search runs against.
    The metadata is what we get back after retrieval.
    """
    
    # What gets embedded — rich text for better retrieval
    embed_text = f"""
    Title: {problem['title']}
    Difficulty: {problem['difficulty']}
    Patterns: {', '.join(problem['topic_tags'])}
    Description: {problem['description_text']}
    """
    # Note: description_text is HTML-stripped version
    # html_content is the original HTML kept for display
    
    doc = Document(
        page_content=embed_text,
        metadata={
            "slug":          problem['slug'],
            "title":         problem['title'],
            "difficulty":    problem['difficulty'],
            "topic_tags":    json.dumps(problem['topic_tags']),
            "acceptance_rate": problem['acceptance_rate'],
            "html_content":  problem['html_content'],  # full HTML for display
            "description_text": strip_html(problem['content'])[:500],  # store truncated

        }
    )
    
    vectorstore.add_documents([doc])
"""get_project_knowledge — reads from project knowledge file."""

import os

from langchain_core.tools import tool

KNOWLEDGE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", "project_knowledge.txt"
)


@tool
async def get_project_knowledge(query: str) -> str:
    """Search project knowledge base for relevant information.

    Args:
        query: The topic or question to search for in the knowledge base.
    """
    if not os.path.exists(KNOWLEDGE_FILE):
        return "База знаний проекта пока не заполнена."

    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple keyword-based search (stub implementation)
    lines = content.split("\n")
    relevant = [line for line in lines if query.lower() in line.lower()]

    if relevant:
        return "\n".join(relevant[:5])
    return "Не найдено релевантной информации в базе знаний."

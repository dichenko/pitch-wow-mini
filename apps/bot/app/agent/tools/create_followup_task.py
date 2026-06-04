"""create_followup_task — stub tool for creating follow-up tasks."""

from langchain_core.tools import tool


@tool
async def create_followup_task(title: str, description: str = "") -> str:
    """Create a follow-up task or reminder for the team.

    Args:
        title: Short title for the task.
        description: Optional detailed description of the task.
    """
    # TODO: Implement actual task creation (e.g., send to task management system)
    return f"Задача создана: {title}"

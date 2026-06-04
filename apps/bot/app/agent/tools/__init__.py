"""Tool registry — all tools registered here for the LangChain agent."""

from apps.bot.app.agent.tools.create_followup_task import create_followup_task
from apps.bot.app.agent.tools.get_project_knowledge import get_project_knowledge
from apps.bot.app.agent.tools.save_lead import save_lead
from apps.bot.app.agent.tools.send_to_admin import send_to_admin


def get_all_tools() -> list:
    """Return all tools registered for the LangChain agent.

    send_to_admin is always registered (REQUIRED default tool).
    Other tools are template stubs demonstrating the pattern.

    To add a new tool:
    1. Create a new file in tools/ directory
    2. Define the tool using @tool decorator
    3. Import and add it to this list
    """
    return [
        send_to_admin,  # REQUIRED — always registered
        save_lead,
        get_project_knowledge,
        create_followup_task,
    ]

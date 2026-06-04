"""save_lead — stub tool for saving lead information."""

from langchain_core.tools import tool


@tool
async def save_lead(name: str, phone: str, comment: str = "") -> str:
    """Save a potential client's contact information as a lead.

    Args:
        name: The person's name.
        phone: The person's phone number.
        comment: Optional additional information about the lead.
    """
    # TODO: Implement actual lead saving to CRM or database
    return f"Лид сохранён: {name}, {phone}"

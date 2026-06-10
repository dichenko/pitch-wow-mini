"""User language profile helpers for Telegram bot flows."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from sqlalchemy import select

from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import UserProfile
from packages.shared.utils.languages import (
    DEFAULT_LANGUAGE,
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    Language,
    normalize_preferred_language,
)

LANGUAGE_SELECTION_TEXT = (
    "Выберите язык общения / Muloqot tilini tanlang / Choose your language:"
)

LANGUAGE_REQUIRED_TEXT: dict[Language, str] = {
    "ru": "Сначала выберите язык общения.",
    "uz": "Avval muloqot tilini tanlang.",
    "en": "Please choose your language first.",
}
def language_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LANGUAGE_LABELS[language],
                    callback_data=f"language:{language}",
                )
            ]
            for language in SUPPORTED_LANGUAGES
        ]
    )


async def answer_language_selection(message: Message) -> None:
    await message.answer(
        LANGUAGE_SELECTION_TEXT,
        reply_markup=language_selection_keyboard(),
    )


async def upsert_user_profile(user: User) -> UserProfile:
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.tg_id == user.id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = UserProfile(tg_id=user.id)
            session.add(profile)

        profile.first_name = user.first_name
        profile.last_name = user.last_name
        profile.username = user.username
        profile.language_code = user.language_code

        await session.commit()
        await session.refresh(profile)
        return profile


async def get_preferred_language(user: User) -> Language | None:
    profile = await upsert_user_profile(user)
    return normalize_preferred_language(profile.preferred_language)


async def require_preferred_language(message: Message) -> Language | None:
    if not message.from_user:
        return None

    language = await get_preferred_language(message.from_user)
    if language is None:
        await answer_language_selection(message)
        return None
    return language


async def set_preferred_language(user: User, language: str) -> Language:
    normalized = normalize_preferred_language(language)
    if normalized is None:
        raise ValueError(f"Unsupported language: {language}")

    async with async_session_factory() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.tg_id == user.id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = UserProfile(tg_id=user.id)
            session.add(profile)

        profile.preferred_language = normalized
        profile.first_name = user.first_name
        profile.last_name = user.last_name
        profile.username = user.username
        profile.language_code = user.language_code

        await session.commit()
        return normalized

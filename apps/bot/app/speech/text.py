"""Text preparation helpers for speech synthesis."""

import re


def prepare_text_for_tts(text: str) -> str:
    prepared = text.strip()
    prepared = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", prepared)
    prepared = re.sub(r"https?://\S+", "", prepared)
    prepared = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", "", prepared)
    prepared = prepared.replace("**", "")
    prepared = prepared.replace("__", "")
    prepared = prepared.replace("`", "")
    prepared = prepared.replace("\u2022", ". ")
    prepared = prepared.replace("-", " ")
    prepared = re.sub(r"\s+", " ", prepared)
    return prepared.strip()


def prepare_russian_text_for_tts(text: str) -> str:
    prepared = prepare_text_for_tts(text)
    prepared = prepared.replace("₽", " рублей")
    prepared = prepared.replace("$", " долларов")
    prepared = prepared.replace("%", " процентов")
    prepared = re.sub(r"\s+", " ", prepared)
    return prepared.strip()


def truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text

    truncated = text[:max_chars].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space].rstrip()
    return truncated

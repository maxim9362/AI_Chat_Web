# Этот файл разбивает Markdown по абзацам на перекрывающиеся текстовые фрагменты.

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class TextChunk:
    content: str
    char_count: int
    chunk_index: int


def chunk_markdown(
    text: str,
    min_chars: int = 1200,
    max_chars: int = 1800,
    overlap_chars: int = 250,
) -> list[TextChunk]:
    if min_chars < 1 or max_chars < min_chars:
        raise ValueError("Некорректные границы размера чанка.")
    if not 200 <= overlap_chars <= 300:
        raise ValueError("Перекрытие должно быть от 200 до 300 символов.")
    if overlap_chars >= max_chars:
        raise ValueError("Перекрытие должно быть меньше максимального чанка.")

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text.strip())
        if paragraph.strip()
    ]
    if not paragraphs:
        return []

    max_unit_chars = max_chars - overlap_chars - 2
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(
            _split_long_paragraph(
                paragraph=paragraph,
                max_chars=max_unit_chars,
                overlap_chars=overlap_chars,
            )
        )

    chunk_texts: list[str] = []
    current = ""

    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunk_texts.append(current)
            overlap = _tail_overlap(current, overlap_chars)
            current = f"{overlap}\n\n{unit}".strip()
        else:
            current = unit

    if current:
        chunk_texts.append(current)

    return [
        TextChunk(
            content=content,
            char_count=len(content),
            chunk_index=index,
        )
        for index, content in enumerate(chunk_texts)
    ]


def _split_long_paragraph(
    paragraph: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    parts: list[str] = []
    remaining = paragraph

    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at < max_chars // 2:
            split_at = max_chars

        part = remaining[:split_at].strip()
        parts.append(part)
        next_start = max(split_at - overlap_chars, 0)
        remaining = remaining[next_start:].strip()

    if remaining:
        parts.append(remaining)

    return parts


def _tail_overlap(text: str, overlap_chars: int) -> str:
    if len(text) <= overlap_chars:
        return text

    tail = text[-overlap_chars:]
    first_space = tail.find(" ")
    if first_space != -1:
        tail = tail[first_space + 1 :]
    return tail.strip()

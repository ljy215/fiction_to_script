import re
from dataclasses import dataclass


MINIMUM_CHAPTER_COUNT = 3

_CHINESE_NUMERAL = "零〇一二两三四五六七八九十百千万"
_CHAPTER_HEADING_RE = re.compile(
    rf"^\s*(?:第[\d{_CHINESE_NUMERAL}]+[章节回卷集部篇](?:\s*[^\n]{{0,60}})?|"
    r"chapter\s+\d+(?:\s*[:：.\-]?\s*[^\n]{0,60})?)\s*$",
    re.IGNORECASE,
)
_CHINESE_BODY_SENTENCE_RE = re.compile(rf"^\s*第[\d{_CHINESE_NUMERAL}]+[章节回卷集部篇][的了在是中]")


@dataclass(frozen=True)
class ParsedChapter:
    order: int
    title: str
    content_text: str

    @property
    def content_length(self) -> int:
        return len(self.content_text)


def _is_heading(line: str) -> bool:
    candidate = line.strip()
    if not candidate or len(candidate) > 80:
        return False
    if _CHINESE_BODY_SENTENCE_RE.match(candidate):
        return False
    return bool(_CHAPTER_HEADING_RE.match(candidate))


def recognize_chapters(text: str) -> list[ParsedChapter]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if _is_heading(line):
            headings.append((index, line.strip()))

    if not headings:
        content = text.strip()
        return [ParsedChapter(order=1, title="Full Text", content_text=content)] if content else []

    chapters: list[ParsedChapter] = []
    for order, (line_index, title) in enumerate(headings, start=1):
        next_line_index = headings[order][0] if order < len(headings) else len(lines)
        body = "\n".join(lines[line_index + 1 : next_line_index]).strip()
        chapters.append(
            ParsedChapter(
                order=order,
                title=title,
                content_text=body or title,
            )
        )

    return chapters


def has_minimum_chapters(chapter_count: int) -> bool:
    return chapter_count >= MINIMUM_CHAPTER_COUNT

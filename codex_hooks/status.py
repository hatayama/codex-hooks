import re

OPTION_LINE_PATTERN = re.compile(r"^(?:\d+[.)]|[-*])\s")
OPTION_INTRO_PATTERN = re.compile(
    r"\b(?:choose|select|pick)\b|\boptions?\b|\balternatives?\b",
    re.IGNORECASE,
)
QUESTION_ENDING = ("?", "？")
MAX_TRAILING_SUPPLEMENTAL_LINES = 2
JAPANESE_OPTION_INTRO_MARKERS = ("選んで", "選択", "オプション")


def extract_output_text(payload: dict) -> str:
    content: list[dict] = payload.get("content", [])
    lines: list[str] = []
    for item in content:
        item_type: str = item.get("type", "")
        if item_type not in {"output_text", "input_text"}:
            continue
        text: str = item.get("text", "")
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def normalize_lines(message: str) -> list[str]:
    lines: list[str] = []
    for raw_line in message.splitlines():
        line: str = raw_line.strip()
        if not line:
            continue
        if line.startswith("```"):
            continue
        lines.append(line)
    return lines


def is_option_line(line: str) -> bool:
    return OPTION_LINE_PATTERN.match(line) is not None


def is_option_intro_line(line: str) -> bool:
    if OPTION_INTRO_PATTERN.search(line) is not None:
        return True
    return any(marker in line for marker in JAPANESE_OPTION_INTRO_MARKERS)


def find_option_block_end(lines: list[str]) -> int:
    index: int = len(lines) - 1
    supplemental_lines: int = 0

    while index >= 0 and not is_option_line(lines[index]):
        supplemental_lines += 1
        if supplemental_lines > MAX_TRAILING_SUPPLEMENTAL_LINES:
            return -1
        index -= 1

    return index


def ends_with_options(lines: list[str]) -> bool:
    option_end_index: int = find_option_block_end(lines)
    if option_end_index < 0:
        return False

    option_start_index: int = option_end_index
    while option_start_index >= 0 and is_option_line(lines[option_start_index]):
        option_start_index -= 1

    option_count: int = option_end_index - option_start_index
    if option_count < 2:
        return False

    intro_index: int = option_start_index
    if intro_index < 0:
        return False
    if is_option_line(lines[intro_index]):
        return False
    if not is_option_intro_line(lines[intro_index]):
        return False

    return True


def looks_like_question(message: str) -> bool:
    if not message.strip():
        return False

    lines: list[str] = normalize_lines(message)
    if not lines:
        return False

    last_line: str = lines[-1]
    if last_line.endswith(QUESTION_ENDING):
        return True

    if ends_with_options(lines):
        return True

    return False


def completion_matcher(message: str) -> str:
    if looks_like_question(message):
        return "ask"
    return "done"

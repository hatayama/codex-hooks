import re

NUMBERED_OPTION_PATTERN = re.compile(r"^\d+\.\s")


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


def ends_with_numbered_options(lines: list[str]) -> bool:
    option_start_index: int = len(lines)
    index: int = len(lines) - 1

    while index >= 0:
        if not NUMBERED_OPTION_PATTERN.match(lines[index]):
            break
        option_start_index = index
        index -= 1

    if option_start_index == len(lines):
        return False
    if option_start_index == 0:
        return False

    return lines[option_start_index - 1].endswith(":")


def looks_like_question(message: str) -> bool:
    if not message.strip():
        return False

    lines: list[str] = normalize_lines(message)
    if not lines:
        return False

    last_line: str = lines[-1]
    if last_line.endswith(("?", "？")):
        return True

    if ends_with_numbered_options(lines):
        return True

    return False


def completion_matcher(message: str) -> str:
    if looks_like_question(message):
        return "ask"
    return "done"

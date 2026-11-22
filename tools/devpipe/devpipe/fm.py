"""Front matter in a strict YAML subset.

Purpose: read and update the `---` header of tickets and agent files without a
YAML dependency. The subset is deliberately small so a constrained model can
write it reliably and a lint can reject everything else:

    key: scalar
    key: [a, "b c", 3]
    key: {a: 1, b: "x"}
    key:
      - scalar
      - {path: src/x.py, lines: "1-80"}

Scalars are bare words, double- or single-quoted strings, integers and
true/false. A `#` preceded by whitespace starts a comment outside quotes.
Side effects: none.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")


class FrontMatterError(ValueError):
    """The header is missing or uses syntax outside the supported subset."""


def split(text: str) -> Tuple[str, str]:
    """Return (header, body). Raises FrontMatterError when no header exists."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise FrontMatterError("file does not start with a '---' line")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1:])
    raise FrontMatterError("front matter is not closed by a '---' line")


def _strip_comment(line: str) -> str:
    quote = ""
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip()
    return line.rstrip()


def _split_top(text: str, where: str) -> List[str]:
    """Split on commas that are outside quotes, brackets and braces."""
    parts, depth, quote, current = [], 0, "", []
    for char in text:
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
            current.append(char)
        elif char in "[{":
            depth += 1
            current.append(char)
        elif char in "]}":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if quote or depth:
        raise FrontMatterError(f"unbalanced quotes or brackets in {where}")
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _value(token: str, where: str) -> Any:
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        return [_value(part, where) for part in _split_top(token[1:-1], where)]
    if token.startswith("{") and token.endswith("}"):
        result: Dict[str, Any] = {}
        for part in _split_top(token[1:-1], where):
            match = _KEY.match(part)
            if not match:
                raise FrontMatterError(f"expected 'key: value' inside braces in {where}")
            result[match.group(1)] = _value(match.group(2), where)
        return result
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    if token in ("true", "false"):
        return token == "true"
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if token.startswith(("[", "{", "|", ">", "&", "*")):
        raise FrontMatterError(f"unsupported syntax {token[:12]!r} in {where}")
    return token


def parse(header: str) -> Dict[str, Any]:
    """Parse a header produced by split(). Raises FrontMatterError on bad syntax."""
    data: Dict[str, Any] = {}
    open_key = ""
    for number, raw in enumerate(header.splitlines(), start=1):
        line = _strip_comment(raw)
        if not line.strip():
            continue
        where = f"front matter line {number}"
        if line[0] in " \t":
            item = line.strip()
            if not open_key or not item.startswith("- "):
                raise FrontMatterError(f"unexpected indentation in {where}")
            data[open_key].append(_value(item[2:], where))
            continue
        match = _KEY.match(line)
        if not match:
            raise FrontMatterError(f"expected 'key: value' in {where}")
        key, rest = match.group(1), match.group(2).strip()
        if key in data:
            raise FrontMatterError(f"duplicate key {key!r} in {where}")
        if rest:
            data[key] = _value(rest, where)
            open_key = ""
        else:
            data[key] = []
            open_key = key
    return data


def load(text: str) -> Tuple[Dict[str, Any], str]:
    """Return (parsed header, body) for a whole file."""
    header, body = split(text)
    return parse(header), body


def set_scalar(text: str, key: str, value: str) -> str:
    """Return the file text with `key: value` replaced or appended in the header.

    Only the one line changes, so the rest of the file survives byte for byte.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise FrontMatterError("file does not start with a '---' line")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            lines.insert(index, f"{key}: {value}\n")
            return "".join(lines)
        if lines[index].startswith(f"{key}:"):
            lines[index] = f"{key}: {value}\n"
            return "".join(lines)
    raise FrontMatterError("front matter is not closed by a '---' line")

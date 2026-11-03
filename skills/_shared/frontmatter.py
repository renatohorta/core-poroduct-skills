"""
frontmatter.py — minimal `---` frontmatter parser/writer (kanban cards, roadmap).

Supported values: scalar strings, empty values and inline lists `[a, b]`.
Values are never quoted or unquoted; a `:` inside a value is kept verbatim.

Pure standard library.
"""
from __future__ import annotations


def _split_line(line: str):
    if line.endswith(":") and ": " not in line:
        return line[:-1].strip(), ""
    if ": " in line:
        key, value = line.split(": ", 1)
        return key.strip(), value.strip()
    if line.endswith(":"):
        return line[:-1].strip(), ""
    return None


def _value(raw: str):
    if raw.startswith("[") and raw.endswith("]"):
        return [item.strip() for item in raw[1:-1].split(",") if item.strip()]
    return raw


def parse(text: str) -> tuple[dict, str]:
    """Split `text` into (meta, body). No frontmatter -> ({}, text)."""
    text = text.lstrip("﻿").replace("\r\n", "\n")
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        return {}, text
    meta: dict = {}
    for line in lines[1:end]:
        line = line.strip()
        if not line:
            continue
        pair = _split_line(line)
        if pair and pair[0]:
            meta[pair[0]] = _value(pair[1])
    body = "\n".join(lines[end + 1:])
    if body.startswith("\n"):
        body = body[1:]
    return meta, body


def _render(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def dump(meta: dict, body: str) -> str:
    """Render meta (insertion order) and body with LF endings."""
    out = ["---\n"]
    for key, value in meta.items():
        rendered = _render(value)
        out.append(f"{key}: {rendered}\n" if rendered else f"{key}:\n")
    out.append("---\n")
    body = body.replace("\r\n", "\n").rstrip()
    if not body:
        return "".join(out)
    return "".join(out) + "\n" + body + "\n"

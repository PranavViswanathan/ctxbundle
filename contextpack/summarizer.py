"""Heuristic, LLM-free summarization for oversized files."""

from __future__ import annotations

import os
import re
from typing import List, Tuple

HEAD_LINES = 20
TAIL_LINES = 10

# (regex, label). All anchored at line start, capturing the symbol name.
_DEF_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"), "def"),
    (re.compile(r"^\s*class\s+([A-Za-z_]\w*)"), "class"),
    (re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)"), "function"),
    (re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\("), "const"),
    (re.compile(r"^\s*(?:export\s+)?(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:async\s+)?([A-Za-z_]\w*)\s*\([^)]*\)\s*\{"), "method"),
    (re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"), "func"),
    (re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_]\w*)"), "fn"),
    (re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+([A-Za-z_]\w*)"), "class"),
]


def _extract_symbols(text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for line in text.splitlines():
        for pattern, label in _DEF_PATTERNS:
            m = pattern.match(line)
            if m:
                name = m.group(1)
                key = f"{label} {name}"
                if key not in seen:
                    seen.add(key)
                    out.append(key)
                break
    return out


def summarize(path: str, content: str) -> str:
    """Return a heuristic summary: head + tail + symbol list."""
    lines = content.splitlines()
    total = len(lines)

    if total <= HEAD_LINES + TAIL_LINES:
        return content

    head = lines[:HEAD_LINES]
    tail = lines[-TAIL_LINES:]
    omitted = total - HEAD_LINES - TAIL_LINES
    symbols = _extract_symbols(content)

    parts: List[str] = []
    parts.extend(head)
    parts.append("")
    parts.append(f"[... {omitted} lines omitted — heuristic summary ...]")
    if symbols:
        parts.append("")
        parts.append("Definitions found:")
        for s in symbols:
            parts.append(f"  - {s}")
    parts.append("")
    parts.extend(tail)

    return "\n".join(parts)

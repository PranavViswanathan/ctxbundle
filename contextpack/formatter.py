"""Output formatting for the packed context file."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence


@dataclass
class PackedFile:
    path: str
    body: str
    truncated_lines: int = 0  # 0 if not truncated
    summarized: bool = False


@dataclass
class PackResult:
    repo_name: str
    included: List[PackedFile]
    skipped_too_large: List[str]
    skipped_for_budget: List[str]
    total_files: int
    estimated_tokens: int
    token_limit: int


def _truncation_marker(omitted: int) -> str:
    return f"[FILE TRUNCATED - {omitted} lines omitted]"


def truncate(content: str, max_tokens: int) -> tuple[str, int]:
    """Trim content to fit `max_tokens`, keeping head + tail context.

    Returns (new_content, omitted_line_count). The token cap accounts for
    the inserted `[FILE TRUNCATED ...]` marker so the result stays under
    `max_tokens`.
    """
    from .tokenizer import estimate_tokens, CHARS_PER_TOKEN

    if estimate_tokens(content) <= max_tokens:
        return content, 0

    total_lines = content.count("\n")
    # Reserve ~50 chars (~12 tokens) for the truncation marker line.
    marker_reserve_chars = 60
    budget_chars = max(0, max_tokens * CHARS_PER_TOKEN - marker_reserve_chars)
    # 75% head, 25% tail — most code files put declarations near the top.
    head_chars = int(budget_chars * 0.75)
    tail_chars = budget_chars - head_chars

    head = content[:head_chars]
    tail = content[-tail_chars:] if tail_chars > 0 else ""

    # Snap head/tail to line boundaries for cleaner output.
    last_nl = head.rfind("\n")
    if last_nl > 0:
        head = head[: last_nl + 1]
    first_nl = tail.find("\n")
    if first_nl >= 0:
        tail = tail[first_nl + 1 :]

    head_lines = head.count("\n")
    tail_lines = tail.count("\n")
    omitted = max(0, total_lines - head_lines - tail_lines)

    return f"{head}{_truncation_marker(omitted)}\n{tail}", omitted


def format_output(result: PackResult) -> str:
    lines: List[str] = []
    lines.append("=== CONTEXTPACK ===")
    lines.append(f"Repo: {result.repo_name}")
    lines.append(f"Files included: {len(result.included)} of {result.total_files}")
    lines.append(
        f"Estimated tokens: {result.estimated_tokens:,} / {result.token_limit:,}"
    )
    skipped = result.skipped_too_large + result.skipped_for_budget
    if skipped:
        lines.append(f"Skipped (too large): {', '.join(skipped)}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    for pf in result.included:
        lines.append(f"=== FILE: {pf.path} ===")
        lines.append(pf.body)
        if not pf.body.endswith("\n"):
            lines.append("")
        else:
            lines.append("")

    return "\n".join(lines)

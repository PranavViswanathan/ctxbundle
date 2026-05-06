"""Click-based CLI entrypoint for contextpack."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

import click

from . import __version__
from .formatter import PackResult, PackedFile, format_output, truncate
from .summarizer import summarize
from .tokenizer import estimate_tokens, rank
from .walker import walk


_LIMIT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kKmM]?)\s*$")


def _parse_limit(value: str) -> int:
    """Parse '100k', '1.5m', '50000' into an integer token count."""
    m = _LIMIT_RE.match(value)
    if not m:
        raise click.BadParameter(
            f"Invalid token limit: {value!r}. Use forms like 200000, 100k, 1.5m."
        )
    num = float(m.group(1))
    suffix = m.group(2).lower()
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[suffix]
    return int(num * multiplier)


def _per_file_budget(limit: int) -> int:
    """Cap a single file at ~10% of the total budget (min 2k tokens)."""
    return max(2_000, limit // 10)


def _process_file(
    path: str,
    content: str,
    file_budget: int,
    use_summarize: bool,
) -> Tuple[PackedFile, int]:
    """Apply truncation/summarization. Returns (PackedFile, tokens_used)."""
    tokens = estimate_tokens(content)
    if tokens <= file_budget:
        return PackedFile(path=path, body=content), tokens

    if use_summarize:
        body = summarize(path, content)
        return (
            PackedFile(path=path, body=body, summarized=True),
            estimate_tokens(body),
        )

    body, omitted = truncate(content, file_budget)
    return (
        PackedFile(path=path, body=body, truncated_lines=omitted),
        estimate_tokens(body),
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="contextpack")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--limit",
    "limit_str",
    default="200k",
    show_default=True,
    help="Token limit (e.g. 200k, 1.5m, 50000).",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file. Defaults to stdout.",
)
@click.option(
    "--ignore",
    "ignore_patterns",
    multiple=True,
    help="Additional gitignore-style patterns to skip. Repeatable.",
)
@click.option(
    "--summarize",
    "use_summarize",
    is_flag=True,
    default=False,
    help="Summarize large files (head + tail + symbols) instead of truncating.",
)
def main(
    path: Path,
    limit_str: str,
    out_path: Path,
    ignore_patterns: Tuple[str, ...],
    use_summarize: bool,
) -> None:
    """Bundle PATH into a single LLM-ready text file.

    Walks the directory tree, respects .gitignore, skips binaries and
    lockfiles, and prioritizes entry points and source files when the
    token budget is tight.
    """
    limit = _parse_limit(limit_str)
    file_budget = _per_file_budget(limit)
    root = path.resolve()

    # Allow --ignore to be passed as a single space-separated string too.
    extra_ignores: List[str] = []
    for p in ignore_patterns:
        extra_ignores.extend(p.split())

    entries = walk(root, extra_ignores=extra_ignores)
    total_files = len(entries)
    ranked = rank(entries)

    included: List[PackedFile] = []
    skipped_too_large: List[str] = []
    skipped_for_budget: List[str] = []
    used_tokens = 0

    for rf in ranked:
        remaining = limit - used_tokens
        if remaining <= 0:
            skipped_for_budget.append(rf.entry.path)
            continue

        # Single-file cap: smaller of file_budget and remaining global budget.
        cap = min(file_budget, remaining)
        packed, tokens = _process_file(
            rf.entry.path, rf.entry.content, cap, use_summarize
        )

        # If even the truncated body would blow the remaining budget, skip.
        if tokens > remaining:
            if rf.tokens > file_budget:
                skipped_too_large.append(rf.entry.path)
            else:
                skipped_for_budget.append(rf.entry.path)
            continue

        included.append(packed)
        used_tokens += tokens

    # Restore lexicographic ordering in the output for readability,
    # independent of the priority-based packing order.
    included.sort(key=lambda p: p.path)

    result = PackResult(
        repo_name=root.name,
        included=included,
        skipped_too_large=skipped_too_large,
        skipped_for_budget=skipped_for_budget,
        total_files=total_files,
        estimated_tokens=used_tokens,
        token_limit=limit,
    )
    output = format_output(result)

    if out_path is None:
        click.echo(output)
    else:
        out_path.write_text(output, encoding="utf-8")
        click.echo(
            f"Wrote {len(included)} files, ~{used_tokens:,} tokens to {out_path}",
            err=True,
        )


if __name__ == "__main__":
    main()

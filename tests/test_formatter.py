"""Tests for output formatting and truncation."""

from contextpack.formatter import (
    PackResult,
    PackedFile,
    format_output,
    truncate,
)


def test_truncate_passes_through_when_under_budget():
    text = "small\n"
    out, omitted = truncate(text, 1000)
    assert out == text
    assert omitted == 0


def test_truncate_inserts_marker_when_over_budget():
    text = "x\n" * 1000
    out, omitted = truncate(text, 50)
    assert "[FILE TRUNCATED" in out
    assert omitted > 0


def test_truncate_keeps_head_and_tail_markers_intact():
    head = "FIRST_LINE_MARKER\n"
    tail = "LAST_LINE_MARKER\n"
    text = head + ("middle line content\n" * 500) + tail
    # Budget needs enough room for both head and tail after the marker
    # reserve, so use a non-trivial cap.
    out, _ = truncate(text, 200)
    assert "FIRST_LINE_MARKER" in out
    assert "LAST_LINE_MARKER" in out


def test_truncate_omitted_count_reflects_lines_dropped():
    text = "\n".join(str(i) for i in range(1000)) + "\n"
    out, omitted = truncate(text, 40)
    # Roughly: total ~1000 lines, kept lines should be << 1000.
    assert omitted >= 800


def test_format_output_header_fields():
    result = PackResult(
        repo_name="myrepo",
        included=[PackedFile(path="a.py", body="x = 1\n")],
        skipped_too_large=[],
        skipped_for_budget=[],
        total_files=1,
        estimated_tokens=42,
        token_limit=1000,
    )
    out = format_output(result)
    assert "=== CONTEXTPACK ===" in out
    assert "Repo: myrepo" in out
    assert "Files included: 1 of 1" in out
    assert "Estimated tokens: 42 / 1,000" in out
    assert "=== FILE: a.py ===" in out
    assert "x = 1" in out


def test_format_output_lists_skipped_files():
    result = PackResult(
        repo_name="r",
        included=[],
        skipped_too_large=["huge.sql"],
        skipped_for_budget=["other.py"],
        total_files=2,
        estimated_tokens=0,
        token_limit=1000,
    )
    out = format_output(result)
    assert "Skipped (too large)" in out
    assert "huge.sql" in out
    assert "other.py" in out


def test_format_output_omits_skipped_line_when_empty():
    result = PackResult(
        repo_name="r",
        included=[PackedFile(path="a.py", body="x\n")],
        skipped_too_large=[],
        skipped_for_budget=[],
        total_files=1,
        estimated_tokens=1,
        token_limit=1000,
    )
    out = format_output(result)
    assert "Skipped" not in out


def test_format_output_uses_file_delimiter_for_each_included_file():
    result = PackResult(
        repo_name="r",
        included=[
            PackedFile(path="a.py", body="x\n"),
            PackedFile(path="src/b.py", body="y\n"),
        ],
        skipped_too_large=[],
        skipped_for_budget=[],
        total_files=2,
        estimated_tokens=2,
        token_limit=1000,
    )
    out = format_output(result)
    assert out.count("=== FILE:") == 2
    assert "=== FILE: a.py ===" in out
    assert "=== FILE: src/b.py ===" in out

"""Tests for token estimation and file ranking."""

from pathlib import Path

from contextpack.tokenizer import estimate_tokens, rank
from contextpack.walker import FileEntry


def _entry(path: str, content: str = "x\n") -> FileEntry:
    return FileEntry(
        path=path,
        abs_path=Path("/tmp") / path,
        content=content,
        size_bytes=len(content),
        line_count=content.count("\n"),
    )


def test_estimate_tokens_uses_chars_per_4():
    assert estimate_tokens("a" * 400) == 100


def test_estimate_tokens_empty_returns_zero():
    assert estimate_tokens("") == 0


def test_estimate_tokens_short_text_floors_to_one():
    assert estimate_tokens("hi") == 1


def test_rank_puts_entry_points_first():
    entries = [_entry("utils.py"), _entry("main.py")]
    ranked = rank(entries)
    assert ranked[0].entry.path == "main.py"


def test_rank_puts_index_js_above_other_source():
    entries = [_entry("src/lib.js"), _entry("index.js")]
    ranked = rank(entries)
    assert ranked[0].entry.path == "index.js"


def test_rank_puts_readme_above_source():
    entries = [_entry("src/lib.py"), _entry("README.md")]
    ranked = rank(entries)
    assert ranked[0].entry.path == "README.md"


def test_rank_demotes_tests_below_source():
    entries = [_entry("tests/test_foo.py"), _entry("src/foo.py")]
    ranked = rank(entries)
    assert ranked[0].entry.path == "src/foo.py"
    assert ranked[1].entry.path == "tests/test_foo.py"


def test_rank_recognizes_test_naming_conventions():
    entries = [
        _entry("foo.test.ts"),
        _entry("bar.spec.js"),
        _entry("__tests__/baz.js"),
    ]
    ranked = rank(entries)
    # All three should be priority 4 (tests).
    assert all(r.priority == 4 for r in ranked)


def test_rank_demotes_configs_below_source():
    entries = [_entry("pyproject.toml"), _entry("src/main_logic.py")]
    ranked = rank(entries)
    assert ranked[0].entry.path == "src/main_logic.py"

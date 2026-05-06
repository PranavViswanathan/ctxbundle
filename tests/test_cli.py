"""End-to-end tests for the Click CLI."""

from click.testing import CliRunner

from contextpack import __version__
from contextpack.cli import _parse_limit, main


def test_parse_limit_plain_integer():
    assert _parse_limit("100") == 100


def test_parse_limit_k_suffix():
    assert _parse_limit("100k") == 100_000


def test_parse_limit_m_suffix():
    assert _parse_limit("1.5m") == 1_500_000


def test_parse_limit_handles_whitespace():
    assert _parse_limit(" 50k ") == 50_000


def test_parse_limit_rejects_garbage():
    import click

    try:
        _parse_limit("nope")
    except click.BadParameter:
        return
    raise AssertionError("expected BadParameter")


def test_cli_packs_directory_to_stdout(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n")
    result = CliRunner().invoke(main, [str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "=== FILE: main.py ===" in result.output
    assert "print('hi')" in result.output


def test_cli_writes_to_out_file(tmp_path):
    (tmp_path / "x.py").write_text("x = 1\n")
    out_file = tmp_path / "context.txt"
    result = CliRunner().invoke(main, [str(tmp_path), "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    body = out_file.read_text()
    assert "=== FILE: x.py ===" in body
    assert "x = 1" in body


def test_cli_ignore_excludes_file(tmp_path):
    (tmp_path / "keep.py").write_text("a\n")
    (tmp_path / "drop.py").write_text("b\n")
    result = CliRunner().invoke(main, [str(tmp_path), "--ignore", "drop.py"])
    assert result.exit_code == 0
    assert "=== FILE: keep.py ===" in result.output
    assert "=== FILE: drop.py ===" not in result.output


def test_cli_version_flag():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_limit_truncates_large_file(tmp_path):
    big = "\n".join(f"line_{i}" for i in range(2000)) + "\n"
    (tmp_path / "huge.py").write_text(big)
    result = CliRunner().invoke(main, [str(tmp_path), "--limit", "200"])
    assert result.exit_code == 0
    assert "[FILE TRUNCATED" in result.output


def test_cli_summarize_uses_summary_for_large_files(tmp_path):
    big = "\n".join(f"line_{i}" for i in range(1000))
    big += "\ndef notable_function():\n    pass\n"
    (tmp_path / "big.py").write_text(big)
    result = CliRunner().invoke(
        main, [str(tmp_path), "--limit", "5k", "--summarize"]
    )
    assert result.exit_code == 0
    assert "heuristic summary" in result.output
    assert "def notable_function" in result.output


def test_cli_rejects_nonexistent_path():
    result = CliRunner().invoke(main, ["/nonexistent/path/xyz"])
    assert result.exit_code != 0

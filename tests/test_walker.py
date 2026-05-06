"""Tests for directory walking and ignore handling."""

from contextpack.walker import walk


def test_walk_collects_text_files(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n")
    (tmp_path / "README.md").write_text("# repo\n")
    paths = {e.path for e in walk(tmp_path)}
    assert paths == {"main.py", "README.md"}


def test_walk_respects_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("ignored.txt\nbuild_artifacts/\n")
    (tmp_path / "kept.py").write_text("print(1)\n")
    (tmp_path / "ignored.txt").write_text("nope\n")
    (tmp_path / "build_artifacts").mkdir()
    (tmp_path / "build_artifacts" / "out.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path)}
    assert "kept.py" in paths
    assert "ignored.txt" not in paths
    assert "build_artifacts/out.py" not in paths


def test_walk_skips_node_modules(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path)}
    assert paths == {"src/main.py"}


def test_walk_skips_dot_git(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (tmp_path / "main.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path)}
    assert paths == {"main.py"}


def test_walk_skips_lockfiles(tmp_path):
    (tmp_path / "package-lock.json").write_text("{}\n")
    (tmp_path / "yarn.lock").write_text("\n")
    (tmp_path / "main.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path)}
    assert paths == {"main.py"}


def test_walk_skips_binary_files(tmp_path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (tmp_path / "code.py").write_text("hello\n")
    paths = {e.path for e in walk(tmp_path)}
    assert paths == {"code.py"}


def test_walk_skips_files_with_null_bytes(tmp_path):
    (tmp_path / "data.dat").write_bytes(b"some text\x00more text\n")
    (tmp_path / "code.py").write_text("hello\n")
    paths = {e.path for e in walk(tmp_path)}
    assert "data.dat" not in paths
    assert "code.py" in paths


def test_walk_skips_env_files(tmp_path):
    (tmp_path / ".env").write_text("SECRET=hunter2\n")
    (tmp_path / ".env.local").write_text("KEY=val\n")
    (tmp_path / "main.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path)}
    assert paths == {"main.py"}


def test_walk_extra_ignores(tmp_path):
    (tmp_path / "drop.py").write_text("x\n")
    (tmp_path / "keep.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path, extra_ignores=["drop.py"])}
    assert paths == {"keep.py"}


def test_walk_extra_ignore_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("x\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x\n")
    paths = {e.path for e in walk(tmp_path, extra_ignores=["docs/"])}
    assert paths == {"src/main.py"}


def test_walk_returns_sorted_paths(tmp_path):
    (tmp_path / "z.py").write_text("x\n")
    (tmp_path / "a.py").write_text("x\n")
    (tmp_path / "m.py").write_text("x\n")
    entries = walk(tmp_path)
    assert [e.path for e in entries] == ["a.py", "m.py", "z.py"]


def test_walk_handles_nested_gitignore_in_subdir(tmp_path):
    """A gitignore at the root applies to subdirectories."""
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x\n")
    (tmp_path / "src" / "trace.log").write_text("noise\n")
    paths = {e.path for e in walk(tmp_path)}
    assert "src/app.py" in paths
    assert "src/trace.log" not in paths

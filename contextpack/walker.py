"""Directory walking and file collection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import pathspec


# Directories that are never useful in an LLM context.
ALWAYS_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".env.d",
    "build",
    "dist",
    "target",
    ".next",
    ".nuxt",
    ".cache",
    ".idea",
    ".vscode",
    "coverage",
    ".gradle",
    ".terraform",
}

# Glob patterns that are never useful (binary blobs, lockfiles, logs, secrets).
ALWAYS_SKIP_GLOBS = [
    ".env",
    ".env.*",
    "*.lock",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.bin",
    "*.class",
    "*.jar",
    "*.war",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.ico",
    "*.svg",
    "*.webp",
    "*.tiff",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.gz",
    "*.bz2",
    "*.7z",
    "*.rar",
    "*.mp3",
    "*.mp4",
    "*.mov",
    "*.avi",
    "*.webm",
    "*.wav",
    "*.flac",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.otf",
    "*.eot",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "uv.lock",
    "Cargo.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
]


@dataclass
class FileEntry:
    """A collected file with its content and metadata."""

    path: str  # POSIX-style path relative to the repo root
    abs_path: Path
    content: str
    size_bytes: int
    line_count: int


def _read_gitignore(root: Path) -> List[str]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    try:
        return gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _build_spec(
    root: Path, extra_ignores: Sequence[str]
) -> pathspec.PathSpec:
    """Combine .gitignore, always-skip globs, and user --ignore patterns."""
    patterns: List[str] = []
    patterns.extend(_read_gitignore(root))
    patterns.extend(ALWAYS_SKIP_GLOBS)
    patterns.extend(extra_ignores)
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def _looks_binary(sample: bytes) -> bool:
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    # Heuristic: non-text byte ratio > 30% means binary.
    text_bytes = bytes(range(32, 127)) + b"\n\r\t\f\b"
    nontext = sum(1 for b in sample if b not in text_bytes)
    return nontext / len(sample) > 0.30


def _read_text(path: Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            sample = f.read(8192)
        if _looks_binary(sample):
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def walk(
    root: Path, extra_ignores: Sequence[str] = ()
) -> List[FileEntry]:
    """Walk `root` and return text files not excluded by ignore rules."""
    root = root.resolve()
    spec = _build_spec(root, extra_ignores)
    entries: List[FileEntry] = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)

        # Prune always-skip dirs in place so os.walk doesn't descend.
        dirnames[:] = [d for d in dirnames if d not in ALWAYS_SKIP_DIRS]

        # Prune dirs matched by ignore spec (gitignore + user patterns).
        kept = []
        for d in dirnames:
            rel = (rel_dir / d).as_posix() + "/"
            if not spec.match_file(rel):
                kept.append(d)
        dirnames[:] = kept

        for name in filenames:
            rel_path = (rel_dir / name).as_posix()
            if spec.match_file(rel_path):
                continue
            abs_path = Path(dirpath) / name
            content = _read_text(abs_path)
            if content is None:
                continue
            try:
                size = abs_path.stat().st_size
            except OSError:
                size = len(content.encode("utf-8", errors="replace"))
            entries.append(
                FileEntry(
                    path=rel_path,
                    abs_path=abs_path,
                    content=content,
                    size_bytes=size,
                    line_count=content.count("\n") + (0 if content.endswith("\n") or not content else 1),
                )
            )

    entries.sort(key=lambda e: e.path)
    return entries

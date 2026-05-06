"""Token estimation and budget allocation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Sequence

from .walker import FileEntry


# Char/4 is the standard rough heuristic for tokens across most LLM tokenizers.
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


# Filenames that are entry points across common ecosystems.
ENTRY_POINT_NAMES = {
    "main.py",
    "__main__.py",
    "app.py",
    "server.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "index.js",
    "index.ts",
    "index.tsx",
    "index.jsx",
    "main.js",
    "main.ts",
    "server.js",
    "server.ts",
    "app.js",
    "app.ts",
    "main.go",
    "main.rs",
    "Main.java",
    "Program.cs",
}

# Config-ish files we want to keep but rank below source.
CONFIG_NAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "package.json",
    "tsconfig.json",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    ".dockerignore",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".scala",
    ".rb", ".php", ".cs", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp",
    ".swift", ".m", ".mm",
    ".sh", ".bash", ".zsh",
    ".sql", ".graphql", ".proto",
    ".html", ".css", ".scss", ".sass", ".less", ".vue", ".svelte",
}


@dataclass
class RankedFile:
    entry: FileEntry
    priority: int  # Lower = more important.
    tokens: int


def _priority(entry: FileEntry) -> int:
    name = os.path.basename(entry.path)
    lower_path = entry.path.lower()
    ext = os.path.splitext(name)[1].lower()

    if name in ENTRY_POINT_NAMES:
        return 0
    if name.lower().startswith("readme"):
        return 1
    # Tests rank lower than other source code.
    is_test = (
        "test" in lower_path.split("/")
        or lower_path.startswith("tests/")
        or "/tests/" in lower_path
        or "__tests__" in lower_path
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.js")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.js")
    )
    if is_test:
        return 4
    if ext in SOURCE_EXTENSIONS:
        return 2
    if name in CONFIG_NAMES or ext in {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}:
        return 3
    return 5


def rank(entries: Sequence[FileEntry]) -> List[RankedFile]:
    ranked = [
        RankedFile(entry=e, priority=_priority(e), tokens=estimate_tokens(e.content))
        for e in entries
    ]
    # Sort by priority, then by token count ascending so we keep small useful
    # files when budget is tight.
    ranked.sort(key=lambda r: (r.priority, r.tokens, r.entry.path))
    return ranked

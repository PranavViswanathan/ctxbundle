# ctxbundle

Bundle a code repository into a single LLM-ready text file.

`ctxbundle` walks a directory, drops binaries / lockfiles / build output, respects `.gitignore`, prioritizes the files an LLM actually wants to see, and emits a single text artifact you can paste into any chat window.

Zero API calls. Zero ML dependencies. Just `click` and `pathspec`.

## Why this exists

Pasting a whole repo into a chat is annoying. Existing tools either:

- Dump every file (including `node_modules` and PNGs) and blow your context window
- Need an API key or a model to summarize
- Make you hand-curate the file list every time

`ctxbundle` does the boring middle layer: pick the right files, keep them inside a token budget, format the result so an LLM can navigate it on a single read. It runs offline, finishes in seconds, and produces deterministic output you can diff.

## Install

```bash
pip install ctxbundle
```

Or from source:

```bash
git clone https://github.com/pranavviswanathan/ctxbundle
cd ctxbundle
pip install -e .
```

Requires Python 3.8+.

## Usage

```bash
ctxbundle .                        # pack current directory to stdout
ctxbundle ./myrepo                 # pack a specific path
ctxbundle . --limit 100k           # token limit (default 200k)
ctxbundle . --out context.txt      # write to file instead of stdout
ctxbundle . --ignore tests/ docs/  # additional ignore patterns
ctxbundle . --summarize            # summarize large files instead of truncating
```

`--limit` accepts integers, `k` (thousands), or `m` (millions): `50000`, `100k`, `1.5m`.

`--ignore` is repeatable and accepts gitignore-style globs:

```bash
ctxbundle . --ignore "*.test.ts" --ignore "fixtures/"
```

## What gets included

`ctxbundle` always skips:

- VCS / build / cache directories: `.git`, `node_modules`, `__pycache__`, `build/`, `dist/`, `.venv`, `target`, `.next`, ...
- Lockfiles: `package-lock.json`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, `*.lock`
- Binaries and media: `*.png`, `*.jpg`, `*.pdf`, `*.zip`, `*.so`, `*.dll`, fonts, audio, video
- Generated noise: `*.log`, `*.pyc`, `*.min.js`, `*.map`
- Secrets: `.env`, `.env.*`

On top of that, it honors your `.gitignore` and any `--ignore` patterns you pass.

## How budget allocation works

When the repo fits inside `--limit`, every text file is included verbatim.

When it doesn't, files are ranked and packed in priority order:

1. Entry points (`main.py`, `index.js`, `app.py`, `server.js`, `main.go`, ...)
2. README files
3. Source code (`.py`, `.ts`, `.go`, `.rs`, `.java`, ...)
4. Configs (`pyproject.toml`, `package.json`, `Dockerfile`, ...)
5. Tests
6. Everything else

A single file is capped at roughly 10% of the total budget. Files exceeding that cap are either truncated (with a `[FILE TRUNCATED - N lines omitted]` marker) or, with `--summarize`, replaced by a heuristic summary: first 20 lines, last 10 lines, plus a list of function/class names found via regex.

## Output format

```
=== CONTEXTPACK ===
Repo: myrepo
Files included: 23 of 31
Estimated tokens: 94,200 / 200,000
Skipped (too large): migrations.sql, package-lock.json
Generated: 2025-01-15 14:32

=== FILE: src/main.py ===
[file contents]

=== FILE: src/utils/helpers.py ===
[file contents]
...
```

The `=== FILE: <path> ===` delimiter is unambiguous and easy for an LLM to parse on a single pass.

## Token estimation

Token counts use a `chars / 4` heuristic. It matches BPE tokenizers within ~10% on typical source code — close enough for budgeting, and free of ML dependencies.

## Library use

```python
from pathlib import Path
from ctxbundle.walker import walk
from ctxbundle.tokenizer import rank, estimate_tokens

entries = walk(Path("./myrepo"), extra_ignores=["docs/"])
ranked = rank(entries)
for rf in ranked[:10]:
    print(rf.priority, rf.tokens, rf.entry.path)
```

## Publishing (maintainers)

```bash
pip install --upgrade build twine
python -m build
python -m twine upload dist/*
```

## License

MIT.

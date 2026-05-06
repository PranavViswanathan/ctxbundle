# ctxbundle release automation.
# Run `make help` for the full list of targets.

.PHONY: help install test ci build check clean pack publish publish-test \
        version bump-patch bump-minor bump-major release _bump _check-clean

PYTHON     ?= python3
VENV       := .venv
BIN        := $(VENV)/bin
PIP        := $(BIN)/pip
PY         := $(BIN)/python

PACKAGE    := ctxbundle
PYPROJECT  := pyproject.toml
INIT_FILE  := contextpack/__init__.py
CLI_BIN    := $(BIN)/contextpack

VERSION = $(shell sed -n 's/^version = "\(.*\)"/\1/p' $(PYPROJECT) | head -1)

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} \
	  /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
	@echo ""
	@echo "Current version: $(VERSION)"

# ----- environment ---------------------------------------------------------

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install: $(BIN)/python  ## Create .venv and install editable + dev deps

clean:  ## Remove build artifacts and caches
	rm -rf dist build *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

# ----- local dev -----------------------------------------------------------

pack: install  ## Run the CLI on this repo (smoke test)
	$(CLI_BIN) . --out /tmp/$(PACKAGE)-self.txt
	@echo "Wrote /tmp/$(PACKAGE)-self.txt"

test: install  ## Run pytest
	$(BIN)/pytest

ci: install  ## Run the same checks CI runs (test + build + twine check)
	$(BIN)/pytest
	@$(MAKE) -s check

# ----- build & publish -----------------------------------------------------

build: clean install  ## Clean and build sdist + wheel
	$(PY) -m build

check: build  ## Validate the built dist with twine
	$(BIN)/twine check dist/*

publish-test: check  ## Upload to TestPyPI
	$(BIN)/twine upload --repository testpypi dist/*

publish: check  ## Upload to PyPI
	$(BIN)/twine upload dist/*

# ----- versioning ----------------------------------------------------------

version:  ## Print the current version
	@echo $(VERSION)

bump-patch:  ## 0.x.Y -> 0.x.Y+1
	@$(MAKE) -s _bump PART=patch

bump-minor:  ## 0.X.y -> 0.X+1.0
	@$(MAKE) -s _bump PART=minor

bump-major:  ## X.y.z -> X+1.0.0
	@$(MAKE) -s _bump PART=major

_bump:
	@CURRENT=$$(sed -n 's/^version = "\(.*\)"/\1/p' $(PYPROJECT) | head -1); \
	if [ -z "$$CURRENT" ]; then echo "ERROR: could not read version"; exit 1; fi; \
	NEW=$$(echo $$CURRENT | awk -F. -v p=$(PART) '{ \
	  if (p=="patch") print $$1"."$$2"."$$3+1; \
	  else if (p=="minor") print $$1"."$$2+1".0"; \
	  else print $$1+1".0.0"; \
	}'); \
	sed -i.bak "s/^version = \".*\"/version = \"$$NEW\"/" $(PYPROJECT) && rm $(PYPROJECT).bak; \
	sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$$NEW\"/" $(INIT_FILE) && rm $(INIT_FILE).bak; \
	echo "Bumped: $$CURRENT -> $$NEW"

# ----- one-shot release ----------------------------------------------------

release:  ## Run tests, bump patch, commit, tag, push, publish to PyPI
	@$(MAKE) -s _check-clean
	@$(MAKE) -s test
	@$(MAKE) -s bump-patch
	@NEW=$$(sed -n 's/^version = "\(.*\)"/\1/p' $(PYPROJECT) | head -1); \
	git add $(PYPROJECT) $(INIT_FILE); \
	git commit -m "Release v$$NEW"; \
	git tag v$$NEW; \
	git push origin HEAD; \
	git push origin v$$NEW
	@$(MAKE) publish

_check-clean:
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
	  echo "ERROR: working tree has uncommitted changes."; \
	  echo "Commit or stash first, then run 'make release'."; \
	  exit 1; \
	fi

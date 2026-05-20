SHELL := /usr/bin/env bash

ENV_FILE ?= .env
SIGNALS_SCRIPT := scripts/export_signals_to_google_sheet.py
DEFAULT_LIMIT ?= 200
SOURCE_TABLE ?= agent_outputs.signals

.PHONY: signals-install signals-dry-run signals-live

signals-install:
	python3 -m pip install -r scripts/requirements-gm-signal-export.txt

signals-dry-run:
	@set -a; \
	[[ -f "$(ENV_FILE)" ]] && source "$(ENV_FILE)"; \
	set +a; \
	python3 "$(SIGNALS_SCRIPT)" \
	  --dry-run \
	  --limit "$${DEFAULT_LIMIT:-$(DEFAULT_LIMIT)}" \
	  --input-jsonl scripts/sample_signals.jsonl \
	  --source-table "$${SOURCE_TABLE:-$(SOURCE_TABLE)}" \
	  --print-sample 5

signals-live:
	@set -a; \
	[[ -f "$(ENV_FILE)" ]] && source "$(ENV_FILE)"; \
	set +a; \
	python3 "$(SIGNALS_SCRIPT)" \
	  --limit "$${DEFAULT_LIMIT:-$(DEFAULT_LIMIT)}" \
	  --source-table "$${SOURCE_TABLE:-$(SOURCE_TABLE)}" \
	  --print-sample 5

SHELL := /usr/bin/env bash

ENV_FILE ?= .env
SIGNALS_SCRIPT := scripts/export_signals_to_google_sheet.py
SIGNALS_LIMIT ?= 200
SIGNALS_PRINT_SAMPLE ?= 5
SIGNALS_EXTRA_ARGS ?=

.PHONY: signals-dry-run signals-live

signals-dry-run:
	@set -a; \
	[[ -f "$(ENV_FILE)" ]] && source "$(ENV_FILE)"; \
	set +a; \
	python3 "$(SIGNALS_SCRIPT)" \
	  --dry-run \
	  --limit "$(SIGNALS_LIMIT)" \
	  --print-sample "$(SIGNALS_PRINT_SAMPLE)" \
	  $(SIGNALS_EXTRA_ARGS)

signals-live:
	@set -a; \
	[[ -f "$(ENV_FILE)" ]] && source "$(ENV_FILE)"; \
	set +a; \
	python3 "$(SIGNALS_SCRIPT)" \
	  --limit "$(SIGNALS_LIMIT)" \
	  --print-sample "$(SIGNALS_PRINT_SAMPLE)" \
	  $(SIGNALS_EXTRA_ARGS)

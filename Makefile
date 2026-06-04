# Makefile — canonical entry point for the journal repo's infra + podcast pipeline.
#
# These targets are thin aliases over scripts under `infra/azure/` and
# `scripts/`. The scripts remain the source of truth — this Makefile exists
# so a new Mac can `git clone && make bootstrap` and the canonical workflows
# are discoverable via `make help`.
#
# Web-app + Express-proxy targets stay in `package.json` (npm scripts), as
# this Makefile focuses on shell-orchestrated infra + podcast operations.

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── repo paths (do not edit) ────────────────────────────────────────────────
AZURE_DIR     := infra/azure
SCRIPTS_DIR   := scripts
PODCAST_DIR   := $(SCRIPTS_DIR)/podcast

# ── targets ─────────────────────────────────────────────────────────────────

.PHONY: help
help:  ## Print this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Multi-Mac handoff ───────────────────────────────────────────────────────

.PHONY: bootstrap
bootstrap:  ## One-command setup for a new Mac (Azure + skills). See docs/multi-mac-runbook.md.
	@$(AZURE_DIR)/bootstrap-new-mac.sh

.PHONY: install-skills
install-skills:  ## Install Claude Code skills + agent wrappers from this repo into the runtime.
	@$(SCRIPTS_DIR)/install-claude-skills.sh

.PHONY: install-skills-dry
install-skills-dry:  ## Dry-run the skill installer (no files written).
	@$(SCRIPTS_DIR)/install-claude-skills.sh --dry-run

# ── Azure infra ─────────────────────────────────────────────────────────────

.PHONY: provision
provision:  ## Provision (or update) the Azure stack per infra/azure/azure-config.env.
	@$(AZURE_DIR)/provision-azure.sh

.PHONY: store-keys
store-keys:  ## Fetch Azure secrets into macOS Keychain (Key Vault priority when enabled).
	@$(AZURE_DIR)/store-keychain-keys.sh

.PHONY: verify
verify:  ## Run the Azure health check (resources + Keychain entries).
	@$(AZURE_DIR)/verify-azure.sh

.PHONY: azure-probe
azure-probe:  ## Connectivity probe — credentials + live round-trip (set SKIP_LIVE=1 to skip HTTP).
	@python3 $(PODCAST_DIR)/test_azure_connectivity.py

.PHONY: migrate-to-keyvault
migrate-to-keyvault:  ## Push Keychain secrets up to Azure Key Vault (run on primary Mac only).
	@$(AZURE_DIR)/migrate-to-keyvault.sh

# ── Podcast pipeline ────────────────────────────────────────────────────────

.PHONY: podcast-ingest
podcast-ingest:  ## OCR + translate a PDF source. Args: SRC=path/to.pdf BOOK=<slug>
	@test -n "$(SRC)"  || (echo "ERROR: set SRC=path/to.pdf" >&2; exit 2)
	@test -n "$(BOOK)" || (echo "ERROR: set BOOK=<book-slug>" >&2; exit 2)
	@python3 $(PODCAST_DIR)/ingest_source.py "$(SRC)" --book-slug "$(BOOK)"

.PHONY: podcast-transcribe
podcast-transcribe:  ## Azure-STT an episode MP3. Args: BOOK_DIR=... EP=EP##-slug AUDIO=path/to.mp3
	@test -n "$(BOOK_DIR)" || (echo "ERROR: set BOOK_DIR=..." >&2; exit 2)
	@test -n "$(EP)"       || (echo "ERROR: set EP=EP##-slug" >&2; exit 2)
	@test -n "$(AUDIO)"    || (echo "ERROR: set AUDIO=path/to.mp3" >&2; exit 2)
	@python3 $(PODCAST_DIR)/transcribe_episode.py "$(BOOK_DIR)" "$(EP)" "$(AUDIO)"

.PHONY: podcast-audit
podcast-audit:  ## Run the empirical-transcript audit. Args: BOOK_DIR=... EP=EP##-slug
	@test -n "$(BOOK_DIR)" || (echo "ERROR: set BOOK_DIR=..." >&2; exit 2)
	@test -n "$(EP)"       || (echo "ERROR: set EP=EP##-slug" >&2; exit 2)
	@python3 $(PODCAST_DIR)/audit_transcript.py "$(BOOK_DIR)" "$(EP)"

.PHONY: podcast-post-publish
podcast-post-publish:  ## Post-publication wrapper: (optional) transcribe → audit → print challenger next-step.
	@test -n "$(BOOK_DIR)" || (echo "ERROR: set BOOK_DIR=..." >&2; exit 2)
	@test -n "$(EP)"       || (echo "ERROR: set EP=EP##-slug" >&2; exit 2)
	@python3 $(PODCAST_DIR)/post_publish.py "$(BOOK_DIR)" "$(EP)" $(if $(AUDIO),"$(AUDIO)",)

# ── Astro site ──────────────────────────────────────────────────────────────

SITE_PORT := 4322
SITE_URL  := http://localhost:$(SITE_PORT)/library

.PHONY: site
site:  ## Kill any running dev server, restart it, and open the Library in your browser.
	@echo "→ Stopping any process on port $(SITE_PORT)…"
	@lsof -ti :$(SITE_PORT) | xargs kill -9 2>/dev/null || true
	@echo "→ Starting Astro dev server…"
	@cd plan-dashboard && npm run dev &
	@echo "→ Waiting for server to be ready…"
	@for i in $$(seq 1 20); do \
		curl -s -o /dev/null http://localhost:$(SITE_PORT)/ && break; \
		sleep 0.5; \
	done
	@echo "→ Opening $(SITE_URL)"
	@open $(SITE_URL)

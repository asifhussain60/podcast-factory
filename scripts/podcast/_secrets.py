"""_secrets.py — single credential resolver for the whole pipeline.

Resolution order for every secret (first hit wins):
  1. environment variable        — CI / one-shot override
  2. macOS login keychain        — fast local cache
  3. Azure Key Vault             — the SOURCE OF TRUTH (podcast-factory-vault)

The vault is read via the `az` CLI (`az keyvault secret show`), so no extra
Python SDK dependency and it reuses the operator's existing `az login`. Results
are cached in-process. This replaces the scattered, keychain-only loaders
(`_load_gemini_key`, `_load_claude_key`, `_azure._resolve`) with one path, so a
machine that has the keychain populated AND a machine that only has `az login`
both resolve every credential.

Vault secret names (provisioned 2026-06-02; see infra/azure/migrate-to-keyvault.sh):
  llm-anthropic-api-key, llm-gemini-api-key,
  azure-podcast-factory-{docintel,translator,speech,storage}-<field>
"""

from __future__ import annotations

import functools
import os
import subprocess

KEY_VAULT_NAME = os.environ.get("PODCAST_FACTORY_KEYVAULT", "podcast-factory-vault")


@functools.lru_cache(maxsize=256)
def keyvault_secret(kv_name: str) -> str | None:
    """Return a secret value from the Azure Key Vault, or None if unavailable.

    Never raises — a missing `az`, a failed login, or an absent secret all return
    None so callers can fall through / surface their own error.
    """
    try:
        r = subprocess.run(
            [
                "az",
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                KEY_VAULT_NAME,
                "--name",
                kv_name,
                "--query",
                "value",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


@functools.lru_cache(maxsize=256)
def resolve_secret(
    env: tuple[str, ...] = (),
    vault: str | None = None,
) -> str | None:
    """Resolve one secret: env var(s) → Azure Key Vault. None if absent.

    DETERMINISTIC-TO-VAULT (2026-06-04): the macOS-keychain tier was removed. A
    keychain cache could drift from the vault and shadow it, making resolution
    machine-dependent. Now the Azure Key Vault is the single source of truth on
    every machine; env vars remain ONLY as an explicit CI/override escape hatch
    (an empty env value — e.g. the Claude-desktop ANTHROPIC_API_KEY="" — is
    skipped, so it never shadows the vault).
    """
    for name in env:
        val = os.environ.get(name)
        if val:
            return val.strip()
    if vault:
        val = keyvault_secret(vault)
        if val:
            return val
    return None


def scrub_conflicting_anthropic_env() -> None:
    """Remove the EMPTY ANTHROPIC_AUTH_TOKEN / ANTHROPIC_CUSTOM_HEADERS that the
    Claude-desktop runtime injects — they make the anthropic SDK raise
    APIConnectionError even with a valid api_key. Only pops when the value is the
    empty string, so a genuinely-configured token is never touched. Scoped to the
    current process (pipeline scripts run as subprocesses), so the parent session
    is unaffected. Leaves ANTHROPIC_BASE_URL intact (it's the correct endpoint).
    """
    for var in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS"):
        if os.environ.get(var, "non-empty") == "":
            os.environ.pop(var, None)


def get_anthropic_key() -> str:
    scrub_conflicting_anthropic_env()
    val = resolve_secret(env=("ANTHROPIC_API_KEY",), vault="llm-anthropic-api-key")
    if not val:
        raise RuntimeError(
            "Anthropic API key not found. Checked env ANTHROPIC_API_KEY and Key Vault "
            "secret 'llm-anthropic-api-key'. Run `az login` (the vault is the source "
            "of truth). NOTE: this key is for the SDK refinement path only — claude -p "
            "uses the flat-rate Max subscription, not this key."
        )
    return val


def get_gemini_key() -> str:
    val = resolve_secret(env=("GEMINI_API_KEY", "GOOGLE_API_KEY"), vault="llm-gemini-api-key")
    if not val:
        raise RuntimeError(
            "Gemini API key not found. Checked env GEMINI_API_KEY/GOOGLE_API_KEY and Key "
            "Vault secret 'llm-gemini-api-key'. Run `az login` (the vault is the source of truth)."
        )
    return val


# NOTE (cost policy 2026-06-04): there is deliberately NO hydrate_env() that
# pre-loads ANTHROPIC_API_KEY into the process environment. Doing so would divert
# `claude -p` off the flat-rate Claude Max subscription onto the metered API — a P0
# cost violation. Claude reasoning is maximized on Max via `claude -p`; the paid
# Anthropic/Gemini keys are pulled ON DEMAND by get_anthropic_key()/get_gemini_key()
# only at the SDK/Gemini call sites that structurally need them.


# Scrub the conflicting empty Anthropic env vars on import, so any module that
# imports _secrets (the LLM call sites) builds its SDK client in a clean env.
scrub_conflicting_anthropic_env()

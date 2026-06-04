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
            ["az", "keyvault", "secret", "show",
             "--vault-name", KEY_VAULT_NAME, "--name", kv_name,
             "--query", "value", "-o", "tsv"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def _keychain(service: str) -> str | None:
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


@functools.lru_cache(maxsize=256)
def resolve_secret(
    env: tuple[str, ...] = (),
    keychain: str | None = None,
    vault: str | None = None,
) -> str | None:
    """Resolve one secret: env var(s) → keychain → Azure Key Vault. None if absent."""
    for name in env:
        val = os.environ.get(name)
        if val:
            return val.strip()
    if keychain:
        val = _keychain(keychain)
        if val:
            return val
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
    val = resolve_secret(
        env=("ANTHROPIC_API_KEY",),
        keychain="anthropic_api_key",
        vault="llm-anthropic-api-key",
    )
    if not val:
        raise RuntimeError(
            "Anthropic API key not found. Checked env ANTHROPIC_API_KEY, keychain "
            "'anthropic_api_key', and Key Vault secret 'llm-anthropic-api-key'. "
            "Run `az login` or `cd infra/azure && bash pull-secrets.sh`."
        )
    return val


def get_gemini_key() -> str:
    val = resolve_secret(
        env=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        keychain="gemini_api_key",
        vault="llm-gemini-api-key",
    )
    if not val:
        raise RuntimeError(
            "Gemini API key not found. Checked env GEMINI_API_KEY/GOOGLE_API_KEY, "
            "keychain 'gemini_api_key', and Key Vault secret 'llm-gemini-api-key'. "
            "Run `az login` or `cd infra/azure && bash pull-secrets.sh`."
        )
    return val


# Scrub the conflicting empty Anthropic env vars on import, so any module that
# imports _secrets (the LLM call sites) builds its SDK client in a clean env.
scrub_conflicting_anthropic_env()

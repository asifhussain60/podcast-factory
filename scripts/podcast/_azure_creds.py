"""scripts/podcast/_azure_creds.py — Azure credential resolution for the podcast pipeline.

Extracted verbatim from _azure.py (R3 DR-005 split, 2026-07-18); behavior unchanged.
_azure.py re-exports every name here, so `import _azure` call sites keep working.

Keychain naming follows infra/azure/pull-secrets.sh exactly:
    azure-<app>-translator-key1
    azure-<app>-translator-endpoint-text
    azure-<app>-translator-region
    azure-<app>-docintel-key1
    azure-<app>-docintel-endpoint
    azure-<app>-docintel-region
    azure-<app>-speech-key1
    azure-<app>-speech-endpoint
    azure-<app>-speech-region

`<app>` defaults to "podcast-factory"; override with AZURE_APP_NAME env var if
standing up a parallel stack (per docs/azure/setup.md app-portability section).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

APP_NAME = os.environ.get("AZURE_APP_NAME", "podcast-factory")


class AzureCredsError(RuntimeError):
    """Raised when a required Azure credential cannot be resolved."""


def _read_keychain(service: str) -> str | None:
    """Return the password for `service` from the macOS login keychain.

    Returns None if the entry doesn't exist. Raises AzureCredsError if
    `security` itself is missing (i.e., we're not on macOS).
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AzureCredsError(
            "macOS `security` command not found. Either run this on macOS or "
            "set the AZURE_* env vars directly (see infra/azure/azure-config.env)."
        ) from exc
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _resolve(suffix: str, env_name: str) -> str | None:
    """Resolve a single credential: env var (CI override) → Azure Key Vault.

    DETERMINISTIC-TO-VAULT (2026-06-04): the macOS-keychain tier was removed so a
    drifted keychain cache can never shadow the vault. The vault secret name equals
    the former keychain service name (azure-<app>-<suffix>); the vault is the single
    source of truth on every machine.
    """
    if env_name in os.environ and os.environ[env_name]:
        return os.environ[env_name]
    try:
        from _secrets import keyvault_secret

        return keyvault_secret(f"azure-{APP_NAME}-{suffix}")
    except Exception:
        return None


@dataclass(frozen=True)
class DocIntelCreds:
    endpoint: str
    key: str
    region: str


@dataclass(frozen=True)
class TranslatorCreds:
    endpoint: str  # text endpoint — global service
    key: str
    region: str


@dataclass(frozen=True)
class SpeechCreds:
    endpoint: str  # region-based: https://<region>.api.cognitive.microsoft.com
    key: str
    region: str


@dataclass(frozen=True)
class LanguageCreds:
    endpoint: str  # https://<resource>.cognitiveservices.azure.com
    key: str
    region: str


@dataclass(frozen=True)
class OpenAICreds:
    endpoint: str  # https://<resource>.openai.azure.com
    key: str
    region: str
    dalle_deployment: str  # model deployment name (e.g. "dall-e-3")


def load_docintel_creds() -> DocIntelCreds:
    endpoint = _resolve("docintel-endpoint", "AZURE_DOCINTEL_ENDPOINT")
    key = _resolve("docintel-key1", "AZURE_DOCINTEL_KEY")
    region = _resolve("docintel-region", "AZURE_DOCINTEL_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Document Intelligence credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && bash pull-secrets.sh "
            f"(or export AZURE_DOCINTEL_ENDPOINT/KEY/REGION for CI)."
        )
    return DocIntelCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


def load_translator_creds() -> TranslatorCreds:
    endpoint = _resolve("translator-endpoint-text", "AZURE_TRANSLATOR_ENDPOINT")
    key = _resolve("translator-key1", "AZURE_TRANSLATOR_KEY")
    region = _resolve("translator-region", "AZURE_TRANSLATOR_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Translator credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && bash pull-secrets.sh "
            f"(or export AZURE_TRANSLATOR_ENDPOINT/KEY/REGION for CI)."
        )
    return TranslatorCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


def load_speech_creds() -> SpeechCreds:
    endpoint = _resolve("speech-endpoint", "AZURE_SPEECH_ENDPOINT")
    key = _resolve("speech-key1", "AZURE_SPEECH_KEY")
    region = _resolve("speech-region", "AZURE_SPEECH_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Speech credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && bash pull-secrets.sh "
            f"(or export AZURE_SPEECH_ENDPOINT/KEY/REGION for CI)."
        )
    return SpeechCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


def load_language_creds() -> LanguageCreds:
    """Load Azure Language (TextAnalytics) credentials.

    Used for NER, key-phrase extraction, and sentiment analysis in the
    augmentation pipeline. The resource `journal-language-market` is F0 (free
    tier: 5,000 text records/month). Upgrade to S if augmentation exceeds quota.
    """
    endpoint = _resolve("language-endpoint", "AZURE_LANGUAGE_ENDPOINT")
    key = _resolve("language-key1", "AZURE_LANGUAGE_KEY")
    region = _resolve("language-region", "AZURE_LANGUAGE_REGION")
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Language credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && bash store-keychain-keys.sh "
            f"(or export AZURE_LANGUAGE_ENDPOINT/KEY/REGION for CI)."
        )
    return LanguageCreds(endpoint=endpoint.rstrip("/"), key=key, region=region)


def load_openai_creds() -> OpenAICreds:
    """Load Azure OpenAI credentials (for DALL-E 3 image generation).

    The resource is `journal-openai` with a DALL-E 3 deployment. After
    provisioning with provision-azure.sh, run store-keychain-keys.sh to
    populate these credentials.
    """
    endpoint = _resolve("openai-endpoint", "AZURE_OPENAI_ENDPOINT")
    key = _resolve("openai-key1", "AZURE_OPENAI_KEY")
    region = _resolve("openai-region", "AZURE_OPENAI_REGION")
    deployment = _resolve("openai-dalle-deployment", "AZURE_OPENAI_DALLE_DEPLOYMENT") or "dall-e-3"
    missing = [n for n, v in [("endpoint", endpoint), ("key", key), ("region", region)] if not v]
    if missing:
        raise AzureCredsError(
            f"Azure OpenAI credentials missing: {', '.join(missing)}. "
            f"Run: cd infra/azure && bash provision-azure.sh && bash store-keychain-keys.sh "
            f"(or export AZURE_OPENAI_ENDPOINT/KEY/REGION for CI)."
        )
    return OpenAICreds(endpoint=endpoint.rstrip("/"), key=key, region=region, dalle_deployment=deployment)

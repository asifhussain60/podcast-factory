# Azure Pipeline — Operator's Guide

This directory is the field guide for the Azure side of the podcast-factory
pipeline: how it's wired, how to bring it up from scratch, how to keep it
running, and what to do when it breaks. The architecture overview at
[docs/azure/architecture.md](architecture.md) shows
how Azure fits into the larger pipeline; this directory carries the deep
operational detail.

## What lives where

| File | Purpose |
|------|---------|
| [setup.md](setup.md) | Bringing the Azure stack up from zero. Start here on a fresh Mac. |
| [architecture.md](architecture.md) | What each resource does and why it exists. |
| [operations.md](operations.md) | Day-2 maintenance: key rotation, budgets, scaling. |
| [troubleshooting.md](troubleshooting.md) | Symptom → fix decision tree. The pitfalls we hit, and how to avoid them. |

Executable artifacts (scripts + config templates) live in [`infra/azure/`](../../infra/azure/).

## At a glance

The Azure stack exists to OCR scanned Arabic PDFs and translate them to
English. The journal app's `/podcast` skill needs faithful raw translations
of Ismaili/Fatimid sources before it can build NotebookLM-ready episode
bundles — those translations are the work this stack produces.

Four resources, one region, one resource group:

```
rg-journal-ai (East US)
├── journal-translator     Azure AI Translator (Standard S1)
├── journal-docintel       Azure AI Document Intelligence (Free F0)
├── journalpodcaststorage  StorageV2 / LRS
│   ├── source-arabic         input PDFs (Arabic)
│   ├── source-urdu           input PDFs (Urdu)
│   └── translated-english    output translations
└── journal-ai-monthly-cap Budget — $50/mo cap with alerts
```

Keys live in macOS Keychain. Future Mac portability migrates them to Key
Vault — flag in the config flips one switch.

## When to use this guide

- **First time on this Mac** → [setup.md](setup.md)
- **New Mac, app already provisioned** → [setup.md § "Re-using an existing Azure stack"](setup.md)
- **Same recipe for a different app** → [setup.md § "Adapting for a different app"](setup.md)
- **Something stopped working** → [troubleshooting.md](troubleshooting.md)
- **Need to rotate a key, scale up Doc Intel, or change region** → [operations.md](operations.md)
- **Want to understand the design** → [architecture.md](architecture.md)

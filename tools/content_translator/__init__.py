"""content_translator — Urdu→English translation + adaptation for source-extractor bundles.

Sibling to tools/content_reviewer. Three stages:
  translate  — Azure Translator literal Urdu→English → raw-extract.en.md
  adapt      — In-conversation Claude polish + Fatimid-source augmentation → adapted-extract.en.md
  seal       — Stamp bundle.yml stage transition (adapted → challenged after challenger runs)

Stage flow:  reviewed → translated → adapted → challenged
"""

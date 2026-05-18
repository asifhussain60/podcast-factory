# Free and Open-Source OCR / Translation / Refinement Utilities for the Journal App

## OCR and PDF handling

- **OCRmyPDF** — wraps Tesseract and adds searchable text layers to scanned PDFs. Use for PDF-in/PDF-out workflows.
- **Tesseract OCR** — baseline open-source OCR engine. Use `ara+eng` for Arabic/English mixed scans.
- **PaddleOCR / PaddleOCR-VL** — stronger open-source OCR/document parsing candidate for Arabic, layout, tables, and mixed scripts.
- **RapidOCR** — ONNX-friendly OCR runtime that can be easier to deploy locally.
- **PyMuPDF** — fast PDF page rendering, text extraction, page counting, and image extraction.
- **pdfminer.six** — fallback text extraction and layout-aware parsing.
- **Poppler utilities** — `pdftotext`, `pdftoppm`, `pdfinfo`; required for robust PDF extraction and rasterization.
- **qpdf** — repair, split, linearize, and normalize malformed PDFs.
- **unpaper** — deskew and clean scanned book pages.
- **OpenCV** — image preprocessing: thresholding, deskewing, denoising, margin removal, page splitting.
- **img2pdf** — rebuild processed page images into PDFs when needed.

## Arabic normalization and NLP

- **camel-tools** — Arabic NLP toolkit for morphology, tokenization, normalization, and named entity support.
- **farasapy / Farasa wrapper** — useful for segmentation and Arabic preprocessing where licensing permits.
- **python-bidi + arabic-reshaper** — display correction for Arabic text in preview UIs.
- **regex / unicodedata** — Unicode normalization and Arabic presentation-form cleanup.

## Translation support

Open-source machine translation for classical Arabic is weaker than paid cloud translation. Use these only for drafts, not final verified translations:

- **Argos Translate** — offline translation engine; useful for privacy-first rough drafts.
- **Marian NMT / OPUS-MT models** — open-source translation models; variable quality for classical Arabic.
- **NLLB models** — multilingual translation; heavier but broader coverage.

Recommendation: use open-source translation only as a local fallback and confidence comparison layer. For serious Arabic PDF translation, route through Azure or Google Cloud and keep open-source tools for preprocessing and QA.

## Search, indexing, and cross-reference

- **SQLite FTS5** — local full-text index for raw OCR, translations, glossary, and page anchors.
- **FAISS** — local vector search over paragraphs and translations.
- **sentence-transformers** — local embeddings for semantic retrieval.
- **pgvector** — if you move to PostgreSQL for larger corpora.
- **NetworkX** — graph construction for relationships between sources, concepts, people, verses, and hadith.
- **Whoosh / Tantivy bindings** — optional local search alternatives.

## NotebookLM and podcast packaging helpers

- **Pandoc** — convert markdown to DOCX, HTML, EPUB, or plain text.
- **ffmpeg** — normalize audio/video files when podcast inputs include media.
- **whisper.cpp or faster-whisper** — local transcription for audio/video source material.
- **pydub** — audio chunking and cleanup.

## Utility scripts to add to the journal app

```text
scripts/sources/intake_classify.py
scripts/sources/check_text_layer.py
scripts/sources/split_pdf_pages.py
scripts/sources/preprocess_page_images.py
scripts/sources/run_ocr.py
scripts/sources/normalize_arabic.py
scripts/sources/build_translation_batches.py
scripts/sources/validate_page_anchors.py
scripts/sources/build_source_index.py
scripts/sources/package_for_notebooklm.py
scripts/sources/qc_translation.py
```

## Required configuration

Create `config/source-processing.yaml`:

```yaml
ocr:
  default_engine: paddleocr
  fallback_engine: tesseract
  languages: [ara, eng]
translation:
  provider: azure-translator
  preserve_page_anchors: true
  raw_first: true
index:
  full_text: sqlite_fts5
  vector: faiss
  graph: networkx
notebooklm:
  max_source_bundle_scope: one_chapter_or_argument_unit
  require_context_file: true
  require_pronunciation_guide: true
```


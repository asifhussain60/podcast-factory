# Stage 02 — Extract Text

**Purpose:** Convert every source file into clean UTF-8 text that downstream stages can process.

## Input

- `WORK_DIR/00-source/` contains the original files.

## Output

- `WORK_DIR/_extracted/raw-text.md` — single concatenated Markdown file containing all source text in file order, with file boundaries marked.
- `WORK_DIR/_extracted/extraction-log.md` — per-file extraction method, confidence notes, flagged issues.

## Extraction method by file type

| File type | Method | Notes |
|---|---|---|
| `.txt`, `.md` | Read as UTF-8 | Detect encoding if not UTF-8; convert. |
| `.docx` | `python-docx` or `pandoc` | Preserve heading levels as Markdown headings. |
| `.pdf` (text-based) | `pdftotext -layout` then post-process | Try `pdftotext` first; if output is empty or garbled, treat as scanned PDF. |
| `.pdf` (scanned) | OCR via `tesseract` or vision model | One page at a time; preserve page boundaries. Log OCR confidence per page. |
| Images | OCR via `tesseract` or vision model | One image at a time, in alphabetical filename order. |
| Audio | Transcription via Whisper | Use word-level timestamps if available. |
| Video | Extract audio with `ffmpeg`, then Whisper | Discard video frames unless user requested visual analysis. |
| `.zip` | Extract to temp, recurse | Process inner files in alphabetical order. |

## Concatenation order

When the source has multiple files:

1. **Sort key:** numeric prefix in filename if present (`ch-01.txt`, `ch-02.txt`, …), else alphabetical.
2. **Boundary markers** between files in `raw-text.md`:
   ```
   <!-- FILE: ch-01.txt -->
   [content]
   <!-- END FILE: ch-01.txt -->
   ```
3. These markers are stripped at Stage 05 (clean/normalize) but used by Stage 09 (segmentation) as a fallback signal.

## OCR confidence handling

- Per-page confidence threshold: 0.80.
- Pages below threshold → mark with `<!-- OCR-LOW-CONFIDENCE -->` at the start of the page's content in `raw-text.md`.
- Words below 0.60 → wrap in `[?word?]` to flag for review.
- If more than 20% of pages are low-confidence, write `WORK_DIR/OCR-QUALITY-WARNING.md` and ask the user whether to proceed or supply a better source.

## Transcription confidence handling

- Whisper transcription: use `large-v3` model if available.
- Phrases with low confidence → wrap in `[?phrase?]`.
- Speaker diarization for interviews and dialogues (if Whisper supports it).
- Preserve approximate timestamps as Markdown HTML comments every ~30 seconds: `<!-- t=03:42 -->`.

## Extraction log

`WORK_DIR/_extracted/extraction-log.md` records:

```
## Per-file extraction

### [filename]
Method: [tool used]
Output size: [N] characters, [N] words
Issues flagged:
  – [issue 1]
  – [issue 2]
Confidence: [high | medium | low]

## Summary
Total words extracted: [N]
Total characters: [N]
Files with confidence issues: [N]
```

## Failure modes

- Unsupported file type → log in extraction-log.md, skip file, continue. Flag in final editorial notes.
- Tool not installed (e.g., `tesseract`) → write `WORK_DIR/MISSING-TOOL.md` listing what's needed, pause.
- Whisper API or local model unavailable for audio/video → pause and ask user to convert to text first.

## What this stage does NOT do

- Does not clean OCR artifacts beyond marking low-confidence regions — that's Stage 05.
- Does not detect language, tradition, or metadata — that's Stage 03 / 04.
- Does not segment into sections — that's Stage 09.

# Stage 01 — Ingest Source

**Purpose:** Accept the user's input, derive a source-slug, create the working directory, copy the input verbatim.

## Inputs

- One or more files provided by the user, or a single inline text block.
- Supported formats:
  - Text: `.txt`, `.md`
  - Word: `.docx`
  - PDF: `.pdf` (text or scanned)
  - Images: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.webp`
  - Audio: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`
  - Video: `.mp4`, `.mov`, `.mkv`, `.avi`
  - Archives of any of the above: `.zip`

## Steps

1. **Validate input exists.** If file path provided, confirm file is readable. If inline text, write to `WORK_DIR/00-source/inline.txt` after creating WORK_DIR.

2. **Pre-flight size check.** Reject sources exceeding NotebookLM limits and pause for user:
   - More than 500,000 words → ask user how to split (by chapter, by part, by file).
   - More than 200 MB per file → ask user to provide a smaller version or split.

3. **Derive source-slug.** Best-effort identifier for the work, used as the WORK_DIR name:
   - If file has frontmatter with `title:`, slugify the title.
   - Else if first line looks like a title (short, no terminating period, title-case or all-caps), slugify it.
   - Else if filename is meaningful (not `untitled.pdf`, not `scan001.tiff`), slugify the filename stem.
   - Else generate a placeholder slug `untitled-YYYYMMDD-HHMM` and flag in editorial notes.
   - Slugify rules: lowercase, strip punctuation, collapse spaces to hyphens, max 60 chars.

4. **Create WORK_DIR.** Path: `JOURNAL_DIR/_workspace/podcast/<source-slug>/`. If directory exists from a prior run, append `-rerun-N` rather than overwrite.

5. **Create the standard subdirectories:**
   ```
   WORK_DIR/00-source/
   WORK_DIR/01-refined/
   WORK_DIR/02-instructions/
   ```
   Other output files (`03-pronunciation.md`, `04-editorial-notes.md`, etc.) are written at later stages directly under WORK_DIR.

6. **Copy input verbatim to `00-source/`.** Preserve original filenames. For inline text, write as `inline.txt`. For multi-file inputs, preserve directory structure.

7. **Write a manifest** at `WORK_DIR/00-source/MANIFEST.txt`:
   ```
   Ingested: [YYYY-MM-DD HH:MM:SS]
   Source-slug: [slug]
   Files:
     – [filename] ([size] bytes, [SHA-256 first 12 chars])
   Total: [N] files, [total bytes]
   ```

8. **Stage 01 complete.** Proceed to Stage 02.

## Outputs

- `WORK_DIR/` directory created
- `WORK_DIR/00-source/` contains verbatim input
- `WORK_DIR/00-source/MANIFEST.txt` written

## Failure modes

- Input file unreadable → stop, report path, ask user to verify.
- Size exceeds limit → write `WORK_DIR/SIZE-LIMIT-EXCEEDED.md` describing the situation, pause.
- WORK_DIR already exists → auto-rename with `-rerun-N` suffix, log to editorial notes.

## What this stage does NOT do

- Does not read the source content for processing — that's Stage 02.
- Does not identify content type — that's Stage 03.
- Does not modify the source — `00-source/` is verbatim and immutable for the rest of the pipeline.

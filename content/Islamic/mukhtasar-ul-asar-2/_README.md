# Translation Edition - Mukhtasar ul Asar 2

This workspace is configured as a faithful translation-edition sample.

Source PDF:

- `_source/Mukhtasar ul Asar 2 .pdf`

Run the automated path only after confirming OCR/LLM spend:

```bash
python3 scripts/podcast/generate_translation_edition.py \
  --slug mukhtasar-ul-asar-2 \
  --source-pdf "content/Islamic/mukhtasar-ul-asar-2/_source/Mukhtasar ul Asar 2 .pdf" \
  --src-lang ar \
  --confirm-ingest
```

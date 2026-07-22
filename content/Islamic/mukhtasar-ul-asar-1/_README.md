# Translation Edition - Mukhtasar ul Asar 1

This workspace is configured as a faithful translation-edition sample.

Source PDF:

- `_source/Mukhtasar ul-Asaar part 1.pdf`

Run the automated path only after confirming OCR/LLM spend:

```bash
python3 scripts/podcast/generate_translation_edition.py \
  --slug mukhtasar-ul-asar-1 \
  --source-pdf "content/Islamic/mukhtasar-ul-asar-1/_source/Mukhtasar ul-Asaar part 1.pdf" \
  --src-lang ar \
  --confirm-ingest
```

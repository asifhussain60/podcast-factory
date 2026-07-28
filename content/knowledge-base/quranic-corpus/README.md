# Quranic Arabic Corpus — morphology data layer

Word-by-word morphological annotation of the entire Quran: every one of the
~128,000 segments carries its part of speech, and stems carry their lemma and
triliteral root. This is the deterministic reference behind the pipeline's
etymology accuracy gate (`scripts/podcast/_etymology.py`), the corpus-grounded
etymology generation prompt, and the deterministic glossary Arabic fill
(`scripts/podcast/fill_glossary_arabic.py`).

## License and attribution

> **GNU General Public License. Copyright (C) Kais Dukes, 2009–2017.**
> The Quranic Arabic Corpus — <https://corpus.quran.com> — annotated corpus of
> Quranic Arabic morphology, syntax and semantics. The raw annotation file is
> redistributed here under the GPL with its license header intact, as the GPL
> permits. The morphology data in `morphology.db` is derived from it and
> carries the same license.

## Layout

```
quranic-corpus/
  source/quranic-corpus-morphology-0.4.txt   # raw GPL annotation file (committed, header intact)
  morphology.db                              # derived SQLite (committed — consumers need zero build steps)
  README.md
```

## Rebuild (deterministic, one command)

```
python3 scripts/podcast/quranic_morphology.py            # build + verified counts
python3 scripts/podcast/quranic_morphology.py --verify   # re-check a committed DB
python3 scripts/podcast/quranic_morphology.py --root rHm # study a root's derived family
```

The build hard-asserts the corpus's documented shape (114 chapters, 6,236
verses, ~77k words, ~128k segments, 1,600+ roots, 3,000+ lemmas) and refuses to
write a DB that misses any range. If `source/quranic-corpus-morphology-0.4.txt`
is absent, the builder prints download instructions: the file must be fetched
manually from <https://corpus.quran.com/download/> after accepting the GPL
terms — it cannot be fetched non-interactively.

## Related

- `scripts/podcast/_buckwalter.py` — Buckwalter ↔ Arabic transliteration
  (fixture-pinned at `tests/fixtures/buckwalter.fixtures.json`).
- `scripts/podcast/_morphology_parse.py` — pure parser for the raw file.
- `scripts/podcast/lexicon_ingest.py` + `content/knowledge-base/lexicon.jsonl`
  — classical-lexicon meanings (Lane / Maqayis / Mufradat) joined per root.

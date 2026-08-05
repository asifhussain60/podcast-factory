# Arabic Integrity Report — spiritual-ethos

- Rule: R-ARABIC-INTEGRITY (fingerprint v1.0)
- Phase verified: `0b`
- Generated: 2026-08-05T20:48:57Z
- Verdict: FAIL

Forbidden = an Arabic span mutated/dropped/invented by an LLM pass with no
sanctioning provenance (canonical injection or glossary curation).

## AI-DROP — spans removed without sanction (12)

| NFC_text | Artifact | Anchor | Count |
|---|---|---|---|
| مواد | _system/source/text/raw-extract.md | {'line': 11} | 1 |
| ذکر | _system/source/text/raw-extract.md | {'line': 125} | 1 |
| بصارۃ | _system/source/text/raw-extract.md | {'line': 127} | 1 |
| بصیرۃ | _system/source/text/raw-extract.md | {'line': 127} | 1 |
| حقائق الایمان | _system/source/text/raw-extract.md | {'line': 127} | 1 |
| ۱۸۱ | _system/source/text/raw-extract.md | {'line': 389} | 1 |
| وَٱلَّذِينَ كَذَّبُوا۟ بِـَٔايَتِنَا سَنَسْتَدْرِجُهُم مِّنْ حَيْثُ لَا يَعْلَمُونَ | _system/source/text/raw-extract.md | {'line': 389} | 1 |
| معرفۃ | _system/source/text/raw-extract.md | {'line': 665} | 1 |
| عقل | _system/source/text/raw-extract.md | {'line': 699} | 1 |
| جزیۃ | _system/source/text/raw-extract.md | {'line': 955} | 1 |
| خَرَج | _system/source/text/raw-extract.md | {'line': 955} | 1 |
| سنۃ | _system/source/text/raw-extract.md | {'line': 955} | 1 |

## AI-INVENT — spans introduced without sanction (1)

| NFC_text | Artifact | Anchor | Count |
|---|---|---|---|
| ۱۸۱ وَٱلَّذِينَ كَذَّبُوا۟ بِـَٔايَتِنَا سَنَسْتَدْرِجُهُم مِّنْ حَيْثُ لَا يَعْلَمُونَ | _system/source/text/refined-english.md | {'line': 484} | 1 |

## AI-VOWEL-DRIFT — tashkeel altered on a protected span (1)

| Baseline | Present | Artifact | Anchor |
|---|---|---|---|
| وَلَمْ يَجْمَعْ بَيْتٌ وَاحِدٌ يَوْمَئِذٍ فِي الإِسْلامِ غَيْرَ رَسُولِ اللهِ صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ وَخَدِيجَةَ وَأَنَا ثَالِثُهُمَا | وَلَمْ يَجْمَعْ بَيْتٌ وَاحِدٌ يَوْمَئِذٍ فِي الإِسلامِ غَيْرَ رَسُولِ اللهِ صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ وَخَدِيجَةَ وَأَنَا ثَالِثُهُمَا | _system/source/text/raw-extract.md | {'line': 21} |


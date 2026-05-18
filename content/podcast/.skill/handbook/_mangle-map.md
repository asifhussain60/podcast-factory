# Generic Mangle Map — Cross-Book Name Mispronunciations

**Purpose.** Catalogs canonical Arabic / Islamic vocabulary that NotebookLM's TTS empirically mangles the same way across any book that uses it. Per-book overrides live next to the chapter at `BOOK_DIR/_system/mangle-map.md` (same table shape) and **win on conflict** with this generic map.

**Consumer.** `scripts/podcast/audit_transcript.py` reads this file via `load_generic_mangle_map()` and merges it with the per-book overrides before scanning the NotebookLM transcript for known-mangling forms.

**Maintenance.** New entries arrive from the learning pipeline — when a `TX-MANGLE:<canonical>-><mangled>` signature crosses the proposer threshold, the resulting proposal will recommend adding it here (or to the per-book file, when the canonical noun is book-specific).

**Format.** Markdown pipe table. First cell = canonical spelling (as it should appear in the chapter). Second cell = comma-separated list of empirically-observed mangled forms (lowercase substring match in the transcript).

| Canonical | Mangled forms (comma-separated) |
|---|---|
| Tasawwuf | tassel wolf, tasso wolf, tasa wolf, tassel woolf |
| Ikhlas | aclus, iclas, ick las |
| Nahj al-Balagha | najah balala, najah balaga, nahjal balaga |
| Dhul-Nun al-Misri | shakestone noon mystery, shake stone noon |
| Bay'a | bhaya, bayaa |
| Riyazat | rizat, riyzat |
| Mujahadah | mujahada, moo jahada |
| Nasir-i Khusraw | nasiri khusra, nasir kushra |
| Riya |  rhea ,  rhea., rhea  |
| Ihya Ulum al-Din |  EI ,  EI. |
| Sahih Bukhari | sahail bukhari |
| Sahih Muslim | sahi muslim |
| Sahih Sitta | sahasita, sa ha sita |
| Azwaj al-Mutahharat | aswaja al-mutaharat |
| Aisha Siddiqa | aisha siddhika |
| Fard al-ayn | fard al-an |
| Fard Kifaya | fard ki efaya |

**Note on `Hadith Qudsi`.** The audit script detects adjacent token repetition (the "X, X" doubling shape) separately; `Hadith Qudsi` mangling is caught there, not here.

**Note on entry placement.** When a canonical noun is **book-specific** (only one book has it as a named figure or work), add it to that book's `_system/mangle-map.md`, not here. This file is for vocabulary appearing across two or more podcasted books.

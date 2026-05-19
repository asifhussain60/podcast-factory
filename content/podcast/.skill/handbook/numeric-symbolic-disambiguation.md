# Numeric / Symbolic Disambiguation — Protocol

**Owned by:** the podcast skill.
**Read by:** producer (any chapter authoring on Islamic / Ismaili / classical-philosophical source material) AND podcast-challenger Loop N (P4.5).
**Authority:** [`_workspace/plan/numeric-symbolic-disambiguation-plan.md`](../../../../_workspace/plan/numeric-symbolic-disambiguation-plan.md) — design document with worked Master & Disciple Ch-02 example.

This is the **general protocol** that applies to ANY book asserting counts without enumeration, containing abjad-encoded ciphers, or applying modern glosses to pre-modern referents. The plan doc is the worked example; this file is the rule.

---

## 0. Activation triggers

Apply this protocol whenever a chapter contains ANY of:

1. **Counts without enumeration.** The text asserts "twelve X" / "seven Y" / "five Z" without naming the items. Examples: "twelve regions", "seven seas", "five intermediaries", "twelve hujjas".
2. **Abjad-encoded sequences.** Bracketed letter strings or named letter-sequences used as cipher (e.g., `(ب ج لا د م لہ م)` for the seven spheres).
3. **Chronograms.** A line whose letter-sum encodes a Hijri date.
4. **Anachronistic glosses.** A pre-modern referent translated using a modern category that didn't exist at the source's date (e.g., "seven continents" for `al-aqālīm al-sabʿa`).
5. **Letter-count claims.** "The seven letters of `kun fayakun`" — verify by counting; flag if wrong.
6. **Hisab al-Jummal value claims.** "The value of X equals Y" — verify against [`content/_shared/arabic/06-abjad-numerals.md`](../../../_shared/arabic/06-abjad-numerals.md).

If a chapter has ZERO of these, this protocol is not active. Most non-Islamic-source chapters won't activate it.

---

## 1. Per-ambiguity workflow

For each ambiguity surfaced by §0 triggers, follow this 5-step protocol:

### Step 1 — Identify
Capture the claim verbatim from the source text. Note the chapter, paragraph, and surrounding context. Do not paraphrase at this stage.

### Step 2 — Research

Resolution preference order (highest authority first):

| Tier | Source | Notes |
|---|---|---|
| 1 | **Critical edition** of the work itself | If the chapter cites a passage that the critical edition annotates with the enumeration / cipher decoding, that is authoritative. For Ismaili sources: James W. Morris's I.B. Tauris editions. |
| 2 | **Period-contemporary primary source** | Yaʿqūbī (9th c.) for early Arab geography; Ibn Ḥawqal for jazīra cartography; Nāṣir-i Khusraw for Ismaili da'wa structure. |
| 3 | **Iranica, IIS, Encyclopaedia of Islam** | Peer-reviewed scholarly references. |
| 4 | **Named medieval scholarly tradition** | When multiple medieval scholars converge on the same reading, that consensus is citable. |
| 5 | **General reference** | Wikipedia, only when paths 1-4 are exhausted AND the article cites a tier-1/2/3 source. |
| — | **WEB GUESSES / FORUMS / AI-GENERATED ANSWERS** | **NEVER ACCEPTABLE** — these are the source of inventions the protocol exists to prevent. |

### Step 3 — Classify

Each ambiguity ends in one of three classifications:

- **RESOLVED** — A tier 1–4 source provides an explicit enumeration / decoding / cross-check, AND the source is reproducible (cite work + page or section).
- **RESOLVED (framing caveat)** — Resolution exists but requires explicit host-framing language to avoid anachronism or misreading. E.g., "the Seven Seas of classical Arab geography known at the time the book was written" rather than the Greek/Mediterranean list.
- **NEEDS HUMAN REVIEW** — No tier 1–4 source resolves it, OR the source is contested. The chapter ships with this ambiguity flagged; the host signals listener-facing that "the tradition encodes X in a form that requires specialist commentary to fully decode."

### Step 4 — Record

Every ambiguity gets a row in `BOOK_DIR/_notebooklm/03-source-integrity-notes.md` under a `## Numeric/Symbolic enumeration register` section, with columns:

| Item | Chapter | Status | Authoritative source | Podcast instruction |
|---|---|---|---|---|

Plus, for anachronisms, a separate `## Anachronism register`:

| Claim | Chapter | Issue | Podcast instruction |
|---|---|---|---|

Each row is the SHIP-readiness record for that ambiguity. Loop N reads this table.

### Step 5 — Scaffold

Update the per-chapter scaffolding (`BOOK_DIR/_notebooklm/chNN-scaffolding.md`) with a `## Numeric Disambiguation` section per [`pre-refined-source-mode.md`](./pre-refined-source-mode.md). The section names each item, its classification, and the host's on-air instruction. Cross-references back to the register table.

---

## 2. The ONE-TIME enumeration rule

Once a list is enumerated for the first time in a series, it is NEVER re-enumerated.

### Why
NotebookLM hosts treat lists as conversation hooks. If twelve jazāʾir are enumerated in Episode 2 and re-enumerated in Episode 4, the listener hears the same list twice and the second time feels like padding. Worse, NotebookLM may introduce drift on the second telling (e.g., adding a Greek/Mediterranean sea to the Yaʿqūbī list).

### How
The chapter that FIRST mentions the count is the chapter that owns the enumeration. Subsequent chapters refer back ("the twelve jazāʾir we listed in Episode 2") but do not re-enumerate. This is enforced at scaffolding-authoring time AND at Loop N challenger time (one-time-enumeration check).

### Cross-episode discipline
The first-enumeration assignment is recorded in the series' `_notebooklm/05-episode-arc.md`. When a future episode's scaffolding is authored, the author checks the arc map and writes "see Episode 2" rather than re-enumerating.

---

## 3. Anachronism handling

When a chapter applies a modern category to a pre-modern referent (canonical example: "seven continents" for `al-aqālīm al-sabʿa`), the scaffolding MUST label BOTH:

1. **Period referent** — what the source's own time-frame meant by the term.
2. **Modernization** — what the modern reader thinks of when reading the translation.

The host then explicitly names which one is being used: *"the modern reader thinks of seven continents; the period text refers to the seven climes — the Greek-Ptolemaic latitudinal bands also used by the Ikhwān al-Ṣafāʾ."*

This is per the **R-NOMODERNIZE** rule in [`notebooklm-customize-prompt-rules.md`](./notebooklm-customize-prompt-rules.md). Loop M (challenger) audits transcripts post-publication for unlabeled modernizations.

### Anachronism whitelist
Some modernizations are deliberate editorial accommodations and are fine. Examples: rendering month names in Gregorian for date legibility, naming Islamic schools of jurisprudence in English. The whitelist is per-book, declared in `03-source-integrity-notes.md`.

### Anachronism blacklist
Some modernizations are ALWAYS wrong:
- "Twitter" / "X" / "social media" / "algorithm" / any named modern platform.
- "Cognitive behavioral therapy" / any named modern therapeutic modality.
- "21st century" / "in our modern world" / "today's society" — framed as the source's own register.

The Loop M DENY-modernize block (per [`...customize-prompt-rules.md`](./notebooklm-customize-prompt-rules.md) `R-NOMODERNIZE`) lists the canonical blacklist.

---

## 4. Invented content is a P0 BLOCKED finding

**This is the failure mode the protocol exists to eradicate.**

If a chapter or scaffolding file asserts an enumeration that is NOT backed by a tier 1–4 source, that is **invented content**. Per challenger Loop N (P4.5), invented content is **P0 BLOCKED** — the book CANNOT ship until either:

1. A tier 1–4 source is added to the register row, or
2. The item is reclassified as NEEDS HUMAN REVIEW (and the assertion is removed from the chapter prose, replaced with the "requires specialist commentary" framing).

### What counts as invention
- Listing "twelve regions" by inventing twelve names that don't appear in any tier 1–4 source.
- Decoding an abjad cipher without a source citation.
- Asserting a chronogram date without showing the letter-sum calculation.
- Assigning a meaning to a symbolic number ("seven represents perfection") without citing the tradition that says so.

### What does NOT count as invention
- Listing an enumeration WITH a citation that any reader can verify.
- Flagging an item as NEEDS HUMAN REVIEW and not asserting any decoding.
- Drawing a parallel between numeric structures across traditions IF the parallel itself is cited in scholarship.

### Why this rule
NotebookLM treats source text as authoritative. If we invent an enumeration and feed it to NotebookLM, the listener hears it spoken in the same authoritative voice as the verified items. The listener has no signal that one was made up. This is a quality fraud surface; the protocol exists to close it.

---

## 5. Source-preference register (which authorities for which types)

| Ambiguity type | Tier 1-2 source examples |
|---|---|
| Ismaili da'wa structure (hujja, nāṭiq, asāas, dāʿī) | Iranica §"Cosmogony vi"; Iranica §"Dāʿī"; al-Naysabūrī; Ja'far ibn Mansūr al-Yaman's own corpus |
| Twelve jazāʾir cartography | Iranica §"Dāʿī"; Ibn Ḥawqal; Nāṣir-i Khusraw |
| Seven seas (medieval Arab geography) | Yaʿqūbī (9th c.); Wikipedia §"Seven Seas / Medieval Arab geographers" (which cites Yaʿqūbī) |
| Seven oft-repeated (al-sabʿ al-mathānī) | Cross-tradition tafsīr consensus (Sunni: al-Baghawī, al-Shinqīṭī; Shia: Majlisī's *Ḥayāt al-Qulūb*); quran.com tafsir aggregation |
| Abjad / Hisab al-Jummal | [`content/_shared/arabic/06-abjad-numerals.md`](../../../_shared/arabic/06-abjad-numerals.md); Lane's *Arabic-English Lexicon*; Encyclopaedia of Islam |
| Pledge of al-Aqaba 12 | wikishia §"Pledge of al-Aqaba"; Bukhari (Merits of the Helpers) |
| Seven heavens / Ptolemaic luminaries | Ikhwān al-Ṣafāʾ Epistle on Astronomy; Suhrāb's *ʿAjāʾib al-aqālīm al-sabʿah* (902–945 CE) |
| Karūbiyya (sphere-letters) | Iranica §"Cosmogony vi"; Morris critical edition footnotes |

This register is the **starting point** for any research step. If an ambiguity falls outside these categories, escalate to a critical-edition or peer-reviewed lookup; do not improvise.

---

## 6. How Loop N (P4.5) enforces this protocol

The podcast-challenger agent runs Loop N on every chapter post-authoring. The five Loop N checks:

1. **Enumeration coverage** — every "N X" claim has either an enumeration in the per-chapter scaffolding's Numeric Disambiguation block, OR an explicit `NEEDS HUMAN REVIEW` flag in `03-source-integrity-notes.md`.
2. **One-time enumeration** — no enumeration repeated across episodes; cross-episode scan against `05-episode-arc.md`.
3. **Abjad cipher coverage** — any abjad-encoded sequence has either a sourced decoding OR a `NEEDS HUMAN REVIEW` flag.
4. **Anachronism labeling** — every anachronistic gloss has both period referent + modernization labeled, with explicit on-air host instruction.
5. **No invented content** — any enumeration without a source citation is **P0**.

### Severity ladder
- **P0 (BLOCKED)** — invented enumeration; unsourced cipher decoding. Ship is REFUSED.
- **P1 (SHIP-WITH-CAUTION)** — enumeration repeated across episodes; anachronism unlabeled. Ships with sidecar note.
- **P2 (note for next episode)** — `NEEDS HUMAN REVIEW` items still pending after publication. Tracked in the post-publication audit cadence.

---

## 7. Worked example pointer

The canonical worked example is **Master & Disciple Ch-02 (Oath and Cosmic Origins)**. The full ambiguity register, source citations, and decision log for that chapter live in:

- [`_workspace/plan/numeric-symbolic-disambiguation-plan.md`](../../../../_workspace/plan/numeric-symbolic-disambiguation-plan.md) §1 — live audit of Ch-02 ambiguities.
- `content/podcast/library/books/the-master-and-the-disciple/_notebooklm/03-source-integrity-notes.md` — the per-book register (when P4.7 scaffolding lands).
- `content/podcast/library/books/the-master-and-the-disciple/_notebooklm/ch02-scaffolding.md` Numeric Disambiguation section.

Future books on classical Islamic / Ismaili material follow the same template.

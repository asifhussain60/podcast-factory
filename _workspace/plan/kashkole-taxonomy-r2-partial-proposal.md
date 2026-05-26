# KAHSKOLE Taxonomy — Round 2 Partial Proposal

**Generated:** 2026-05-24
**Scope:** Topic retitles for 9 small binders (235 of 1,337 topics)
**Status:** Awaiting approval — NO bundles modified

Companion to the machine-readable [tools/content_classifier/data/kashkole-r2-decisions.yaml](../../tools/content_classifier/data/kashkole-r2-decisions.yaml).

For the 10 deferred binders (1,102 topics queued for the next session), see [kashkole-r2-handoff.md](kashkole-r2-handoff.md).

## How to review

Skim each binder's section below. For any title you want to revise, edit the corresponding entry in the YAML at the `binder_id`/`chapter_id`/`topic_id` key. The proposal-level structure (which topics get retitled, which binders are covered) is not under review — only the **English title text** per entry.

After review:
- ✅ approve as-is → set `approved_at` in YAML
- ✏️ edit individual entries in YAML, then approve the batch
- ⏭️  defer a specific entry → leave `confidence: low` and add `needs_revision: true` on that entry

## Confidence summary

- **227 high** — well-established Arabic/Ismaili term with English gloss (96.6%)
- **6 medium** — interpretive translation choice
- **2 low** — sparse source content; title is a stub

## Per-binder review (235 topics across 9 binders)

### Binder 5 — Selected Devotional Poetry (24 topics)

3 chapters: marsiya, Arabic poetic compositions, manāqib.

Most entries follow the convention: `<transliterated matlaʿ> — <English description>`. Examples:
- t340 `Khallaq-E-Karbala Maula Hussain Hai` → `Khallāq-e Karbalā Mawlā Ḥusayn Hai — The Creator of Karbalāʾ Is Mawlā Ḥusayn`
- t343 `Extemporary Poem By Farazdaq` → `Al-Farazdaq's Extemporaneous Qaṣīda on Imam Zayn al-ʿĀbidīn` (the famous qaṣīda recited at the Ka'ba)
- t1355 `ائے حسین` → `Ay Ḥusayn — O Ḥusayn! (Urdu marsiya, fully extracted)` — the only one with actual content

### Binder 12 — Lives and Episodes of the Duʿāt (7 topics)

5 of 7 entries are biographical/poetic, with high-confidence titles for Mālik al-Ashtar, Uways al-Qaranī, Sayyidnā al-Muʾayyad al-Shīrāzī, the Karbalāʾ martyrs. Two entries (`سیرت` and `نانا ملا شفقت حسین صاحب`) are placeholder section markers with empty content — flagged as needs_revision after content gets developed.

### Binder 16 — Collection of Selected Supplications (14 topics)

All 14 entries are duʿāʾ titles with established names. Examples:
- t832 `Dua Isteftah (Imam Jaffar Al-Sadiq)` → `Duʿāʾ al-Istiftāḥ (attributed to Imam Jaʿfar al-Ṣādiq) — The Opening Supplication`
- t830 `Talabe Afu Wal Maghfirah (Imam Ali Zainul Abideen)` → `Ṭalab al-ʿAfw wa-l-Maghfira (Imam Zayn al-ʿĀbidīn) — Seeking Pardon and Forgiveness`
- Weekday duʿāʾs (chapter 44): `Sunday — Duʿāʾs for the Day`, etc.

### Binder 18 — Inner Realities of Qurʾānic Prophet Stories (26 topics)

The Ādam-cycle chapter (cid 52) is fully retitled with 18 entries covering the cosmological/eschatological treatment of Ādam: tests, fall, repentance, expulsion, descent, Qābīl/Hābīl, and Ādam-as-Bismillāh-mamthūl. Plus chapters on the prophet-cycle structure (Nuṭaqāʾ, Mūsā via taʾwīl, ʿĪsā compared with ʿAlī, and Nūḥ's English-source entry).

### Binder 25 — Daʿāʾim al-Islām: Ṭahāra (42 topics)

5 chapters covering the full Ṭahāra treatment from Qadi al-Nuʿmān's *Daʿāʾim*: traditions, the 7 obligatory + 12 sunna acts of wuḍūʾ, najāsa, the inner taʾwīl of the 11 pillars of wuḍūʾ, and Ghusl. Every title preserves the technical term plus an English description.

### Binder 27 — Ādāb and Noble Character (40 topics)

6 chapters: Kitāb Waṣāyā Iblīs (parables of self-deception), sayings on ādāb, treatises on wilāya, aqwāl from the Ahl al-Bayt, ḍarb al-ḥikam, episodes from the Sīra. Several entries acknowledge the mothers-of-sins (Kibr/Ḥasad/Ḥirṣ), the rights of parents and the rights of ʿibād, and the Mahdī signs.

### Binder 29 — Daʿāʾim al-Islām: Ṣawm (43 topics)

4 chapters covering the inner-Ramaḍān theology: the symbolic identification of the month with ʿAlī, the three decades, the four blessed nights, Laylat al-Qadr, and the two ʿĪd prayers. Titles preserve the Ismaili technical terms (Mamthūl, Asās, Ḥujja, Nāsūt) with English gloss.

### Binder 32 — Al-Ghazālī, Kīmiyāʾ al-Saʿāda (15 topics)

2 chapters from al-Ghazālī's discipline-of-the-soul material. Sources are already in English; retitles refine the wording (e.g., `Disciplining The Soul` → `Disciplining the Soul (from al-Ghazālī's Iḥyāʾ)`).

### Binder 36 — Islām, Īmān, Iḥsān (24 topics)

3 chapters covering the foundational pedagogy: salutations (4 ḥamd formulas), introduction to ādāb and the 10 foundations, and the full Islām/Īmān/Iḥsān discourse (19 topics). Already-English titles cleaned up with diacritics and domain context (`Linguistic menaing of IMAAN` → `The Linguistic Meaning of Īmān`).

## Approval checklist

- [ ] B5 — Devotional Poetry (24 topics) — approve
- [ ] B12 — Duʿāt Lives (7 topics) — approve
- [ ] B16 — Supplications (14 topics) — approve
- [ ] B18 — Prophet Stories (26 topics) — approve
- [ ] B25 — Ṭahāra (42 topics) — approve
- [ ] B27 — Ādāb (40 topics) — approve
- [ ] B29 — Ṣawm (43 topics) — approve
- [ ] B32 — Ghazālī (15 topics) — approve
- [ ] B36 — Islām/Īmān/Iḥsān (24 topics) — approve
- [ ] All 235 approve in bulk

Once approved, the next session resumes the deferred 10 binders (1,102 topics) per [kashkole-r2-handoff.md](kashkole-r2-handoff.md).

# Promoted — `J2:density:kitab-al-riyad:EP01-the-lineage-of-a-lost-argument`

**Status.** Accepted and merged on 2026-05-18.

**What changed.**
- Extended `R-NAMES` auto-fix scope in `content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md` to cover `**Long Name**` emphasis AND `#+ **Long Name**` section-header surface forms (previously the regex matched plain prose only).
- Added 4 ceremonial-form entries to `content/_shared/arabic/05-name-alias-policy.md` (Ismaili tradition table): `Abu Hatim Ahmad ibn Hamdan al-Razi → Abu Hatim al-Razi`; `Abu Ya'qub Ishaq al-Sijistani → al-Sijistani` (already had short form, ceremonial alias added); `Hamid al-Din Ahmad ibn Abdullah al-Kirmani → al-Kirmani` (already had short form, ceremonial alias added); `Muhammad ibn Ahmad al-Nasafi → al-Nasafi`.
- Applied the fix to `content/podcast/library/books/kitab-al-riyad/chapters/ch01-the-lineage-of-a-lost-argument.txt` lines 87, 91, 97, 99 — 4 bold-header reintroductions rewritten as `**Alias** — long-form, the author of *work*.` bio anchors.
- New regression fixture under `_learning/fixtures/j2_bold_header/` (4 hits expected) keeps the rule pinned.

**Why the original proposal triggered.** 3× firings of J2 in one chapter (4× after the symmetric al-Nasafi fix was extended). The auto-fix logic was looking for plain-text occurrences and missing emphasis / heading constructs entirely.

**Acceptance check.** `python3 scripts/podcast/test_challenger.py` exits 0 with the new fixture; `build_episode_txt.py` still emits the kitab-al-riyad EP01 customize prompt clean.

**Source proposal.** Deleted from `_learning/proposals/` per workflow ("delete on promotion"). This file is the audit trail.

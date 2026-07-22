# Prompt — Arabic gloss rule

---

In **podcast-factory** (`develop`), the inline-Arabic pass
(`scripts/podcast/_book_inline_arabic.py`) is producing redundant glosses in
`content/Islamic/the-master-and-the-disciple/book/book.md`. Live example:

> the speaking Imam (الإمام) (*al-Imam al-Natiq* (الإمام الناطق)), his gate
> (*bab* (باب)), his successor (*wasi* (الوصي)), his summoners (*duat* (الدعاة))

Three renderings of one term at once — English meaning, Latin transliteration,
and Arabic script — nested two parentheses deep.

**The rule I want: where the Arabic script is present, drop the Latin
transliteration and put the English MEANING in the parentheses instead.** The
above should read:

> the speaking Imam (الإمام الناطق), his gate (باب), his successor (الوصي), his
> summoners (الدعاة)

Note this is mostly **deletion**, not authoring: the English meaning is usually
already in the prose immediately before the term.

**The carve-out that makes it intelligent.** A proper NAME has no English
meaning — for `Allah`, `Tur`, `Jafar ibn Mansur al-Yaman`, the transliteration
*is* the English rendering and must stay: `Jafar ibn Mansur al-Yaman (جعفر بن
منصور اليمن)`. Only TERMS (bab, wasi, duat, natiq) lose their transliteration.
Decide name-vs-term from the glossary, not from a hardcoded list.

Constraints:
- `_system/glossary.yml` has 68 entries with `arabic_script` and **0** with
  `english` — so the meaning must come from the prose, or the field gets
  populated as part of this. Do not invent meanings.
- Fix at the pipeline, not in `book.md` — it must survive a re-compose.
- This also closes the reviewer's twelve nested-parenthesis findings; see
  `book/book-challenger-report.md`.
- Still open and unrelated: the six `(ع)` honorifics, an editorial choice.
- Verify in the **Book Composer** (`/studio/the-master-and-the-disciple/compose`),
  not the PDF. Close that tab before any compose — it autosaves over one.
- `book.md` restores from `1b750a3` (approved base) + the three deterministic
  passes; the recovery tag is `pre-rebuild/the-master-and-the-disciple-2026-07-21`.
- Gates: `pytest scripts/podcast/tests` (1690), `cd plan-dashboard && npm test`
  (48), `npx tsc --noEmit`, `npm run lint:views`, `npm run smoke`, `ruff`.

Background if needed: `_workspace/plan/session-handoff-2026-07-21.md`.

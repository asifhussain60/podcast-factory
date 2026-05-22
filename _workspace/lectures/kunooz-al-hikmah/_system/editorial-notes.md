# Editorial Notes — Kunooz al-Hikmah (recorded lecture series)

## Source

A four-part recorded lecture series in colloquial Urdu, explaining the classical
Tayyibi-Bohra text *Kunooz al-Hikmah al-Mazboora li-Arbaab al-Ismah*
("Treasures of Wisdom Stored for the Lords of Infallibility") authored by
**Sayyidina Ali bin Hibatullah al-Makrami**.

Audio files (MP3) live locally under `library/audio/kunooz-al-hikmah/` and are
gitignored — the derived English transcripts and authored chapters travel
through the repo.

| File | Duration | Path |
|---|---|---|
| EP01 | 41m 11s | `01 GH - Kunooz Al-Hikmah.mp3` |
| EP02 | 38m 51s | `02 GH - Kunooz Al-Hikmah.mp3` |
| EP03 | 48m 5s  | `03 GH - Kunooz Al-Hikmah.mp3` |
| EP04 | 44m 58s | `04 GH - Kunooz Al-Hikmah.mp3` |

The speaker is a senior Bohra teacher (identity to be confirmed by Asif) and
the lectures are live recordings — there is incidental cross-talk with
attendees (notably "Shabbir Bhai", "Muslim Bhai", "Shaman Bhai") and one
audio-quality interruption in EP03's opening minutes. The body of each
lecture is the speaker reading and unpacking sections of al-Makrami's text.

## Tradition + theological frame

Dawoodi Bohra (Tayyibi Mustaali Ismaili) discourse. Key technical concepts
that recur across all four lectures, used in their proper sense (not as
generic Sunni terminology):

- **Dai / Du'at** — preacher/missionary; plural for the line of Dais after
  the seclusion of the Imam.
- **Hudood** — the limits/ranks of the spiritual hierarchy (Imam, Hujjat,
  Dai, Ma'zoon, Mukasir, etc.).
- **Hujjat** — the "proof" rank just below the Imam; technical term, not
  generic.
- **Wilayat** — the authority/guardianship of the Imam and the Ahl al-Bayt.
- **Ismah / Arbaab al-Ismah** — infallibility / "Lords of Infallibility"
  (the Imams + the Du'at by their participation).
- **Asraar / Anwaar** — secrets / lights; technical pair the speaker
  develops in EP02 around the Dai's spiritual harvest.
- **Riyas / Nawasid-e-zilliyah** — subtle spiritual emanations and their
  shadow-correlates; EP04 unpacks this at length.
- **Naasut / Malakut / Jabarut** — the three realms (human / angelic /
  divine power); the speaker uses the variant *Nasur-e-Khaas / Nasur-e-Adna
  / Nasur-e-Awsat / Nasur-e-Tabi / Nasur-e-Zilli* for graded
  manifestations within Naasut.
- **Adam-e-Aal-e-Aba** — "Adam of the Family of the Cloak" — title applied
  to Imam Ali Zain-ul-Abideen in EP04.

## Transcription pipeline

Two-source workflow per lecture:

1. **TurboScribe** (primary) — Asif's paid commercial transcription, English
   output with section timestamps in `(MM:SS - MM:SS)` markers. Drops under
   `library/turboscribe/kunooz-al-hikma/` as `.txt`. Substantially better
   than out-of-the-box Azure at preserving religious-vocabulary
   transliterations (*Bismillah*, *Ta'wuz*, *Dawah*, etc. survive cleanly).
2. **Azure Speech** (secondary, cross-reference) — `transcribe_episode.py
   --locale ur-IN`. Produces an Urdu Nastaliq transcript that is the
   ground-truth check when TurboScribe's English is ambiguous or
   word-broken. Output lands in `transcripts/` (gitignored).

**EP03 exception**: TurboScribe captured only 329 words from 48 min of audio
(English-detection apparently failed on the Arabic/Urdu density). Azure
Speech on the same file returned 4,192 words. EP03's authoring runs through
the Azure→Translator path instead of TurboScribe.

## Editorial decisions

- **Voice** — third-person narrative attribution: *"the speaker explains
  that..."* / *"al-Makrami writes that..."*. Do not put words in the
  speaker's mouth or extrapolate Tayyibi theology beyond what is literally
  stated in the recording.
- **Religious sensitivity** — this is in-tradition instruction. The
  chapter prose preserves the technical theological vocabulary as the
  speaker uses it; it does not "translate" specialized terms into generic
  Sunni equivalents (e.g. *Du'at* stays as *Du'at*, not "preachers"; *Imam*
  in the Imami sense, not "prayer-leader").
- **Quranic citations** — the speaker quotes Arabic verses then explains in
  Urdu. The chapter renders the verse in transliteration + English
  rendering on first mention; for subsequent mentions of the same verse,
  English alone suffices.
- **Attendee cross-talk** — names like "Shabbir Bhai" / "Muslim Bhai" are
  preserved when load-bearing (they ask substantive questions); incidental
  chatter ("Bismillah, brother, can you hear me?") is dropped.
- **Repetitions** — TurboScribe often echoes phrases due to ASR confusion
  on similar-sounding Urdu words. These are merged silently in chapter
  prose; the underlying meaning is preserved.

## Anti-mangling overrides (NotebookLM history)

To be populated after EP02 first run through `/podcast` reveals which terms
NotebookLM butchers. Likely candidates given the source vocabulary:

- **Ali bin Hibatullah al-Makrami** — full canonical form; never "Ali bin
  Hibah" or "al-Makrami" alone on first mention.
- **Arbaab al-Ismah** — locked phonetic; never "Arbab" or "Ismat" alone.
- **Adam-e-Aal-e-Aba** — full phrase, locked; never "Adam Allah" or
  letter-spelled.

## Status

- 2026-05-18 — book directory scaffolded; EP02 chapter authoring in
  progress; EP01/EP03/EP04 pending after EP02 quality gate.

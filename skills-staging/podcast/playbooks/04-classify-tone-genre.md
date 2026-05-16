# Stage 04 — Classify Tone, Genre, and Tradition

**Purpose:** Identify the source's tone (which must be preserved through refinement) and detect the tradition (which determines the enrichment whitelist).

## Input

- `WORK_DIR/_extracted/raw-text.md`
- `WORK_DIR/_metadata.yml` (from Stage 03)

## Output

- Append to `WORK_DIR/_metadata.yml`:
  - `tone` block with multi-label tone classification.
  - `tradition` block with detected tradition + confidence.
- If tradition confidence is low or `source-tradition=auto` was passed, write `WORK_DIR/tradition-confirmation.md` and pause for user.

## Tone classification

Multi-label. A work can be reverent AND argumentative. Score each on a 0–1 scale:

| Tone label | Signals |
|---|---|
| `reverent` | Devotional invocations, honorifics, theological vocabulary, restraint in tone |
| `narrative` | Dialogue, scene-setting, character actions, temporal flow |
| `argumentative` | Premises and conclusions, "therefore", counterposition language |
| `conversational` | Direct address, contractions, colloquialisms, oral cadence |
| `academic` | Citations, hedged claims, jargon, formal voice |
| `literary` | Imagery, metaphor, lyrical sentence structure |
| `instructional` | Imperatives, step-by-step structure, "you must" / "you should" |
| `polemical` | Strong assertions against named positions, urgency, emotional charge |
| `meditative` | Repetition, slow pacing, internal/spiritual focus |
| `analytical` | Categorization, taxonomies, formal definitions |

Record the top 3 tones with scores. These drive the refinement stage's tone preservation:

```yaml
tone:
  - label: "reverent"
    score: 0.92
  - label: "narrative"
    score: 0.85
  - label: "instructional"
    score: 0.70
```

## Tradition detection

Tradition signals come from:

1. **Named figures.** Cross-reference figures named in the source against tradition figure-lists in `traditions/<name>.yml`. Each match adds to that tradition's score.
2. **Technical vocabulary.** Each tradition file has a `signal_terms` list. Each match adds to score.
3. **Citation patterns.** Bibliographic style, scripture quotation conventions, scholarly forms.
4. **Explicit declarations.** If the source explicitly states its tradition ("from the Ismaili da'wah", "Catholic theology", "Vedanta"), that's a strong signal.

Score traditions and pick the top one:

```yaml
tradition:
  detected: "ismaili"
  confidence: 0.88
  signals:
    – Named figure: "Imam Ja'far al-Sadiq" matches ismaili.yml figure list
    – Named figure: "al-Qadi al-Numan" matches ismaili.yml figure list
    – Signal term: "taa-weel" matches ismaili.yml signal_terms
    – Signal term: "wilaayah" matches ismaili.yml signal_terms
    – Citation pattern: Fatimid-era source citations
  alternatives:
    - name: "islamic"
      confidence: 0.72
      note: "Some signals are shared with broader Islamic tradition"
```

## Confidence thresholds

- ≥ 0.80 and `source-tradition=auto` → proceed with detected tradition; record decision in editorial notes; no prompt to user.
- 0.60–0.79 → write `WORK_DIR/tradition-confirmation.md` asking the user to confirm:
  ```
  # Tradition Confirmation Needed
  
  Detected tradition: [name] (confidence [N])
  Alternative: [name] (confidence [N])
  
  Signals that drove this detection:
    – [signal 1]
    – [signal 2]
  
  Please confirm by editing the line below and re-running:
    USER_DECISION: [confirmed_tradition_name | none | other]
  ```
- < 0.60 → ask user explicitly; default proposed is `none` (generic enrichment only).

If user passed `source-tradition=<name>` explicitly, skip the detection prompt — use the supplied tradition regardless of detection.

## Tradition file structure

Each `traditions/<name>.yml`:

```yaml
name: ismaili
description: "Ismaili tradition — comprehensive whitelist for enrichment"

figures:
  - "Prophet Muhammad"
  - "Imam Ali"
  - "Imam Hasan"
  - "Imam Husayn"
  # ... and so on

signal_terms:
  - "taa-weel"
  - "wilaayah"
  - "natiq"
  - "da'i"
  # ... and so on

allowed_enrichment_sources:
  - "The Holy Qur'an"
  - "Hadith collections used in Ismaili tradition"
  - "First seven Imams (in the Ismaili line)"
  - "Qadi al-Numan"
  - "Nasir-i Khusraw"
  - "al-Sijistani"
  - "al-Kirmani"
  - "Nasir al-Din al-Tusi"
  - "Contemporary IIS scholarship"
  - "Fatimid philosophical sources"

forbidden_enrichment_sources:
  - "Non-Ismaili hadith collections used to contradict Ismaili interpretation"
  - "Sectarian polemics from outside the tradition"
  - "Modern non-Ismaili commentary on Ismaili texts (unless explicitly historical/academic context)"

modern_analogy_register:
  preferred_domains:
    - "software architecture (interface / code / architecture mirrors outer / inner / innermost)"
    - "professional licensing and authorization (oath / covenant)"
    - "mentorship and apprenticeship (scholar / seeker)"
    - "secure access systems (knowledge transmission)"
  avoid_domains:
    - "any analogy that flattens spiritual hierarchy to mere institutional structure"
    - "any analogy that equates revelation with information theory"

tone_preferences:
  - "preserve reverence — no casual rephrasing of theological claims"
  - "preserve honorifics — Prophet ﷺ, Imam (in pronunciation guide as Imaam)"
  - "preserve restraint — do not amplify or dramatize"
```

## Failure modes

- All traditions score below 0.6 AND user did not specify → write `tradition-confirmation.md` proposing `none`, pause.
- User specifies a tradition for which no `<name>.yml` exists → write `WORK_DIR/MISSING-TRADITION-FILE.md` listing what's needed, pause.

## What this stage does NOT do

- Does not enrich content — that's Stage 10.
- Does not generate analogies — that's Stage 11.
- Does not modify the raw text — that's Stage 05.

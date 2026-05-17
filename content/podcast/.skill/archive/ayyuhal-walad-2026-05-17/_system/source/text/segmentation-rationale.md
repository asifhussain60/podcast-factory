# Segmentation Rationale — Ayyuhal Walad

## Raw inventory

The source PDF contains a TOC of 25 entries (Introduction through Supplication). Verified against the body, these collapse into 22 distinct sections (three TOC entries turned out to be paragraphs inside a parent section, not standalone units). The 22-section inventory lives in `inventory.yml`.

## Episode segmentation

5 episodes total. Geometry rationale per episode:

### EP01 — Imam Ghazali's Response to the Letter (sections 1+2)

The first two TOC sections (Introduction + Response) form a single argumentative arc: the student writes the letter (introduction), Ghazali responds (response chapter). The response chapter alone moves through six movements — opening warning, Junaid's dream and the lion/medicine analogies, the angel and the worshipper, the intention test, the night prayer, and the closing pivot to Mujahadah and the four conditions. These movements depend on each other; splitting them loses narrative force. We accept that this bundle runs ~3,500 words (over the standard 2,800 ceiling) in exchange for a coherent single-arc episode. **Existing bundle, preserved.**

### EP02 — Hatim's Eight Benefits (section 3)

Section 3 is a self-contained vignette: Shaqiq al-Balkhi asks Hatim, his student of thirty-three years, what he has learned. Hatim gives eight numbered benefits. The structure is enumerative and the unit is clean. One section = one episode at ~2,100 words refined.

### EP03 — The Path (sections 4 through 11)

Sections 4–11 are short (each 200–400 words) but thematically tight: they unfold the *Tariqah* — the path of the seeker. Qualities of a spiritual guide, obedience to the guide, outer etiquettes, inner etiquettes, and then four "Reality of..." sections (Tasawwuf, Servitude, Tawakkul, Ikhlas). These belong together; splitting them across multiple episodes would produce eight 250-word fragments. Total raw ~2,175 words → refined ~2,100.

### EP04 — The Eight Admonitions: Ghazali's Four Cautions (sections 12 through 16)

The "Eight Admonitions" header in the source covers four parallel cautions, each with an extended treatment: principles of debate (caution 1), reality of preaching (caution 2), staying away from rulers (caution 3), not accepting gifts from rulers (caution 4). Sections 14–16 are framing material (categories of patients, advice according to comprehension, individual capable of benefiting) that supports the preaching caution and is folded into it. Raw ~3,009 words → refined ~2,700 (at the top of the standard band, justified by the parallel structure of four cautions in one architecture).

### EP05 — The Method of Living and the Closing Prayer (sections 17 through 22)

The final cluster: "Four Matters Worthy of Our Actions" (sections 17–20: relating to God, relating to people, the obligation to study, not stockpiling food) plus the closing supplication (sections 21–22). Raw ~1,866 words → refined ~1,900. Clean closing unit.

## Deviation from the legacy 7-episode plan

The legacy `_workspace/podcast/ayyuhal-walad/_meta/_segments/segments.yml` proposed splitting Ghazali's response chapter (section 2) into three sub-episodes (frame, knowledge-that-saves, closing-counsels). The existing EP01 bundle — already built and reviewed at the scratchpad layer — collapses these three into one. Rather than discard that work, this plan preserves EP01 as a single response-chapter episode and matches the legacy plan from section 3 onward. Net delta: 7 → 5 episodes.

If, after generation, EP01 reads as too long against the others, the recommended future split is into three thematic units:
  - **The Frame and the First Counsel** (movements 1–2 of EP01: opening warning, Junaid, lion, medicine, the Quranic stack)
  - **The Angel and the Intention** (movements 3–4: the man who answers the angel, the intention test, the first question at the grave, "knowledge without actions is madness")
  - **The Night, Mujahadah, and the Doorway** (movements 5–6: Tahajjud, the dove poetry, worship as obedience, Mujahadah, the four conditions of the seeker, Shibli's hadith)

This split is a future option, not part of the current generation pass.

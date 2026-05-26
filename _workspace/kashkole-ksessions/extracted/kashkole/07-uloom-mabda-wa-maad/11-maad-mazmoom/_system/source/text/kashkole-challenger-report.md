# KAHSKOLE Challenger Report
*Generated: 2026-05-25T16:05:04.130804+00:00 | Model: claude-haiku-4-5-20251001*

## Deterministic Validator
Validator: 0 P0 errors, 2 P1 warnings
  ⚠ [V2] 66 ⟪ar:…⟫ marker(s) absent or form-changed in adapted
      ⟪ar:’برہوت ‘⟫ ⟪ar:’خرقا ‘⟫ ⟪ar:’صورات مستخدمۃ ‘⟫ ⟪ar:’خالدین فیھا ‘⟫ ⟪ar:‏ وَمَآ أُبَرِّئُ نَفْسِىٓ ۚ إِنَّ ٱلنَّفْسَ لَأَمَّارَةٌۢ بِٱلسُّوٓءِ إِلَّا مَا رَحِمَ رَبِّىٓ ۚ إِنَّ رَبِّى غَفُورٌۭ رَّحِيمٌۭ ‎⟫
  ⚠ [V6] 1 citation(s) reference non-allowlisted authors
      cite-14: Exegetical tradition

# Challenge Report — Planned Resurrection
**Date:** 2026-05-25  
**Verdict:** WARN

---

### Checks

- **Prose quality**: The English is scholarly and generally readable, with appropriate formal register. Sentence structure is occasionally complex but follows logically. No evidence of raw machine translation; however, some passages remain dense and could benefit from restructuring for clarity.

- **Terminology**: Ismaili key terms are consistently transliterated with Arabic markers and first-occurrence glosses (nafs ammarah bi'l-su', nafs lawwamah, etc.). The glossing is consistent and accessible. However, the validator flagged 66 missing or form-changed Arabic markers, suggesting systematic loss during adaptation—a technical debt rather than a content error.

- **Faithfulness**: The adapted content faithfully conveys the doctrinal material on the stages of the soul (nafs), punishment in the grave, and moral accountability. The analogy between the hamstrung she-camel and the corrupted soul preserves the source's allegorical method. No major omissions detected in the sample; theological logic flows coherently.

- **Citations**: Three citations provided. Cite-1 and cite-2 reference high-authority Ismaili exegetical works (*Rahat al-ʿAql*, *Kitab al-Yanabiʿ*) with high confidence and training grounding. **Cite-14** (referenced in validator output as "Exegetical tradition") appears non-allowlisted—this is a P1 warning. All three visible citations are relevant to their excerpts and support the text's doctrinal claims.

- **Section structure**: Four section headings are meaningful and hierarchically appropriate, tracking a logical progression: types of condemned souls → allegorical slaughter → the defaulting believer's fate → recompense mechanism. Headings are descriptive and aid navigation.

---

### Findings

**P1 Warnings:**
1. **[V2] Arabic marker loss**: 66 transliteration markers absent or form-changed in adapted text, including Qur'anic verse markers. This does not affect readability but signals potential data integrity issues in downstream processing (e.g., search, citation linking).
2. **[V6] Non-allowlisted citation**: Cite-14 ("Exegetical tradition") lacks specific author/work attribution and does not appear on the approved citations list. Recommend reassignment to a named high-authority source or removal.

**No P0 (critical) errors detected.**

---

### Verdict rationale

WARN assigned because the adapted chapter demonstrates strong prose quality, faithful theological content, and generally sound citation practice, but two systematic issues—Arabic marker degradation and one unverified citation—require remediation before publication.
# KAHSKOLE Challenger Report
*Generated: 2026-05-25T10:07:51.618565+00:00 | Model: claude-haiku-4-5-20251001*

## Deterministic Validator
Validator: 0 P0 errors, 2 P1 warnings
  ⚠ [V2] 5 ⟪ar:…⟫ marker(s) absent or form-changed in adapted
      ⟪ar:حضرت خدیجہ⟫ ⟪ar:‏فَسَبِّحْ بِحَمْدِ رَبِّكَ وَكُن مِّنَ ٱلسَّجِدِينَ ‎⟫ ⟪ar:‏ذَلِكَ ٱلْكِتَبُ لَا رَيْبَ ۛ فِيهِ ۛ هُدًۭى لِّلْمُتَّقِينَ ‎⟫ ⟪ar:‏ٱلَّذِينَ يُؤْمِنُونَ بِٱلْغَيْبِ وَيُقِيمُونَ ٱلصَّلَوٰةَ وَمِمَّا رَزَقْنَهُمْ يُنفِقُونَ ‎⟫ ⟪ar:‏وَٱعْبُدْ رَبَّكَ حَتَّىٰ يَأْتِيَكَ ٱلْيَقِينُ ‎⟫
  ⚠ [V6] 11 citation(s) reference non-allowlisted authors
      cite-1: Ismaili traditionist source
      cite-2: Ismaili traditionist source
      cite-3: Ismaili traditionist source

# Challenge Report — Articles related to Wilayat

**Date:** 2026-05-25  
**Verdict:** WARN

---

### Checks

- **Prose quality**: The adapted English is scholarly, well-structured, and readable. Transliterations are consistent (ʿAhd Sharīf Nāma, dāʿī, taqwā, etc.). The rhetorical repetition ("Affirm this with conviction!") effectively mirrors the oath-letter's performative register. No evidence of raw machine translation.

- **Terminology**: Key Ismaili terms are correctly transliterated with first-occurrence glosses: ʿahd (covenant), dāʿī (Summoner), zakāh (alms-tax), daʿwa (summons), taqwā (piety). Glossing is appropriate and consistent.

- **Faithfulness**: The adapted content appears to faithfully convey the doctrinal emphasis on covenant obedience, the role of the Imam and his deputies, the five pillars, and ethical conduct. The theological warnings against covenant-breaking are preserved. No obvious omissions detected in the sample; structure and doctrinal tone align with source intent.

- **Citations**: All three citations reference "Ismaili traditionist source" rather than specific named authors. While high-confidence and training-grounded, they do not meet the allowlist requirement for named-author citations. This is a P1 compliance issue, not a faithfulness problem.

- **Section structure**: Two section headings are present and meaningful. First section ("The Noble Oath-Letter") is appropriate for a covenant text; second section ("ʿAbdullāh ibn Masʿūd's Message") clearly introduces a different source. Headings follow Ismaili scholarly convention.

---

### Findings

**P1 (Warning):**
- **V2 Arabic markers**: 5 source-language markers (ʿArabic script quotations and proper names) are missing or form-changed in the adapted text. Examples include "Ḥaḍrat Khādija" and Qur'ānic verses (e.g., *Fa-sabbih bi-ḥamdi rabbika*). While transliterations are provided, the original Arabic script references should be preserved in annotation markers for scholarly citation traceability.
- **V6 Citation authority**: 11 citations reference "Ismaili traditionist source" rather than named authors on an institutional allowlist. High confidence and training-grounding are noted, but the citations do not meet formal attribution standards for KASHKOLE peer review.

---

### Verdict rationale

The adapted chapter demonstrates strong prose quality, correct terminology, faithful doctrinal content, and clear structure, but fails to fully preserve Arabic-script markers and relies on non-allowlisted author attribution across multiple citations, warranting a WARN pending remediation of these compliance issues.
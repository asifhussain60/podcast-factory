"""Phase 0probe — pre-generation Arabic pronunciation probe.

Generates one small NotebookLM bundle that forces the highest-risk Arabic terms
to be spoken, so mispronunciations are caught and corrected BEFORE the whole
book is committed to per-chapter generation. Corrections feed the cross-book
pronunciation library (``knowledge/pronunciation_ledger.py``).
"""

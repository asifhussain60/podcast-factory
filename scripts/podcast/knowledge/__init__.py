"""Knowledge-extraction package — phase 0h `knowledge-extract`.

Three pieces:
- `extractor`   — pulls atoms from audit-vetted chapters
- `librarian`   — dedupes scratch atoms into the canonical library
- `augmenter`   — query helper for injecting prior atoms into future-book prompts

Authority:
- Spec: `_workspace/plan/intelligence-pipeline-wave1-spec.md`
- Agent: `.github/agents/podcast-librarian.agent.md`
- Library: `content/knowledge-base/`
- Visual overview: `_workspace/plan/view/intelligence-pipeline.html`

Status (2026-05-25): scaffolded, awaiting Wave 1 implementation. All modules raise
`NotImplementedError` until the implementer wires them up per the spec.
"""

"""Prompt builder for the translation-edition compose.

Extracted from ``_translation_edition.py`` (DR-005 line-count gate, 2026-07-20).

That module's docstring previously recorded a decision to keep this prompt beside
its orchestration, per the Spec-2 precedent. That precedent covers prompts bound
to their caller by free variables — this one is not: ``_compose_prompt`` is a pure
function of its arguments, so the coupling the precedent protects does not exist
here. The module also sat one line under the gate, meaning ANY change to it would
have tripped the same failure; splitting now is what stops the next author paying
for it.
"""

from __future__ import annotations

from _arabic_coverage import arabic_ground_truth_block
from _narrative import ARABIC_DIRECTIVE, frame_prompt_directive


def _compose_prompt(
    title: str,
    body: str,
    previous_tail: str,
    *,
    arabic_src: str = "",
    quran_anchor: str = "",
    frame: str = "",
    narrator: str = "",
) -> str:
    directives = frame_prompt_directive(frame, narrator) + ARABIC_DIRECTIVE if frame else ""
    continuity = (
        "\nContinuity note: the previous chapter ended with this thought. "
        "Open naturally without repeating it:\n"
        f"{previous_tail}\n"
        if previous_tail
        else ""
    )
    return f"""You are preparing a faithful English translation edition of a non-English Islamic teaching text.

Write one polished chapter titled "{title}" from the source passage below.

Core rule: this is LLM-enriched translation, not augmentation. Enrichment here means clear articulation,
clean paragraphing, careful denoising, and readable English. It does not mean adding outside facts,
new examples, modern analogies, doctrine from other books, or explanatory material not present in the source.

Preserve meaning:
- Preserve every teaching, argument, example, named person, citation, Quran verse, hadith, quote, and Arabic term present in the source.
- Preserve Arabic script when it appears in the source. Do not romanize it away.
- If a Quran verse, hadith, poem, or quoted saying appears, keep it visibly quoted and keep the attribution present in the source.
- Do not break a continuous quotation with a new attribution tag (e.g. "..., he said, ...") that the source does not already have there. A long quoted passage stays one unbroken quotation unless the source itself interrupts it — inserting a tag mid-quote re-points everything after it and can misattribute the argument.
- Do not invent canonical Arabic from memory. If the source gives Arabic, preserve it; if the source gives only a translation, translate/polish only that.
- Use the original-language source block only as preservation evidence, not as permission to add new side material.
- Keep salutations compact. Do not repeatedly spell out long English honorifics. In English prose the only permitted honorifics are the Arabic runs عليهم السلام, ع, and رض. Write each one inside ONE pair of parentheses — `Ali (ع) said` — and never inside two: `((ع))` is wrong. The parentheses are the sentence's, not part of the honorific, so do not add a pair around a run that already has one, and do not put an English lead-in such as "may" inside the brackets beside the Arabic.
{quran_anchor}{arabic_ground_truth_block(arabic_src)}

Denoise:
- Remove or compress historical side information, bibliographic apparatus, editorial notes, damaged-manuscript notes, chain-of-publication details, translator/editor commentary, and background digressions unless they directly teach the point of the chapter.
- Keep the author's teaching as the spine.

Style:
- Clear, dignified English.
- No podcast language.
- No episode references.
- No bullet-list study guide unless the source itself is enumerating points.
- No em dashes.
- Render each technical term the SAME way on every occurrence; do not vary a term for freshness.
{directives}{continuity}
Output only the chapter prose. No preamble, no code fences, no notes.

SOURCE PASSAGE
{body}"""

> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. ["Site Reliability Engineering."](https://landing.google.com/sre/book/chapters/postmortem.html).

# A faithful opening was reverted as if the model had invented it (RCA-008)

### Date

2026-08-01 (detected 02:30 PM EST; the defect dates to the introduction of the
narrative-opening gate on 2026-07-19)

### Authors

Claude (investigation + fix), reviewed by Asif

### Status

RESOLVED 2026-08-01. Root cause fixed, pinned by four tests, and the affected
chapter re-articulated. Open corrective action: AI-3.

### Summary

The articulation pass reverted chapter 2 of *Ayyuhal Walad* — "The Striving That
Mercy Meets" — because its opening announced the act of narration: "Let me tell
you of a man among the Children of Israel."

Al-Ghazali wrote that sentence. It is in the source, and it is in the faithful
base prose the pass was adapting. The model had preserved it, which is exactly
what fidelity demands, and the gate reverted the chapter as though the model had
invented it. The paid articulation work was discarded, the chapter shipped in
un-articulated prose while its nine siblings were articulated, and the
consistency invariant that guards the reading edition went permanently red.

### Impact

One chapter of a finished reading edition shipped noticeably stiffer than the
book around it — the surviving base prose reads "be firmly convinced of this:
without effort you will not find its reward" where the discarded articulation
read "hold firmly to this conviction: you will not find the reward without the
effort that earns it."

One chapter's worth of `claude -p` articulation was paid for and thrown away
(flat-rate Max; no Azure or Gemini spend). One test — `test_articulation_state_is_intact`
— was left failing on `develop`, and blocked a 66-commit push until the post-merge
audit found it.

The class-level impact is larger than the instance: **any book whose source opens
a chapter by announcing its own telling could never pass articulation**, and the
failure mode is silent. The pass reports a revert, not an error.

### Root Causes

**1. The gate was the only non-differential check in a differential gate set.**
`revoice_gates` compares a re-voice against its base on every other axis:
abridgement measures against the base's word count, `teaching_loss_findings` takes
both texts, dropped Arabic runs compares run counts, new doctrinal P0s subtract
the base's own signatures, and the narrative-frame guards take both. Only
`narrative_opening_findings` received the rewritten text alone. It could therefore
only ask "does this announce its telling?" when the question that matters is "did
this *start* announcing its telling?"

**2. The gate was designed from one direction of evidence.** It was added on
2026-07-19 against six live instances in *The Master and the Disciple* where the
model had genuinely invented the announcement. Every test written for it supplied
a single string. Nothing in its design or its tests considered a source that
already opened that way, so the asymmetry was invisible to the test suite that
was meant to pin the gate's behaviour.

**3. The invariant that caught it was unsatisfiable by the sanctioned repair.**
`test_articulation_state_is_intact` asserts `reverted == 0`. The on-demand repair
tool, `rearticulate_chapter.py`, records into `_system/composer-edits.json` and
never writes `book-fluency-report.json` — so the count it asserts on cannot be
cleared by the tool built to fix the thing it is asserting about. The only path
to green was a full pass re-run, which re-rolls the same gate. A correctly
functioning system could pin that test red indefinitely.

**4. CI could not see the commit that broke it.** The `podcast-e2e` workflow's
path filters covered `scripts/**`, `tests/**`, `pytest.ini` and `requirements.txt`
— but several tests read `content/**` as fixture data and assert invariants over
it. `c7903af` was content-only. The broken invariant therefore arrived on the
branch with no gate firing anywhere: not the pre-commit hook (which runs
doc-links and the repo-surgeon probe, not pytest), and not the workflow.

### Trigger

The 2026-08-01 post-merge audit before pushing 66 commits — the standing
`repo-surgeon --scope podcast` sweep — ran the contract's `verify:` list and
surfaced the failing test.

### Resolution

`narrative_opening_findings` now takes an optional `base_text` and reports the
finding only when the re-voice *introduced* the announcement. `base_text=None`
preserves the older single-argument contract for tests that exercise the
phrase-matching in isolation. `revoice_gates` passes the base through, bringing
this gate into line with every one of its neighbours.

Four tests pin the corrected behaviour, including the live case verbatim and —
importantly — the inverse, so the differential cannot decay into a blanket
amnesty: a plain base plus an announcing re-voice is still a finding.

The affected chapter was re-articulated with a targeted single-section pass
(`only=[3]`). It adapted cleanly with no gates fired. All 1,069 Arabic runs
survived, word count moved 13,706 → 13,708, no heading changed, and the diff is
confined to that chapter's line range. The articulation report now reads 10
adapted / 0 reverted.

The workflow's path filters gained `content/**`, closing root cause 4.

### Detection

The post-merge audit — the last gate before a push, and the only one that ran
pytest against this change. That it worked is the good news; that it was the
*only* thing standing between a broken invariant and `origin/develop` is root
cause 4.

Worth naming: the audit's own first reading was that the reverted chapter was
either a content problem needing re-articulation or an over-strict test needing
relaxation. Both were wrong, and both would have left the underlying gate defect
in place — the second would have actively enshrined it. Reading the base prose
next to the gate's finding text is what showed the announcement was the author's.

### Action Items

| # | Action | Type | Owner | Status |
|---|---|---|---|---|
| AI-1 | Make `narrative_opening_findings` differential; wire the base through `revoice_gates` | fix | Claude | DONE |
| AI-2 | Pin both directions with tests, including the live case and the inverse | prevent | Claude | DONE |
| AI-3 | Audit the remaining gates in `_book_voice` / `_narrative` for other non-differential checks | prevent | Claude | DONE (audit) — see below. One correctly non-differential, one genuine candidate escalated as AI-6 |
| AI-6 | Decide whether `narrative_person_findings` should consult the base | prevent | Asif + Claude | OPEN — spawned as a separate task; it is a design decision on a LOCKED rule, not an audit fix |
| AI-4 | Add `content/**` to the e2e workflow path filters | prevent | Claude | DONE |
| AI-5 | Re-articulate the affected chapter and regenerate the report | fix | Claude | DONE |

#### AI-3 result: the sweep for sibling defects

Two checks in the gate modules still judge output without consulting input.

`leaked_marker_findings` is **correctly** non-differential. It fires on a
surviving `===ARTICULATION-NOTES===` marker, which the base can never contain —
the marker is produced by the pass itself. There is no base reading that would
make it a false positive.

`narrative_person_findings(text, frame, ...)` is a **genuine candidate for the
same defect**. It flags an attribution window whose grammatical person
contradicts the book's declared frame, judging the candidate alone. If a source
contradicts its own declared frame in a single paragraph — a `transmitted_report`
book carrying one first-person attribution — the model preserving that paragraph
is flagged and the window reverted, which is precisely the failure this RCA
documents.

It is deliberately **not** fixed here. The narrative frame is a LOCKED rule with
a docs-sweep obligation attached (`framework.md`, `SKILL.md`, the `book-challenger`
spec), and making it differential would weaken a deliberate enforcement rather
than correct an oversight — a source that contradicts its own declared frame may
mean the *declaration* is wrong. That is Asif's call, not an audit's. Escalated
as AI-6.

### Lessons Learned

#### What went well

The revert was safe. The gate's contract — a failed window reverts to its base —
meant the worst outcome was un-articulated but *faithful* prose. No text was
corrupted, nothing was lost, and the book remained publishable throughout.

`merge_records` made the targeted re-run honest: running one section marks the
other nine `skipped`, and carrying the prior run's records forward is what let a
single-chapter fix produce a truthful whole-book report instead of "0 adapted, 9
skipped."

The diagnosis was verified against the actual prose rather than accepted from the
gate's own message. The gate's finding quoted the *candidate's* opening, which
looks damning in isolation; only reading the base beside it showed both texts
opened the same way.

#### What went wrong

A gate meant to protect fidelity was itself unfaithful — it punished the model
for preserving the author's words. That is the most expensive kind of gate defect
because its failures look like successes: a revert reads as the system working.

The invariant guarding this could not be satisfied by the tool built to repair
what it guards. A test that can only be cleared by an expensive, nondeterministic
re-run is a test that will eventually be relaxed for the wrong reason.

#### Where we got lucky

The affected book was *Ayyuhal Walad*, whose chapter 2 opens with a story. Had
the same source construction appeared in a book already published to the library,
the un-articulated chapter would have shipped to a reader rather than to a test.

The push was blocked by an unrelated standing rule. Without the mandatory
post-merge audit, 66 commits including a red invariant would have gone to
`origin/develop`, where the workflow would have fired only incidentally — because
unrelated `scripts/**` changes happened to be in the same range.

### Timeline

All times EST.

| Time | Event |
|---|---|
| 07-19 | The narrative-opening gate is added against six real instances of model-invented announcements. Every test supplies a single string |
| 07-31 06:19 PM | `134b544` — the articulate style becomes the Islamic default |
| 08-01 07:00 AM | `c7903af` — the *Ayyuhal Walad* translation edition is committed. The articulation report arrives already reading `reverted: 1`. Content-only: no gate fires |
| 08-01 02:30 PM | Post-merge audit runs the contract's verify list; `test_articulation_state_is_intact` fails |
| 08-01 02:45 PM | Base prose read beside the gate's finding — both openings are al-Ghazali's. The gate, not the content, is the defect |
| 08-01 02:55 PM | Gate made differential; four tests added; all 21 gate tests green |
| 08-01 03:05 PM | Chapter re-articulated (`only=[3]`), adapts with no gates. Report: 10 adapted / 0 reverted |

### Supporting information

- The gate: [scripts/podcast/_book_voice.py](../../scripts/podcast/_book_voice.py) — `narrative_opening_findings`, `revoice_gates`
- The pins: [scripts/podcast/tests/test_book_voice.py](../../scripts/podcast/tests/test_book_voice.py)
- The invariant: [scripts/podcast/tests/test_compose_lanes_distinct.py](../../scripts/podcast/tests/test_compose_lanes_distinct.py) — `test_articulation_state_is_intact`
- The report: `content/Islamic/ayyuhal-walad/_system/book-fluency-report.json`
- Related: [RCA-001](2026-07-22-composer-snapshots-froze-unarticulated-prose.md) — the previous incident in which a chapter shipped un-articulated

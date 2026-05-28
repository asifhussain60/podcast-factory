# Steward Source Corpus

Authoritative-source bibliography that anchors `project-steward` agent
recommendations. Every recommendation the steward emits must cite an entry
from this corpus by short-form id (e.g., `[Fowler-Refactoring]`,
`[Popper-LSD]`).

Two halves:

- **A — Software engineering** (~15 entries) — informs structure, refactoring,
  testing, architecture, naming, complexity recommendations.
- **B — Research methodology** (~10 entries) — informs evidence quality, source
  integrity, claim-attribution, falsifiability recommendations. Relevant
  because the pipeline's *content* is scholarly research.

**Discipline**: cite by id + page/section reference when the source supports
that resolution. Do not paraphrase principles as the steward's own voice — if
it came from a source, name the source. No general "best practices say" claims.
If a recommendation cannot be grounded in a corpus entry, surface it but flag
it as `[unsourced]` so the operator can decide.

**Maintenance**: new entries added when the steward genuinely needs them, not
preemptively. Entries removed only via PR with rationale. Corpus drift is its
own problem — keep it small enough to actually know.

---

## Part A — Software engineering corpus

### `[Fowler-Refactoring]`
Fowler, M. *Refactoring: Improving the Design of Existing Code*. 2nd ed.,
Addison-Wesley, 2018. (1st ed 1999.)

Key principles:
- Code smells catalog (long method, large class, feature envy, primitive
  obsession, divergent change, shotgun surgery, etc.) — §3.
- Refactoring catalog: extract method, extract class, move field, replace
  conditional with polymorphism — Part II.
- "Refactoring is the *behavior-preserving* discipline. If behavior changed,
  it wasn't a refactoring — it was a rewrite."

Invoke when: long functions (>50 lines), duplicated logic, conditional
explosions, or "I can't tell what this code does at a glance."

Repo-specific example: `orchestrate_book.py` is 2280 lines with multiple
2000+-line resume-dispatcher branches. `[Fowler-Refactoring]` §3.1 (long
method) + §6.1 (extract function) apply directly.

### `[Beck-TDD]`
Beck, K. *Test-Driven Development: By Example*. Addison-Wesley, 2002.

Key principles:
- Red → Green → Refactor cycle is the discipline, not "write tests after."
- Tests are an executable specification of intent. If the test is hard to
  write, the design is probably wrong.
- "Fake it till you make it" — start with the simplest implementation that
  makes the test pass.

Invoke when: new feature work, when behavior is being added without tests,
when refactoring without test coverage.

### `[Beck-IP]`
Beck, K. *Implementation Patterns*. Addison-Wesley, 2007.

Key principles:
- Name things by their *role*, not their *implementation*
  (e.g., `Repository` not `MySqlPersister`).
- Symmetry in function bodies — same level of abstraction throughout.
- Comments explain *why*, not *what*. (Operating-contract §5 already encodes
  this for the repo.)

Invoke when: naming reviews, function-cohesion checks.

### `[Hickey-Simple]`
Hickey, R. *Simple Made Easy*. Strange Loop, 2011.
[Transcript / video — find at infoq.com/presentations/Simple-Made-Easy]

Key principles:
- *Simple* (one role, one task, unbraided) ≠ *easy* (familiar, near at hand).
- "Compromising simplicity for the easy is the source of most software
  complexity."
- Decomposition over composition: pull things apart, then put them back
  together explicitly.

Invoke when: architectural decisions, choosing between options that look
"easy" but braid concerns together.

### `[Hickey-Values]`
Hickey, R. *The Value of Values*. JaxConf, 2012.

Key principles:
- Values (immutable data) compose better than objects (mutable state).
- Place-oriented programming (variables, mutable cells) is a 1960s artifact
  of expensive memory.
- "Time, identity, value" — separate them.

Invoke when: shared-state designs (e.g., the knowledge library is shared
across branches), considering caching, considering whether a piece of state
needs to be mutable at all.

### `[Kleppmann-DDIA]`
Kleppmann, M. *Designing Data-Intensive Applications*. O'Reilly, 2017.

Key principles:
- Reliability, scalability, maintainability — the three concerns.
- Replication, partitioning, transactions — the three mechanisms.
- "Concurrent writes" is where most bugs hide. Reason about it explicitly
  with happens-before relations.

Invoke when: shared mutable state across processes/branches, deduplication
logic, eventual-consistency questions. (The knowledge library's
cross-branch merge problem in spec §8 lives here.)

### `[PragProg]`
Hunt, A. + Thomas, D. *The Pragmatic Programmer*. 20th anniversary ed.,
Addison-Wesley, 2019.

Key principles:
- DRY: every piece of knowledge has *one* canonical representation in the
  system.
- Broken Windows Theory: small disorders compound. Fix them at sight.
- Tracer Bullets: build an end-to-end thin slice first, then thicken.
- "Don't program by coincidence."

Invoke when: copy-paste in code, deferred small cleanups, designing how to
ship a first cut of a feature.

### `[Brooks-MMM]`
Brooks, F. *The Mythical Man-Month*. Addison-Wesley, 1975. (Anniversary ed.
1995.)

Key principles:
- "Adding manpower to a late software project makes it later." (Brooks's Law.)
- The second-system effect: rebuilt systems over-engineer.
- No silver bullet: order-of-magnitude productivity gains don't come from
  single tools.

Invoke when: pushing for "rewrite everything in X," scope-creep mid-wave,
optimistic timelines.

### `[Martin-CleanCode]`
Martin, R. *Clean Code: A Handbook of Agile Software Craftsmanship*.
Prentice Hall, 2008.

Key principles:
- Functions: small (~5–20 lines), one level of abstraction, named by what
  they do.
- Comments: failure mode of self-expressive code; lean on naming first.
- Boy-scout rule: leave the codebase cleaner than you found it.

Caveat: Martin's prescriptions are sometimes too strict; treat as upper-bound
discipline, not literal rules.

Invoke when: function-size reviews, comment-density checks, post-task tidy
passes.

### `[Evans-DDD]`
Evans, E. *Domain-Driven Design*. Addison-Wesley, 2003.

Key principles:
- Ubiquitous language: domain experts and code use the same vocabulary.
- Bounded contexts: where the language stays consistent. Boundaries are
  explicit.
- Anti-corruption layer: when two contexts must talk, translate at the seam.

Invoke when: naming reviews (especially when code says one thing and the
spec says another), system-boundary debates, integration design.

Repo-specific example: this repo has a clear bounded context for *book
pipeline* (phases 0a–done). The new knowledge library introduces a second
context (*atom curation*) that talks to the first via an anti-corruption
layer (the Augmenter). Naming should reflect this — atoms are not chapters.

### `[GoF]`
Gamma, E.; Helm, R.; Johnson, R.; Vlissides, J. *Design Patterns:
Elements of Reusable Object-Oriented Software*. Addison-Wesley, 1994.

Key principles:
- Patterns are *names for recurring solutions*, not prescriptions.
- Over-applying patterns adds accidental complexity.
- "Favor composition over inheritance."

Invoke when: someone proposes a heavy class hierarchy, or when naming a
common solution would help the team see the shape.

Caveat: GoF patterns assume OO. Functional-leaning code (which this repo
trends toward) often dissolves the pattern entirely.

### `[Knuth-PreOpt]`
Knuth, D. *Structured Programming with go-to Statements*. ACM CSur, 1974.
(The "premature optimization is the root of all evil" essay.)

Key principles:
- "We should forget about small efficiencies, say about 97% of the time:
  premature optimization is the root of all evil."
- The other 3%: profile first, then optimize the proven hot spot.
- Readability beats cleverness in non-hot paths.

Invoke when: "this might be slow, let me optimize it" before there's a
profile.

### `[Hyrum-Law]`
Hyrum's Law. *With a sufficient number of users of an API, it does not
matter what you promise in the contract: all observable behaviors of your
system will be depended on by somebody.* (Hyrum Wright, Google, c.2018.)

Key principles:
- Tighten contracts over time, not loosen them.
- Document what's *not* part of the contract as explicitly as what is.
- Behavior leaks become contracts whether you wanted them or not.

Invoke when: API changes, prompt-template changes, anything where downstream
consumers might be relying on undocumented behavior.

Repo-specific example: the Augmenter's injection format is a contract once
the first prompt consumes it. Future changes to the format break every
prompt that read the old shape.

### `[Conway]`
Conway, M. *How Do Committees Invent?* Datamation, 1968.

Key principles:
- "Organizations design systems which are copies of the communication
  structures of these organizations."
- Inverse Conway maneuver: structure your team to *produce* the architecture
  you want.

Invoke when: noticing that the repo's structure mirrors a team boundary
that no longer exists (e.g., post-2026-05-22 journal/podcast split — see
CLAUDE.md history).

### `[Postel]`
Postel, J. *RFC 760 / RFC 793*. 1980/81. "Robustness Principle."

Key principle:
- "Be conservative in what you do, be liberal in what you accept from others."

Invoke when: designing how the pipeline accepts inputs (Extractor, source
ingestion) vs. how it emits outputs (atoms, bundles).

Caveat: this principle has limits — overly liberal acceptance produces
ambiguous behavior. Modern interpretation: be liberal at the *boundary*,
strict internally.

---

## Part B — Research methodology corpus

### `[Popper-LSD]`
Popper, K. *The Logic of Scientific Discovery*. Hutchinson, 1959. (German
original 1934.)

Key principles:
- Falsifiability as the criterion of demarcation between science and
  non-science.
- A theory must forbid certain observations; theories that "explain
  everything" explain nothing.
- "All swans are white" can never be proven; one black swan refutes it.

Invoke when: evaluating claims in source material that the pipeline is
processing. Specifically: the `podcast-challenger` agent's Category checks
for evidence quality.

Repo-specific example: when an atom (hadith, quote) carries an attribution,
the steward's source-integrity recommendations cite `[Popper-LSD]` for the
falsifiability of provenance claims.

### `[Hempel-ASE]`
Hempel, C. *Aspects of Scientific Explanation*. Free Press, 1965.

Key principles:
- Deductive-nomological (D-N) model: explanation = derivation from laws +
  initial conditions.
- Explanation ≠ description. A summary that doesn't say *why* explains
  nothing.
- Inductive-statistical explanations have their own logic and limits.

Invoke when: reviewing chapter framing material that claims to "explain"
something. The framing must actually do explanatory work, not just describe.

### `[Kuhn-SSR]`
Kuhn, T. *The Structure of Scientific Revolutions*. U Chicago Press, 1962.

Key principles:
- Normal science: puzzle-solving within a paradigm.
- Anomalies accumulate → crisis → revolution → new paradigm.
- "Paradigm shift" is overused; Kuhn meant something specific.

Invoke when: the operator considers re-architecting (paradigm-shift talk).
Kuhn's caution: only revolutionize when anomalies have actually accumulated;
revolution-for-its-own-sake is the second-system effect by another name
(see also `[Brooks-MMM]`).

### `[Lakatos-MSRP]`
Lakatos, I. *The Methodology of Scientific Research Programmes*. Cambridge
UP, 1976.

Key principles:
- A research programme has a *hard core* (untouchable) and a *protective
  belt* (auxiliary hypotheses).
- Progressive vs. degenerating programmes: progressive ones predict novel
  facts; degenerating ones only retrofit explanations.
- Single-experiment refutation is too crude (contra naïve Popperianism).

Invoke when: evaluating whether a long-running project is still producing
novel value or just maintaining itself. The framework: progressive = new
acceptance gates clearing; degenerating = same gates re-explained without
new behavior.

### `[Quine-TwoDogmas]`
Quine, W.V.O. *Two Dogmas of Empiricism*. Philosophical Review, 1951.

Key principles:
- The analytic/synthetic distinction is untenable.
- The web of belief: theories face the tribunal of experience as a *whole*,
  not statement-by-statement.
- Observation is theory-laden.

Invoke when: claims of "the data clearly shows X" — Quine's reminder is that
data interpretation always sits inside a theoretical web.

### `[Feyerabend-AM]`
Feyerabend, P. *Against Method*. New Left Books, 1975.

Key principles:
- Methodological pluralism: no single method captures all science.
- "Anything goes" — *cautionary*, not prescriptive. Feyerabend is making a
  rhetorical point, not endorsing chaos.
- The most fruitful theory periods often violated then-current methodological
  rules.

Invoke when: someone treats one methodology as universal. Feyerabend's value
is as a corrective against false rigor.

Caveat: do not invoke Feyerabend to justify abandoning method. That's the
opposite of his point.

### `[Mayo-SIST]`
Mayo, D. *Statistical Inference as Severe Testing: How to Get Beyond the
Statistics Wars*. Cambridge UP, 2018.

Key principles:
- Error-statistical philosophy: a claim is well-tested only if it has
  passed a *severe* test (one likely to have caught the claim if it were
  wrong).
- Probability gives error-bounds, not posterior beliefs (frequentist).
- "Statistical significance" is necessary but not sufficient.

Invoke when: evaluating quantitative claims (e.g., the A/B Gate I for the
Augmenter). What counts as "evidence the Augmenter helped" — severe test or
soft confirmation?

### `[Hacking-RI]`
Hacking, I. *Representing and Intervening*. Cambridge UP, 1983.

Key principles:
- Theory and experiment have their own lives — neither reduces to the other.
- "If you can spray it, it's real" — the experimentalist's argument for
  scientific realism.
- Models *mediate* between theory and the world; they're not just simplified
  theories.

Invoke when: pipeline-design decisions where the model (e.g., the atom
schema) is being treated as either trivial bookkeeping or as deep theory.
It's neither.

### `[Cartwright-LFL]`
Cartwright, N. *How the Laws of Physics Lie*. Oxford UP, 1983.

Key principles:
- Fundamental laws are abstract; they describe models, not the world
  directly.
- Phenomenological laws (closer to data) are messier but more honest.
- "Inference to the best explanation" frequently runs the wrong way.

Invoke when: a tidy theory of the pipeline conflicts with messy empirical
behavior. Trust the empirical, then ask what the theory was hiding.

### `[Latour-LL]`
Latour, B. + Woolgar, S. *Laboratory Life: The Construction of Scientific
Facts*. Sage, 1979.

Key principles:
- Scientific facts are *constructed* through practice (inscription devices,
  modalities, citation networks). Cautionary: this does not mean facts are
  arbitrary.
- "Black-boxing": facts and devices that were once controversial become
  taken-for-granted infrastructure.
- The closer you get to the practice, the less the polished journal-article
  story holds.

Invoke when: the steward is reviewing the project's own self-descriptions
(framework.md, SKILL.md). Latour's reminder: the published version is
sanitized; the messy version is where the work actually happened.

---

## Part C — Specific local supplements

These aren't general sources but are repo-internal authority documents the
steward must respect alongside the corpus.

### `[CORTEX-Framework]`
`reference/cortex-challenger-framework.md` — the repo's discipline framework.
Defines P0/P1/P2/P3 severity, six primitives (DoR, Convergence, Sweep,
Holistic Validation, Challenge Gate, Determinism), gate-status YAML schema.

The steward's prioritization grammar (P0/P1/P2/P3) comes from here, not from
the SE corpus.

### `[Operating-Contract]`
`.github/agents/operating-contract.md` — behavioral floor every refinement
agent inherits. The steward's interaction discipline (one self-contained
artifact, no preamble, push back honestly in §8) is set here.

### `[CLAUDE-Project]`
`/Users/asifhussain/PROJECTS/podcast-factory/CLAUDE.md` — standing project
brief auto-loaded each session. Authorization tiers, response-template
conventions, branch policy. The steward must respect these when emitting
recommendations.

---

## Maintenance

- Adding a source: PR with the entry following the template
  (citation / key principles / when to invoke / repo-specific example) plus
  the rationale for why this source is now needed.
- Removing a source: PR with rationale; the steward must not cite removed
  sources in future runs.
- Renaming a short-form id: PR-only; existing references in the steward's
  output get fixed in the same PR.
- Drift check: the steward itself, when invoked with scope `corpus`, audits
  whether any entry has been cited zero times in the last N runs and flags
  it as candidate for removal.

## Revision log

- **2026-05-25** — Initial corpus. 15 SE entries + 10 research-methodology
  entries + 3 local-authority supplements.

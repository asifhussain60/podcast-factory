# Enrichment Whitelist — ISL2 / MAS-I

**Override note:** the library-default enrichment pool (Quran / hadith / Imam Ali / Ismaili tradition) does **not apply to this book**. ISL2 is a secular STEM textbook; its enrichment pool is **modern data-science analogies + actuarial-exam context + R/Python ecosystem references**, capped at the existing 60% Invariant-4 ceiling. See [`integration-analysis.md`](integration-analysis.md) §3.3 for the rationale.

This file enumerates the **approved enrichment sources** for ISL2 chapters. The Phase 0e author may draw from anything listed here; anything outside this list requires an explicit operator amendment to this file before insertion.

---

## Tier 1 — the textbook authors' own corpus (highest priority)

Citations from the four ISL2 authors' own work are the gold-standard enrichment for any ISL2 chapter — they preserve "voice continuity" with the source.

| Work | Authors | Year | Relevance |
|---|---|---|---|
| *The Elements of Statistical Learning* (ESL) | Hastie, Tibshirani, Friedman | 2009 (2nd ed.) | The "graduate sibling" of ISL2. Cite when the listener needs the deeper mathematical treatment, or when ISL2 references ESL by name. |
| *Generalized Additive Models* | Hastie, Tibshirani | 1990 | The GAMs origin text. Cite in EP07 for the historical anchor on Ch 7's GAMs section. |
| "Regression shrinkage and selection via the lasso" | Tibshirani | 1996 (JRSS-B) | THE Lasso paper. One of the most-cited statistics papers ever. Cite in EP06 when introducing the L1 penalty. |
| "Bootstrap methods: another look at the jackknife" | Efron | 1979 (Annals of Statistics) | The bootstrap's founding paper. Not an ISL2 author, but Tibshirani is Efron's student. Cite in EP05. |
| *Computer Age Statistical Inference* | Efron, Hastie | 2016 | Modern survey; useful for the historical arc of resampling methods. EP05 anchor. |

## Tier 2 — modern data-science culture (analogies + concrete real-world hooks)

Use sparingly — at most one or two per episode. Each must serve a *specific* concept being introduced.

| Anchor | Where | Why |
|---|---|---|
| **Netflix Prize (2006–2009)** | EP02, EP05 | The canonical modern motivating example: a $1M prize for a 10% improvement in collaborative-filtering RMSE. Illustrates "out-of-sample evaluation" at internet scale. |
| **Spotify Discover Weekly** | EP01, EP02 | Recommendation-as-supervised-learning in a listener's daily life. |
| **FICO credit scoring** | EP04 | Real-world logistic regression at industrial scale. "When your credit score goes up because you opened a new account, you're seeing logistic-regression coefficients adjusted." |
| **Kaggle competitions** | EP05, EP06 | The canonical "k-fold CV on a held-out test set" workflow. Standardized scoring protocols. |
| **The 2008 financial crisis (correlation breakdown)** | EP03 | Multicollinearity and high-leverage points; mortgage-default correlations that were near-zero in normal years approached 1.0 in 2008. |
| **Email spam filters (1990s–2000s)** | EP04 | The original mass-deployment Naive Bayes use case. |
| **COMPAS recidivism / ProPublica 2016** | EP04 | A *cautionary* anchor on classification fairness — illustrates "the model is technically a classifier but its real-world deployment raises questions the math doesn't answer." Use carefully, briefly. |
| **Tesla Autopilot misclassifications** | EP04, EP07 | Edge cases in deployed classifiers. |
| **GPT-style models (large-scale parametric)** | EP02 | Modern frame for "very-many-parameters parametric models." Used as a parametric/non-parametric counterweight; not as endorsement. |
| **GAMs in insurance pricing** | EP07 | The actuarial home turf: claim frequency by age curve is almost always a smooth function fit by a GAM. THE bridge between ISL2 and the MAS-I exam application context. |

## Tier 3 — actuarial-exam context (audience-specific)

The listener is preparing for **MAS-I**. Anchor the material to exam-relevance where it's natural — but do not turn the episode into exam prep.

| Anchor | Where | Why |
|---|---|---|
| **GLMs in MAS-I scope** | EP04 (Ch 4 §4.6) | The chapter's Poisson regression treatment maps directly onto exam-relevant GLM theory. Worth a callout. |
| **Resampling on MAS-I** | EP05 | Bootstrap and CV are exam-testable concepts; the chapter and the syllabus align. |
| **Variable selection on MAS-I** | EP06 | Ridge/LASSO/PCR appear in the syllabus under "model selection." |
| **Non-linear methods on MAS-I** | EP07 | Splines and GAMs appear under "generalized linear and nonlinear modeling." |
| **SOA exam culture** | EP01 (briefly) | Position ISL2 as "the textbook that translates between the SOA's statistics curriculum and modern data-science practice." |

## Tier 4 — R/Python ecosystem references (light touch only — walking listener doesn't need code)

ISL2 is R-first; the labs are R. The listener is *not* going to run code on a walk. Use these references for *recognition*, not *recital*.

| Anchor | Where | Why |
|---|---|---|
| **`lm()` in base R** | EP03 | "The function every R user calls without thinking — `lm(sales ~ TV + radio + newspaper, data=Advertising)`." Recognition only. |
| **`glm(family=poisson)` in R** | EP04 | Same recognition role. |
| **`cv.glmnet()` in R** | EP06 | Tibshirani's own package; the practical handle on Lasso. |
| **`gam()` in mgcv** | EP07 | Simon Wood's package; the workhorse GAM implementation. |
| **scikit-learn equivalents** | (any episode where relevant) | One-line bridge for Python-native listeners. Don't dwell. |

## What is NOT allowed under any tier

- Religious citations of any kind (Quran, hadith, Imam Ali, Sufi tradition, Bible, Torah, any other scripture).
- Political commentary.
- Speculation about ML's societal impact beyond what ISL2 itself references.
- Discussion of specific living individuals beyond the textbook authors and historical figures (Efron, Fisher, Yogi Berra's quote which ISL2 itself uses).
- Modern news anchors more recent than 2023 (this textbook is 2021; framing as if it's current invites listener-confusion about what ISL2 covered vs what came after).

## Cap and audit

- **60% enrichment cap** per chapter (Invariant 4). Counted as enriched chapter words divided by total chapter words. Tracked in [`enrichment-log.md`](enrichment-log.md).
- Every Tier-1 citation MUST carry a bracketed attribution: `[Lasso paper, Tibshirani 1996]`, `[ESL §3.4]`, `[GAMs, Hastie & Tibshirani 1990]`.
- Every Tier-2 anchor carries a year: `[Netflix Prize, 2006–2009]`, `[2008 financial crisis]`.
- Tier-3 and Tier-4 references do not require attribution (general culture), but should be factually correct.
- The challenger's Loop N (numeric/symbolic disambiguation, retargeted) will flag year drift, attribution drift, and any uncited claim.

This whitelist is the authority for Phase 0e on this book. Amendments require an explicit operator commit on the `book/islr-mas-i` branch.

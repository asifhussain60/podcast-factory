# Jargon Glossary — ISL2 / MAS-I

**Purpose:** the ISL2-specific replacement for the Arabic phonetics index. Consumed by Phase 0c in place of `SHARED_ARABIC/03-arabic-english-manifest.md` lookups for this book.

**Two columns of work per term:**
1. **Pronunciation** — TTS respelling in the `R-PRONUNCIATION-IMPERATIVE` form ("Pronounce 'X' as 'X-spelled-out'."). Goes into each customize-prompt's `## Pronunciation` block when the term first appears in the episode.
2. **Listener primer** — one-sentence concept tag that NotebookLM can lean on for context if asked. NOT a definition the hosts must recite; a steering anchor.

The pronunciation-respelling rules from `SHARED_ARABIC/01-tts-pronunciation-key.md` generalize: use hyphenated syllables, CAPS the stressed syllable, drop into TTS as a single word.

---

## Pronunciation table

| Term | TTS respelling | Stressed syllable | First appears |
|---|---|---|---|
| **heteroscedasticity** | HET-er-oh-skuh-DAS-tih-see | DAS | EP03 (Ch 3, §3.3) |
| **homoscedasticity** | HOH-moh-skuh-DAS-tih-see | DAS | EP03 (Ch 3, §3.3) |
| **multicollinearity** | mull-tee-koh-lin-ee-AIR-ih-tee | AIR | EP03 (Ch 3, §3.3) |
| **Akaike (AIC)** | ah-kah-EE-keh | EE | EP06 (Ch 6, §6.1) |
| **Bayesian (BIC)** | BAY-zee-an | BAY | EP04 (Ch 4, §4.4) and EP06 |
| **Mallows's Cp** | MAL-ohz SEE-pee | MAL | EP06 (Ch 6, §6.1) |
| **LASSO** | LASS-oh | LASS | EP06 (Ch 6, §6.2) |
| **ridge regression** | RIDJ ree-GRES-shun | RIDJ | EP06 (Ch 6, §6.2) |
| **eigendecomposition** | EYE-gen-dee-com-poh-ZISH-un | ZISH | EP06 (Ch 6, §6.3) |
| **kurtosis** | kur-TOH-sis | TOH | EP02 (Ch 2, §2.2) |
| **leverage** | LEV-er-ij | LEV | EP03 (Ch 3, §3.3) |
| **asymptotic** | a-simp-TOT-ik | TOT | EP05 (Ch 5, §5.2) |
| **parametric** | pair-ah-MET-rik | MET | EP02 (Ch 2, §2.1) |
| **non-parametric** | NON pair-ah-MET-rik | NON, MET | EP02 (Ch 2, §2.1) |
| **regularization** | REG-yoo-lar-ih-ZAY-shun | REG, ZAY | EP06 (Ch 6, §6.2) |
| **multinomial** | mull-tih-NOH-mee-al | NOH | EP04 (Ch 4, §4.3) |
| **Poisson** | PWAH-sahn | PWAH | EP04 (Ch 4, §4.6) |
| **stochastic** | sto-KAS-tik | KAS | EP05 (Ch 5, §5.2) |
| **smoothing spline** | SMOOTH-ing SPLINE | SMOOTH, SPLINE | EP07 (Ch 7, §7.5) |
| **LOESS** | LOH-ess | LOH | EP07 (Ch 7, §7.6) |
| **K-nearest neighbors / KNN** | KAY NEAR-est NAY-burz | NEAR | EP02 (Ch 2, §2.2) |
| **QDA** | KYOO-dee-AY | AY | EP04 (Ch 4, §4.4) |
| **Naive Bayes** | nai-EEV BAYZ | EEV, BAYZ | EP04 (Ch 4, §4.4) |

The customize-prompt's `## Pronunciation` block per episode is generated from this table, filtered to the terms that actually appear in that chapter.

---

## Concept primers (listener anchors — NOT mandatory recitation)

When the chapter introduces a term for the first time, the framing's discussion-spine should give NotebookLM a one-sentence anchor it can lean on. The hosts should *use* the concept, not lecture it.

- **Bias** — how wrong your model is on average across many training sets.
- **Variance** — how much your model's prediction jumps if you swap in a different training set of the same size.
- **Irreducible error** — the noise floor; the bit you can never explain because the response itself is random given X.
- **Overfitting** — the model has memorized the training noise; test performance crashes.
- **MSE (mean squared error)** — the average squared distance between predicted and actual values. Smaller is better.
- **Training MSE vs Test MSE** — training MSE keeps falling as you add flexibility; test MSE falls then rises (the U-shape).
- **Cross-validation** — split the data into k folds, hold one out, fit on the rest, score on the held-out, repeat for all folds, average.
- **The bootstrap** — resample your dataset *with replacement* and refit; the spread of the refits is your standard-error estimate.
- **Maximum likelihood** — pick the parameters that make the observed data most probable under the model.
- **The logistic function** — the S-shaped curve that squashes any real number into the (0, 1) range; turns a linear predictor into a probability.
- **Bayes' rule** — posterior is prior times likelihood, normalized. The mechanical engine of generative classifiers.
- **L1 penalty (the LASSO's penalty)** — sum of absolute values of coefficients; produces *exact zeros* for irrelevant predictors.
- **L2 penalty (ridge's penalty)** — sum of squared coefficients; shrinks all coefficients toward zero without zeroing any.
- **Knot** — a join-point where a spline switches from one polynomial piece to the next.
- **Effective degrees of freedom** — for a flexible model, the equivalent "number of parameters" it's costing you in complexity terms.
- **Backfitting** — the iterative algorithm GAMs use to fit each smooth function while holding the others fixed, looping until convergence.

These primers stay in the framing layer; the chapter text itself uses the terms in their natural ISL2 phrasing.

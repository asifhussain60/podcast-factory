# Chapter Design Rationale — ISL2 (MAS-I Subset)

**Purpose**: ground the Phase 0d segmentation decision in the operator's exam-scope constraints BEFORE the orchestrator runs. Per the orchestrator's Phase 0f gate, length-tier and chapter list are the two human-reviewed items; this file pre-stages both.

**Audience model**: actuarial student who has passed Exams P (Probability) and FM (Financial Mathematics), now preparing for **MAS-I** (Modern Actuarial Statistics I). They have strong probability/calculus foundations and basic regression exposure, but minimal ML vocabulary. **Listening mode**: casual walk — no R recitation, no formulas-solved-aloud, no "pause and try this".

**Length tier**: **Default Deep Dive (~12–15 min per episode)**. Total program ~90 min, fits a one-hour-thirty walk or three 30-min sessions. Brief is too thin for the conceptual density; Longer/Extended risks the walking listener tuning out.

**Host dynamic (recommendation)**: `curious_mind + patient_teacher` from the canonical pair list — same as `the-master-and-the-disciple`. The patient_teacher slot maps naturally to "senior actuary who got the credentials a decade ago", and curious_mind maps to "MAS-I candidate working through the material". If a `walking_companion + senior_actuary` pair is later added to `two-host-framing.md`, that's the better fit; the existing pair is a safe fallback that doesn't require a handbook edit.

**Total episodes**: **7** (strict 1:1 chapter ↔ episode per Invariant 1; the source's 7 in-scope chapters map cleanly to 7 episodes).

---

## Per-chapter plan

### EP01 — `ch01-introduction.txt` — *What Statistical Learning Actually Is*

- **MAS-I scope:** full Chapter 1 (no exclusions).
- **Source pages (PDF):** 18–30 (printed pp 1–13).
- **Source size (raw):** ~36 KB / 639 lines.
- **Beats:**
  1. The three motivating examples — Wage, Smarket, NCI60 (don't just name them; use them to land the supervised/unsupervised split intuitively).
  2. Brief history — least squares → LDA (1936) → logistic → GLMs → trees → neural nets → SVMs. Frame as: "you're inheriting two centuries of statistical ideas; ML is just the latest layer."
  3. Premises for the book — accessibility, R focus, intuition-first.
- **Analogies/enrichment hooks:** Spotify/Netflix as recommendation-as-supervised; weather forecasting as regression; spam detection as classification; PCA-the-cell-line-clusters as "imagine you have 6,830 features and need to see them in 2D".
- **Quantitative claims to preserve verbatim:** "approximately 60% [stock-market direction]" (p4); "6,830 gene expression measurements for each of 64 cancer cell lines" (p4); LDA dated 1936.
- **Walking-listen guardrail:** zero formulas. Pure intuition episode.

### EP02 — `ch02-statistical-learning.txt` — *Estimating f, Bias, and Variance*

- **MAS-I scope:** Chapter 2 **excluding §2.2.3** ("The Classification Setting"). Keep §2.1 (all of it), §2.2.1 (Measuring Quality of Fit), §2.2.2 (Bias–Variance Trade-Off). **Drop §2.2.3 entirely.** R Lab §2.3 is referenced but not narrated.
- **Source pages (PDF):** 26–55 approximately (printed pp 15–41). Skip pp 37–41 (printed) which contain §2.2.3.
- **Source size (raw):** ~130 KB / 2431 lines (will shrink after §2.2.3 removal — author the chapter file to omit that section explicitly).
- **Beats:**
  1. The framework: Y = f(X) + ε. "Statistical learning is a set of approaches for estimating f."
  2. Why estimate f — prediction vs inference. The two motivations are distinct; the choice cascades.
  3. Parametric vs non-parametric. Linear regression is the parametric ur-example; KNN the non-parametric ur-example.
  4. The accuracy–interpretability frontier — the figure showing which methods sit where on flexibility/interpretability.
  5. Supervised vs unsupervised vs semi-supervised.
  6. **Measuring quality of fit — MSE** (training vs test; the U-shaped test-MSE curve is THE picture of the chapter).
  7. **The bias–variance decomposition** — Var(ε) is irreducible; bias² + variance is the budget. Drive the intuition: rigid models are biased; flexible models are noisy.
- **Analogies/enrichment hooks:** the bias–variance trade-off as "the dartboard": tight cluster off-center (high bias, low variance) vs scattered around bullseye (low bias, high variance). Polynomial degree as the "knob" listeners can imagine turning. Test-set MSE as "the prediction-tournament rule".
- **Quantitative claims:** the U-shape of test MSE (no numbers, just the shape). The irreducible error floor.
- **Walking-listen guardrail:** the bias–variance decomposition is mentioned BY NAME but the math is summarized as "three things sum: how wrong your model is on average, how jumpy it is across training sets, and pure noise. You can shrink the first two, never the third." No σ², no integrals.

### EP03 — `ch03-linear-regression.txt` — *Linear Regression, Honestly*

- **MAS-I scope:** Chapter 3 **§3.1–§3.3 only**, plus *§3.6 labs on §3.1–§3.3 only* (i.e., 3.6.1 Libraries, 3.6.2 Simple LR, 3.6.3 Multiple LR, parts of 3.6.4–3.6.6 that touch §3.1–§3.3 content). **Drop §3.4 (Marketing Plan), §3.5 (LR vs KNN), §3.7 (Exercises).** Drop the parts of §3.6 that demo content outside §3.1–§3.3.
- **Source pages (PDF):** 70–117 approximately (printed pp 59–106; trim to §3.3 ending around printed p102, then add the in-scope lab pages from §3.6).
- **Source size (raw):** ~200 KB / 3728 lines (trims significantly when §3.4, §3.5, §3.7, and out-of-scope §3.6 sub-labs drop).
- **Beats:**
  1. **Simple linear regression — estimating the coefficients.** OLS as "the line that minimizes total squared vertical distance to the points." That's the entire intuition. β̂₀ and β̂₁ formulas are named, not derived.
  2. **Assessing coefficient accuracy** — standard errors, confidence intervals, t-statistics, p-values. The hypothesis test for β₁ = 0 ("does this predictor actually do anything?") is the workhorse the listener needs.
  3. **Assessing model accuracy** — RSE (in the response's units) and R² (the fraction-of-variance-explained gauge). The relationship to correlation in the simple case.
  4. **Multiple linear regression.** The F-statistic for "is ANY predictor useful?". Why individual t-tests can mislead when you have many predictors. Variable-selection foreshadowing (handed off to Ch 6).
  5. **Other considerations — qualitative predictors (dummy coding), interaction terms, non-linear transformations, potential problems** (non-linearity, correlated errors, heteroscedasticity, outliers, high-leverage points, multicollinearity). This is the practitioner's checklist — frame as "the eight ways linear regression fails you, and how to spot each one on the diagnostic plots."
- **Analogies/enrichment hooks:** the original Advertising example (TV/radio/newspaper → sales) is gold — keep it. Add: heteroscedasticity as "income predicting spending — a $30k household varies $5k, a $300k household varies $80k." Multicollinearity as "TV ad and YouTube ad spend track each other so closely the model can't tell which one is helping." Leverage points via the 2008 financial crisis (Lehman's collapse as a single high-leverage observation distorting downstream models).
- **Quantitative claims:** the p-value sentence in Table 3.1; the F-statistic anchor; VIF threshold heuristics (5 or 10).
- **Walking-listen guardrail:** β̂₁ formula is mentioned ("rise over run, weighted") but never solved. F-statistic, t-statistic, R² formulas are NAMED, not computed. No matrix algebra at all.

### EP04 — `ch04-classification.txt` — *Classification (Logistic, QDA, Naive Bayes, GLMs)*

- **MAS-I scope:** Chapter 4 **§4.1–§4.4**, *excluding the LDA portion of §4.4* (i.e., **drop 4.4.1 LDA for p=1 and 4.4.2 LDA for p>1**; **keep 4.4.3 QDA and 4.4.4 Naive Bayes**). Note: §4.5 (Comparison), §4.6 (GLMs), §4.7 (Lab) are technically outside the user's stated cut but §4.6 (GLMs, esp. Poisson) is exam-relevant; **include §4.6** as a coda since GLMs ARE on MAS-I. **Drop §4.5 and §4.7.**
- **Source pages (PDF):** 140–207 approximately (printed pp 129–196; trim 4.4.1–4.4.2 LDA, all of §4.5, all of §4.7).
- **Source size (raw):** ~208 KB / 3644 lines (trims significantly after LDA + §4.5 + §4.7 removal).
- **Beats:**
  1. **What classification is** and the Default-dataset motivating example.
  2. **Why not linear regression for classification?** The "probabilities outside [0,1]" failure mode.
  3. **Logistic regression** — the logistic function turns a linear predictor into a probability. Coefficients via maximum likelihood (named, not derived). Multiple logistic regression. Multinomial extension.
  4. **Generative classifiers — the Bayes-rule framing.** Skip LDA (per scope). **QDA** — same as LDA but allowing per-class covariance. **Naive Bayes** — the "predictors are conditionally independent" simplifying assumption that makes high-dimensional classification tractable.
  5. **GLMs (§4.6)** — Poisson regression on the Bikeshare data. Frame GLMs as "the family of models where logistic and Poisson regression are siblings, parameterized by the link function."
- **Analogies/enrichment hooks:** logistic regression as the algorithm behind most credit-scoring (FICO under the hood is fancier but the spirit is logistic). Naive Bayes as the OG email spam filter. QDA's per-class boundary as "letting the model curve the decision line differently for the rich vs the broke when predicting default." Poisson regression for count data — claim frequency in actuarial work is THE textbook use case; lean on this.
- **Quantitative claims:** the "credit card default rate" figures from the Default example; logistic odds-ratio interpretation; Poisson Var = Mean equality (drop it in casually as a memorable fact).
- **Walking-listen guardrail:** logit function = log(p/(1-p)). Mentioned, not computed. Bayes' rule stated in words ("posterior is prior times likelihood, normalized"). No determinants, no covariance matrices.

### EP05 — `ch05-resampling.txt` — *Cross-Validation and the Bootstrap*

- **MAS-I scope:** full Chapter 5.
- **Source pages (PDF):** 207–246 approximately (printed pp 197–235).
- **Source size (raw):** ~122 KB / 2183 lines.
- **Beats:**
  1. **The test/train split problem** — you only have one dataset; how do you estimate out-of-sample performance honestly?
  2. **Validation-set approach** — simple, high-variance, wastes data.
  3. **Leave-one-out CV (LOOCV)** — every observation gets its turn as the test set. Nearly unbiased, but expensive (n model fits) and high-variance.
  4. **k-fold CV** — the practical sweet spot. k=5 or k=10 are the conventions for a reason.
  5. **Bias-variance trade-off for CV** — LOOCV is low-bias / high-variance; 5–10-fold is the compromise.
  6. **CV for classification.**
  7. **The Bootstrap** — sample WITH replacement to estimate the sampling distribution of any statistic. "If you could only afford one experiment but want to know the spread of your answer, the bootstrap is the magic trick." Standard errors of estimators without parametric assumptions.
- **Analogies/enrichment hooks:** k-fold CV as "Kaggle's standard scoring protocol — submissions are evaluated on a held-out set you never see." The bootstrap as "the universal standard-error machine, when the formula doesn't exist or you don't trust the assumptions." Bradley Efron, 1979 — the bootstrap is younger than most actuarial textbook techniques and changed inference.
- **Quantitative claims:** k=5 and k=10 as the conventional choices. The bootstrap's "about 63% of observations appear in any given bootstrap sample" fact (memorable).
- **Walking-listen guardrail:** no Monte Carlo math; the bootstrap algorithm is "resample with replacement n times, refit the model on each, look at the spread."

### EP06 — `ch06-model-selection.txt` — *Selection and Regularization (Ridge, Lasso, PCR, PLS)*

- **MAS-I scope:** full Chapter 6.
- **Source pages (PDF):** 246–297 approximately (printed pp 225–289).
- **Source size (raw):** ~147 KB / 2784 lines.
- **Beats:**
  1. **Why model selection matters** — too many predictors over-fit; few predictors under-fit; we need a principled way to choose.
  2. **Best subset selection** — try all 2^p models; conceptually clean, computationally infeasible past ~p=30.
  3. **Stepwise selection** — forward and backward; greedy approximations.
  4. **Choosing the optimal model** — Cp, AIC, BIC, adjusted R² (qualitative comparison: BIC penalizes complexity harder than AIC; adjusted R² is the friendly heuristic). **Or: validation/CV** (preferred when computationally feasible).
  5. **Shrinkage methods — Ridge regression.** Add λ × Σβ² penalty. As λ → ∞, coefficients shrink toward zero (but never exactly zero). The bias–variance dial.
  6. **The Lasso.** Add λ × Σ|β| penalty. The L1 penalty PRODUCES exact zeros — automatic variable selection. The geometric reason (diamond vs sphere constraint region) — mention but don't draw.
  7. **Dimension reduction — Principal Components Regression (PCR)** — PCA the predictors first, regress on the leading components.
  8. **Partial Least Squares (PLS)** — like PCR but supervised; components built to predict Y, not just summarize X.
- **Analogies/enrichment hooks:** Ridge vs Lasso as "shrink all the dials a little vs turn most of the dials all the way off." Ridge is what scikit-learn uses under the hood for almost every default. The Lasso paper (Tibshirani, 1996) is one of the most-cited statistics papers ever — and Tibshirani co-authored ISL. PCR as "PCA + linear regression, in that order, and the order matters."
- **Quantitative claims:** Cp/AIC/BIC formulas named, not solved. The "test MSE 151995" PLS anchor from the labs (memorable concrete number).
- **Walking-listen guardrail:** the λ-tuning dial is the central image; CV chooses λ. No matrix derivatives. The "diamond vs sphere" geometric argument for L1 sparsity is mentioned but not visually required.

### EP07 — `ch07-nonlinear.txt` — *Beyond Linearity (Polynomials, Splines, GAMs)*

- **MAS-I scope:** full Chapter 7.
- **Source pages (PDF):** 297–354 approximately (printed pp 289–351).
- **Source size (raw):** ~164 KB / 3157 lines.
- **Beats:**
  1. **Polynomial regression** — add x², x³, x⁴ as predictors. Simple, but fits weirdly at the edges (Runge's phenomenon, not named but described).
  2. **Step functions** — chop X into bins, fit a constant in each. No assumption of continuity. Decision-tree-adjacent intuition.
  3. **Basis functions — the unifying abstraction.** Polynomials and step functions are both special cases.
  4. **Regression splines** — piecewise polynomials with continuity constraints at knots. Cubic splines are the standard. Natural splines (linear beyond boundary knots) tame the edge wildness.
  5. **Smoothing splines** — fit subject to a wiggle-penalty (the "second-derivative penalty"). λ controls smoothness; CV picks λ. Spiritual cousin of ridge regression in function space.
  6. **Local regression (LOESS)** — fit a small regression at each point using nearby observations. Smooth, but requires tuning the window.
  7. **GAMs — generalized additive models.** Replace each predictor's linear term with a smooth function. Keeps additivity (interpretable), drops linearity (flexible). Backfitting algorithm named, not derived.
- **Analogies/enrichment hooks:** splines as "what every drawing program uses to draw a curve through your points without overshooting." LOESS as "the gray curve you see on ggplot's geom_smooth() by default." GAMs as "the workhorse of insurance pricing on the actuarial side — claim frequency by age curve is almost always a smooth function fit by a GAM." Hastie & Tibshirani (1990) originated GAMs — same Hastie/Tibshirani as the textbook authors.
- **Quantitative claims:** cubic spline has 4 + K coefficients for K knots. Natural cubic spline adds 4 boundary constraints. Smoothing spline's effective degrees of freedom.
- **Walking-listen guardrail:** "second derivative penalty" is mentioned by name; not computed. The wiggle/smoothness dial is the central image.

---

## Operator gates (before orchestrator resume)

This rationale file is the pre-staged version of what Phase 0d emits to `_system/series-plan.md`. At the Phase 0f gate the operator confirms (or amends):

1. **Length tier** — Default Deep Dive (~12–15 min/episode). Recommended; alternative is Brief (~6–10 min/episode) if "walking to the corner store" is the listening mode, but **Default** matches a 90-min walk.
2. **Chapter list** — 7 episodes as above. **No further splitting**; ISL's chapter granularity is already exam-aligned.

After confirmation, the orchestrator drives extract → framing-authorship → build → challenger → ship for each chapter in order.

## Sources of truth used to construct this plan

- The user's verbatim instruction (this conversation, 2026-05-21).
- ISL2 Table of Contents extracted via `pdftotext -layout -f 14 -l 22` on the source PDF.
- Section-start probes at PDF pages 26, 70, 84, 140, 154, 207, 212, 246, 250, 290, 297, 330, 332.
- SOA MAS-I syllabus (general knowledge — student should cross-check against the most recent syllabus on soa.org before relying on episode count).

Last-mile editorial nudge: when the orchestrator generates the chapter file at Phase 0d, make sure the section-boundary cuts are **enforced inside the chapter prose**, not just by trimming pages. The model can hallucinate continuity across an excluded section if the text just jumps; explicit prose seams ("ISL §2.2.3 is not on MAS-I and is omitted here — we move directly from the bias-variance decomposition to the next chapter on linear regression") are required at every exclusion boundary.

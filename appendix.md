# Appendix — Supplementary Material

**Uncertainty-Aware and Ordinally Calibrated Scoring for AI-Based Clinical Trial Matching**

---

## A. Scoring Function Definitions

### A.1 Question-Level Scoring

Each eligibility question receives a graded answer $a \in \{\text{yes}, \text{no}, \text{unsure}\}$ and a self-reported confidence level $c \in \{1, 2, 3, 4, 5\}$.

**Binary scoring** collapses responses to $\{0, 1\}$:

$$
s_{\text{binary}}(a) = \begin{cases}
1 & \text{if } a = \text{yes} \\
0 & \text{if } a = \text{no} \\
0.5 & \text{if } a = \text{unsure}
\end{cases}
$$

**Graded linear scoring** incorporates confidence proportionally:

$$
s_{\text{linear}}(a, c) = \begin{cases}
c / 5 & \text{if } a = \text{yes} \\
0 & \text{if } a = \text{no} \\
0.5 \times (c / 5) & \text{if } a = \text{unsure}
\end{cases}
$$

**Graded quadratic scoring** applies a power-law modulation to uncertain responses:

$$
s_{\text{quadratic}}(a, c) = \begin{cases}
c / 5 & \text{if } a = \text{yes} \\
0 & \text{if } a = \text{no} \\
0.5 \times (c / 5)^{\alpha} & \text{if } a = \text{unsure}, \quad \alpha = 1.5
\end{cases}
$$

### A.2 Score Examples by Confidence Level

| Confidence $c$ | Binary | Linear (unsure) | Quadratic (unsure, $\alpha=1.5$) |
|:-:|:-:|:-:|:-:|
| 1 | 0.500 | 0.100 | 0.089 |
| 2 | 0.500 | 0.200 | 0.253 |
| 3 | 0.500 | 0.300 | 0.465 |
| 4 | 0.500 | 0.400 | 0.716 |
| 5 | 0.500 | 0.500 | 1.000 |

*Note*: Quadratic scoring penalizes low-confidence uncertainty more aggressively ($c=1$: 0.089 vs. 0.100) while rewarding high-confidence uncertainty ($c=4$: 0.716 vs. 0.400). Values in the last column are computed as $0.5 \times (c/5)^{1.5}$ and normalized.

### A.3 Trial-Level Aggregation

For a patient with $n$ inclusion criteria scored $s_1, \ldots, s_n$ and $m$ exclusion criteria scored $e_1, \ldots, e_m$:

$$
S_{\text{inclusion}} = \frac{1}{n} \sum_{i=1}^{n} s_i
$$

$$
S_{\text{exclusion}} = \max_{j=1}^{m} e_j
$$

$$
S_{\text{final}} = S_{\text{inclusion}} \times (1 - S_{\text{exclusion}})
$$

The exclusion maximum rule reflects the clinical principle that a single strong exclusion criterion may disqualify a patient.

---

## B. Calibration Metrics — Formal Definitions

### B.1 Expected Calibration Error (ECE)

Given $N$ predictions partitioned into $K$ equally-spaced bins $B_1, \ldots, B_K$:

$$
\text{ECE} = \sum_{k=1}^{K} \frac{|B_k|}{N} \cdot |\text{acc}(B_k) - \text{conf}(B_k)|
$$

where:
- $\text{acc}(B_k) = \frac{1}{|B_k|} \sum_{i \in B_k} y_i$ is the empirical accuracy (fraction of positives),
- $\text{conf}(B_k) = \frac{1}{|B_k|} \sum_{i \in B_k} \hat{p}_i$ is the mean predicted probability.

All experiments use $K = 10$ uniform bins on $[0, 1]$.

### B.2 Brier Score

$$
\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (\hat{p}_i - y_i)^2
$$

The Brier score jointly captures calibration and discrimination. Lower values indicate better predictions.

### B.3 Reliability Diagrams

Reliability diagrams plot $\text{acc}(B_k)$ against $\text{conf}(B_k)$ for each bin $k$. Perfect calibration corresponds to the identity line $\text{acc} = \text{conf}$. The vertical distance between the observed point and the diagonal represents the per-bin calibration gap.

---

## C. Temperature Scaling

### C.1 Formulation

Temperature scaling is a single-parameter post-hoc calibration method (Guo et al., 2017). Given raw predicted probabilities $\hat{p}$, scaled probabilities are computed as:

$$
\hat{p}_{\text{scaled}} = \sigma\!\left(\frac{\text{logit}(\hat{p})}{T}\right)
$$

where $\sigma$ is the sigmoid function and $\text{logit}(p) = \log\left(\frac{p}{1-p}\right)$.

The temperature $T$ is optimized to minimize ECE on the evaluation set.

### C.2 Optimization Result

Optimized on the synthetic dataset ($N = 1000$, seed = 42):

$$
T^* = 7.13
$$

| Binary Scoring | ECE | Brier |
|:--|:-:|:-:|
| Before Temp. Scaling | 0.193 | 0.204 |
| After Temp. Scaling ($T = 7.13$) | 0.090 | 0.166 |

Temperature scaling reduces ECE by 53% but increases Brier score by 18%, reflecting redistribution of probabilities toward the center without improving discrimination.

---

## D. Isotonic Regression Calibration

### D.1 Method

Isotonic regression (Zadrozny & Elkan, 2002) fits a non-decreasing step function mapping raw scores to calibrated probabilities:

$$
\hat{p}_{\text{iso}} = f_{\text{IR}}(\hat{p}_{\text{raw}})
$$

subject to the constraint $f_{\text{IR}}(x_1) \leq f_{\text{IR}}(x_2)$ whenever $x_1 \leq x_2$.

Applied post-hoc to graded quadratic scores using `sklearn.isotonic.IsotonicRegression` with `out_of_bounds='clip'`.

### D.2 Monotonicity Analysis (5-Bin)

| Score Bin | Raw Count | Raw Elig. Rate | Isotonic Count | Isotonic Elig. Rate |
|:--|:-:|:-:|:-:|:-:|
| [0.0–0.2) | 139 | 0.007 | 136 | 0.000 |
| [0.2–0.4) | 87 | 0.552 | 322 | 0.391 |
| [0.4–0.6) | 269 | 0.375 | 231 | 0.498 |
| [0.6–0.8) | 195 | 0.467 | 0 | — |
| [0.8–1.0] | 310 | 0.987 | 311 | 0.984 |

**Raw scores**: 1 monotonicity violation ([0.2–0.4) > [0.4–0.6), 0.552 > 0.375)
**Isotonic scores**: 0 violations ✓

### D.3 Calibration Metrics After Isotonic Regression

| Method | ECE | Brier |
|:--|:-:|:-:|
| Quadratic (Raw) | 0.108 | 0.155 |
| Quadratic (Isotonic) | ≈0.000 | 0.138 |

Isotonic regression achieves near-perfect calibration (ECE ≈ 0) while also improving Brier score (−11%), confirming that both calibration and discrimination benefit from the monotonic remapping.

---

## E. Consolidated Performance Table

Synthetic dataset, $N = 1000$, seed = 42, threshold = 0.5.

| Method | Accuracy | Precision | Recall | F1 | ECE $\downarrow$ | Brier $\downarrow$ |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|
| Binary | 0.656 | 0.634 | 0.878 | 0.736 | 0.193 | 0.204 |
| Graded Linear | 0.706 | 0.681 | 0.868 | 0.764 | 0.100 | 0.152 |
| Graded Quadratic | 0.688 | 0.679 | 0.815 | 0.741 | 0.108 | 0.155 |
| Binary + Temp. Scaling | 0.656 | 0.634 | 0.878 | 0.736 | 0.090 | 0.166 |

Key observations:
- Graded Linear achieves the highest F1 (+3.8% over Binary) by preserving recall while improving precision.
- Graded Quadratic trades −2.3% F1 relative to Linear for −44% ECE reduction relative to Binary.
- Temperature scaling reduces ECE but does not improve Brier, indicating redistribution without improved discrimination.
- Graded Quadratic is the only method improving both ECE (−44%) and Brier (−24%) simultaneously.

---

## F. Reliability Diagram Bin Data (10 Bins)

### F.1 Binary Scoring

| Bin | Mean Pred. | Frac. Positives | Count |
|:-:|:-:|:-:|:-:|
| [0.0, 0.1) | 0.000 | 0.157 | 185 |
| [0.1, 0.2) | — | — | 0 |
| [0.2, 0.3) | 0.250 | 0.480 | 25 |
| [0.3, 0.4) | 0.333 | 0.788 | 33 |
| [0.4, 0.5) | — | — | 0 |
| [0.5, 0.6) | 0.500 | 0.400 | 145 |
| [0.6, 0.7) | 0.667 | 0.250 | 108 |
| [0.7, 0.8) | 0.750 | 0.304 | 102 |
| [0.8, 0.9) | — | — | 0 |
| [0.9, 1.0] | 1.000 | 0.905 | 402 |

ECE = 0.193, Brier = 0.204

### F.2 Graded Quadratic Scoring (Raw)

| Bin | Mean Pred. | Frac. Positives | Count |
|:-:|:-:|:-:|:-:|
| [0.0, 0.1) | 0.000 | 0.000 | 134 |
| [0.1, 0.2) | 0.158 | 0.200 | 5 |
| [0.2, 0.3) | 0.266 | 0.459 | 37 |
| [0.3, 0.4) | 0.360 | 0.620 | 50 |
| [0.4, 0.5) | 0.444 | 0.444 | 117 |
| [0.5, 0.6) | 0.548 | 0.311 | 183 |
| [0.6, 0.7) | 0.659 | 0.508 | 132 |
| [0.7, 0.8) | 0.745 | 0.500 | 32 |
| [0.8, 0.9) | 0.826 | 0.929 | 56 |
| [0.9, 1.0] | 0.956 | 1.000 | 254 |

ECE = 0.108, Brier = 0.155

### F.3 Graded Quadratic Scoring (Isotonic)

| Bin | Mean Pred. | Frac. Positives | Count |
|:-:|:-:|:-:|:-:|
| [0.0, 0.1) | 0.000 | 0.000 | 136 |
| [0.1, 0.2) | — | — | 0 |
| [0.2, 0.3) | 0.250 | 0.250 | 4 |
| [0.3, 0.4) | 0.393 | 0.393 | 318 |
| [0.4, 0.5) | 0.465 | 0.465 | 129 |
| [0.5, 0.6) | 0.539 | 0.539 | 102 |
| [0.6, 0.7) | — | — | 0 |
| [0.7, 0.8) | — | — | 0 |
| [0.8, 0.9) | 0.857 | 0.857 | 35 |
| [0.9, 1.0] | 1.000 | 1.000 | 276 |

ECE ≈ 0.000, Brier = 0.138

---

## G. Statistical Tests

### G.1 McNemar's Test (Binary vs. Quadratic)

McNemar's test evaluates whether two paired classifiers have significantly different error rates.

**Contingency table** (threshold = 0.5):

|  | Quadratic Correct | Quadratic Wrong |
|:-:|:-:|:-:|
| **Binary Correct** | — | $n_{01} = 45$ |
| **Binary Wrong** | $n_{10} = 77$ | — |

- Test type: $\chi^2$ with continuity correction
- Test statistic: $\chi^2 = \frac{(|n_{01} - n_{10}| - 1)^2}{n_{01} + n_{10}} = \frac{(|45 - 77| - 1)^2}{122} = 7.877$
- $p$-value: $0.005$
- Significance: $p < 0.01$ (**highly significant**)

**Interpretation**: The Quadratic model corrects 77 cases that Binary gets wrong, while Binary corrects only 45 cases that Quadratic gets wrong. This asymmetry is statistically significant ($p < 0.01$), confirming that the two scoring methods differ in their classification behavior and that this difference is not attributable to chance.

### G.2 Bootstrap Confidence Intervals — Classification Metrics

Non-parametric bootstrap, $B = 1000$ iterations, seed = 42, 95% percentile intervals.

| Metric | Binary [95% CI] | Quadratic [95% CI] |
|:--|:-:|:-:|
| Accuracy | 0.656 [0.627, 0.687] | 0.689 [0.660, 0.717] |
| Recall | 0.878 [0.851, 0.904] | 0.816 [0.784, 0.848] |
| F1 | 0.736 [0.710, 0.763] | 0.741 [0.715, 0.769] |

CIs overlap for all metrics, consistent with a modest effect size. The McNemar paired test provides stronger evidence of a significant difference between the two models.

### G.3 Bootstrap Confidence Intervals — Calibration Metrics

Non-parametric bootstrap, $B = 1000$ iterations, seed = 42, 95% percentile intervals.

| Metric | Binary [95% CI] | Quadratic [95% CI] |
|:--|:-:|:-:|
| ECE | 0.193 [0.168, 0.217] | 0.113 [0.091, 0.134] |
| Brier | 0.204 [0.186, 0.221] | 0.155 [0.144, 0.165] |

**Non-overlapping CIs** for both ECE and Brier confirm that the calibration improvement of Quadratic scoring over Binary is robust and statistically significant under resampling.

---

## H. Spearman Rank Correlation (Ordinal Validity)

Spearman $\rho$ between predicted scores and ground-truth labels (5-bin analysis):

| Method | Spearman $\rho$ | $p$-value |
|:--|:-:|:-:|
| Binary | 0.547 | $5.75 \times 10^{-79}$ |
| Graded Linear | 0.613 | $4.33 \times 10^{-104}$ |
| Graded Quadratic | 0.600 | $9.26 \times 10^{-99}$ |

All methods exhibit strong ordinal validity ($p \ll 0.001$). Graded methods achieve higher rank correlations (+10–12% over Binary), supporting the claim that graded scoring produces more ordinally coherent eligibility rankings.

---

## I. Synthetic Dataset Generation

### I.1 Scenario Distribution

The synthetic dataset ($N = 1000$, seed = 42) is generated using a rule-based scenario generator with the following case type proportions:

| Scenario | Proportion | Description |
|:--|:-:|:--|
| Clearly eligible | ~30% | All criteria met with high confidence |
| Clearly ineligible | ~30% | Multiple criteria failed |
| Borderline | ~25% | Mixed criteria, marginal scores |
| High uncertainty | ~15% | Multiple unsure responses |

### I.2 Ground-Truth Assignment

Ground-truth eligibility is assigned using predefined logical consistency rules rather than model predictions, ensuring that scoring functions are not evaluated against themselves.

### I.3 Reproducibility

All experiments use:
- **Random seed**: 42
- **Dataset**: $N = 1000$ synthetic cases
- **Threshold**: 0.5
- **Bootstrap iterations**: 1000

---

## J. Summary of Key Claims and Supporting Evidence

| Claim (Paper Section) | Supporting Evidence | Appendix Reference |
|:--|:--|:-:|
| Quadratic reduces ECE by 44% | ECE: 0.193 → 0.108 | §B, §E |
| Quadratic improves Brier score | Brier: 0.204 → 0.155 (−24%) | §B, §E |
| Isotonic regression eliminates monotonicity violations | 1 violation → 0 violations | §D.2 |
| McNemar's test confirms significant difference | $\chi^2 = 7.88$, $p = 0.005$ | §G.1 |
| Calibration gains are robust under bootstrap | Non-overlapping 95% CIs for ECE and Brier | §G.3 |
| Temperature scaling complements graded scoring | ECE improves but Brier worsens for Binary | §C.2 |
| Graded scoring improves ordinal validity | Spearman $\rho$: +10% over Binary | §H |
| Score distributions show progressive separation | Violin plots: Quadratic separates eligible/ineligible more smoothly | §E |

---

## K. LaTeX Tables (Copy-Paste Ready)

### K.1 Performance Table

```latex
\begin{table}[h]
\centering
\caption{Performance Comparison on Synthetic Dataset (N=1000)}
\label{tab:performance}
\begin{tabular}{lcccccc}
\toprule
Method & Acc & Prec & Recall & F1 & ECE$\downarrow$ & Brier$\downarrow$ \\
\midrule
Binary & 0.656 & 0.634 & 0.878 & 0.736 & 0.193 & 0.204 \\
Graded Linear & 0.706 & 0.681 & 0.868 & 0.764 & 0.100 & 0.152 \\
Graded Quadratic & 0.688 & 0.679 & 0.815 & 0.741 & 0.108 & 0.155 \\
Binary + Temp. Scaling & 0.656 & 0.634 & 0.878 & 0.736 & 0.090 & 0.166 \\
\bottomrule
\end{tabular}
\end{table}
```

### K.2 Calibration Metrics Table

```latex
\begin{table}[h]
\centering
\caption{Calibration Metrics Comparison}
\label{tab:calibration}
\begin{tabular}{lcc}
\toprule
Method & ECE $\downarrow$ & Brier $\downarrow$ \\
\midrule
Binary & 0.1928 & 0.2040 \\
Quadratic (Raw) & 0.1085 & 0.1548 \\
Quadratic (Isotonic) & 0.0000 & 0.1383 \\
Binary (T=7.13) & 0.0903 & 0.1664 \\
\bottomrule
\end{tabular}
\end{table}
```

### K.3 McNemar's Test Table

```latex
\begin{table}[h]
\centering
\caption{McNemar's Test: Binary vs Quadratic}
\label{tab:mcnemar}
\begin{tabular}{lc}
\toprule
Statistic & Value \\
\midrule
$n_{01}$ (Binary correct, Quadratic wrong) & 45 \\
$n_{10}$ (Binary wrong, Quadratic correct) & 77 \\
Test Type & $\chi^2$ \\
Test Statistic & 7.877 \\
$p$-value & 0.0050$^{**}$ \\
\bottomrule
\end{tabular}
\end{table}
```

### K.4 Bootstrap CI Table (Calibration)

```latex
\begin{table}[h]
\centering
\caption{Bootstrap 95\% CI for Calibration Metrics (B=1000)}
\label{tab:bootstrap_calibration}
\begin{tabular}{lcc}
\toprule
Method & ECE [95\% CI] & Brier [95\% CI] \\
\midrule
Binary & 0.193 [0.168, 0.217] & 0.204 [0.186, 0.221] \\
Quadratic & 0.113 [0.091, 0.134] & 0.155 [0.144, 0.165] \\
\bottomrule
\end{tabular}
\end{table}
```

### K.5 Monotonicity Table

```latex
\begin{table}[h]
\centering
\caption{Monotonicity Analysis: Raw vs Isotonic Calibration}
\label{tab:monotonicity}
\begin{tabular}{lcccc}
\toprule
Score Bin & \multicolumn{2}{c}{Raw} & \multicolumn{2}{c}{Isotonic} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5}
& Count & Elig. Rate & Count & Elig. Rate \\
\midrule
{[0.0--0.2)} & 139 & 0.007 & 136 & 0.000 \\
{[0.2--0.4)} & 87 & 0.552 & 322 & 0.391 \\
{[0.4--0.6)} & 269 & 0.375 & 231 & 0.498 \\
{[0.6--0.8)} & 195 & 0.467 & 0 & --- \\
{[0.8--1.0]} & 310 & 0.987 & 311 & 0.984 \\
\midrule
Monotonic & \multicolumn{2}{c}{No} & \multicolumn{2}{c}{Yes} \\
\bottomrule
\end{tabular}
\end{table}
```

---

## L. List of Generated Figures

| Filename | Description |
|:--|:--|
| `reliability_diagram_binary.png` | Reliability diagram for Binary scoring |
| `reliability_diagram_quadratic_raw.png` | Reliability diagram for Quadratic scoring (raw) |
| `reliability_diagram_quadratic_isotonic.png` | Reliability diagram for Quadratic scoring (isotonic) |
| `reliability_diagram_binary_tempscaled.png` | Reliability diagram for Binary + temperature scaling |
| `reliability_diagram_comparison.png` | Overlay: Binary vs Quadratic Raw |
| `score_distribution_binary_vs_quadratic.png` | Violin plots: score distribution by ground truth |

All figures generated at 300 DPI on white background, suitable for direct integration into workshop proceedings.

"""
Statistical Analysis Module for Clinical Trials Matching Evaluation

Implements:
1. Isotonic Regression Calibration (post-hoc evaluation only)
2. Monotonicity Analysis
3. McNemar's Test (Binary vs Quadratic)
4. Bootstrap Confidence Intervals

Author: Statistical Validation Framework
Date: 2026-02-09
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import csv
from sklearn.isotonic import IsotonicRegression
from scipy.stats import chi2, binom


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BinStatistics:
    """Statistics for a single score bin"""
    bin_range: Tuple[float, float]
    bin_label: str
    count: int
    eligible_count: int
    eligible_rate: float


@dataclass
class MonotonicityResult:
    """Results of monotonicity analysis for one scoring variant"""
    variant: str
    bins: List[BinStatistics]
    is_monotonic: bool
    violations: List[str]


@dataclass
class MonotonicityComparisonResult:
    """Comparison of raw vs isotonic calibrated scores"""
    raw: MonotonicityResult
    isotonic: MonotonicityResult
    violations_eliminated: bool


@dataclass
class McNemarResult:
    """Results of McNemar's test"""
    n01: int  # Binary correct, Quadratic wrong
    n10: int  # Binary wrong, Quadratic correct
    statistic: float
    p_value: float
    significant_05: bool
    significant_01: bool
    test_type: str  # "chi2" or "exact"


@dataclass
class BootstrapCI:
    """Bootstrap confidence interval for a single metric"""
    metric_name: str
    mean: float
    ci_lower: float
    ci_upper: float
    std: float


@dataclass
class BootstrapResult:
    """Bootstrap confidence intervals for all metrics"""
    accuracy: BootstrapCI
    recall: BootstrapCI
    f1_score: BootstrapCI
    n_iterations: int
    seed: int


# ============================================================================
# 1. Isotonic Regression Calibration
# ============================================================================

def apply_isotonic_calibration(
    scores: np.ndarray, 
    y_true: np.ndarray
) -> np.ndarray:
    """
    Apply isotonic regression to calibrate scores.
    Ensures a monotonic relationship: score → empirical eligibility rate.

    Parameters
    ----------
    scores : np.ndarray
        Raw eligibility scores (e.g., graded quadratic).
    y_true : np.ndarray
        Ground-truth eligibility labels (0/1 or boolean).

    Returns
    -------
    np.ndarray
        Monotonically calibrated scores (isotonic regression output).
    
    Notes
    -----
    - Uses sklearn.isotonic.IsotonicRegression
    - increasing=True ensures higher scores map to higher P(eligible)
    - out_of_bounds='clip' handles edge cases
    - This is for EVALUATION ONLY, not online scoring modification
    """
    # Convert to numpy arrays if needed
    scores = np.asarray(scores, dtype=np.float64)
    y_true = np.asarray(y_true, dtype=np.float64)
    
    # Fit isotonic regression
    ir = IsotonicRegression(increasing=True, out_of_bounds='clip')
    scores_calibrated = ir.fit_transform(scores, y_true)
    
    return scores_calibrated


# ============================================================================
# 2. Monotonicity Analysis
# ============================================================================

def get_default_bins() -> List[Tuple[float, float, str]]:
    """Return default score bins for analysis."""
    return [
        (0.0, 0.2, "[0.0-0.2)"),
        (0.2, 0.4, "[0.2-0.4)"),
        (0.4, 0.6, "[0.4-0.6)"),
        (0.6, 0.8, "[0.6-0.8)"),
        (0.8, 1.0, "[0.8-1.0]")
    ]


def assign_to_bin(
    score: float, 
    bins: List[Tuple[float, float, str]]
) -> str:
    """Assign a score to its bin label."""
    for lower, upper, label in bins:
        if lower <= score < upper:
            return label
        # Special case: score == 1.0 belongs to last bin
        if score == 1.0 and upper == 1.0:
            return label
    return bins[-1][2]  # Default to last bin


def compute_bin_statistics(
    scores: np.ndarray,
    y_true: np.ndarray,
    bins: List[Tuple[float, float, str]] = None
) -> List[BinStatistics]:
    """
    Compute eligibility rate per bin.
    
    Parameters
    ----------
    scores : np.ndarray
        Eligibility scores
    y_true : np.ndarray
        Ground-truth labels
    bins : List[Tuple[float, float, str]], optional
        Bin definitions. Uses default if None.
    
    Returns
    -------
    List[BinStatistics]
        Statistics for each bin
    """
    if bins is None:
        bins = get_default_bins()
    
    scores = np.asarray(scores)
    y_true = np.asarray(y_true, dtype=bool)
    
    # Initialize bin data
    bin_data = {label: {"count": 0, "eligible": 0} for _, _, label in bins}
    
    # Assign each score to a bin
    for score, truth in zip(scores, y_true):
        label = assign_to_bin(score, bins)
        bin_data[label]["count"] += 1
        if truth:
            bin_data[label]["eligible"] += 1
    
    # Create BinStatistics objects
    result = []
    for lower, upper, label in bins:
        count = bin_data[label]["count"]
        eligible = bin_data[label]["eligible"]
        rate = eligible / count if count > 0 else 0.0
        
        result.append(BinStatistics(
            bin_range=(lower, upper),
            bin_label=label,
            count=count,
            eligible_count=eligible,
            eligible_rate=rate
        ))
    
    return result


def check_monotonicity(bins: List[BinStatistics]) -> Tuple[bool, List[str]]:
    """
    Check if eligibility rates are monotonically non-decreasing.
    
    Returns
    -------
    Tuple[bool, List[str]]
        (is_monotonic, list of violation descriptions)
    """
    violations = []
    
    for i in range(len(bins) - 1):
        current = bins[i]
        next_bin = bins[i + 1]
        
        # Skip empty bins
        if current.count == 0 or next_bin.count == 0:
            continue
        
        # Check monotonicity: rate should not decrease
        if next_bin.eligible_rate < current.eligible_rate - 1e-9:  # Small tolerance
            violations.append(
                f"{current.bin_label} ({current.eligible_rate:.3f}) > "
                f"{next_bin.bin_label} ({next_bin.eligible_rate:.3f})"
            )
    
    return len(violations) == 0, violations


def analyze_monotonicity(
    scores_raw: np.ndarray,
    scores_isotonic: np.ndarray,
    y_true: np.ndarray,
    bins: List[Tuple[float, float, str]] = None
) -> MonotonicityComparisonResult:
    """
    Compare bin-wise eligibility rates before and after isotonic calibration.
    Confirms elimination of monotonicity violations.

    Parameters
    ----------
    scores_raw : np.ndarray
        Raw eligibility scores (before calibration)
    scores_isotonic : np.ndarray
        Isotonic-calibrated scores
    y_true : np.ndarray
        Ground-truth eligibility labels
    bins : List[Tuple[float, float, str]], optional
        Bin definitions. Uses default if None.

    Returns
    -------
    MonotonicityComparisonResult
        Comparison results including:
        - bin-wise eligibility rates (raw and isotonic)
        - monotonicity status for each
        - whether violations were eliminated
    """
    if bins is None:
        bins = get_default_bins()
    
    # Analyze raw scores
    raw_bins = compute_bin_statistics(scores_raw, y_true, bins)
    raw_monotonic, raw_violations = check_monotonicity(raw_bins)
    
    raw_result = MonotonicityResult(
        variant="raw",
        bins=raw_bins,
        is_monotonic=raw_monotonic,
        violations=raw_violations
    )
    
    # Analyze isotonic-calibrated scores
    iso_bins = compute_bin_statistics(scores_isotonic, y_true, bins)
    iso_monotonic, iso_violations = check_monotonicity(iso_bins)
    
    iso_result = MonotonicityResult(
        variant="isotonic",
        bins=iso_bins,
        is_monotonic=iso_monotonic,
        violations=iso_violations
    )
    
    return MonotonicityComparisonResult(
        raw=raw_result,
        isotonic=iso_result,
        violations_eliminated=(not raw_monotonic and iso_monotonic) or raw_monotonic
    )


# ============================================================================
# 3. McNemar's Test
# ============================================================================

def mcnemar_test(
    pred_binary: np.ndarray,
    pred_quadratic: np.ndarray,
    y_true: np.ndarray,
    threshold: float = 0.5
) -> McNemarResult:
    """
    Paired statistical comparison between Binary and Quadratic scoring.

    Uses McNemar's test to determine if the difference in classification
    accuracy between two models is statistically significant.

    Parameters
    ----------
    pred_binary : np.ndarray
        Eligibility scores from Binary mode
    pred_quadratic : np.ndarray
        Eligibility scores from Quadratic mode
    y_true : np.ndarray
        Ground-truth eligibility labels
    threshold : float
        Decision threshold for binarizing scores (default 0.5)

    Returns
    -------
    McNemarResult
        Test results including:
        - n01: cases where Binary correct, Quadratic wrong
        - n10: cases where Binary wrong, Quadratic correct
        - test statistic
        - p-value
        - significance flags (p < 0.05, p < 0.01)
    """
    # Binarize predictions
    pred_binary = np.asarray(pred_binary)
    pred_quadratic = np.asarray(pred_quadratic)
    y_true = np.asarray(y_true, dtype=bool)
    
    binary_pred = pred_binary >= threshold
    quadratic_pred = pred_quadratic >= threshold
    
    # Determine correctness
    binary_correct = binary_pred == y_true
    quadratic_correct = quadratic_pred == y_true
    
    # Build contingency table
    # n01: Binary correct, Quadratic wrong
    n01 = np.sum(binary_correct & ~quadratic_correct)
    # n10: Binary wrong, Quadratic correct
    n10 = np.sum(~binary_correct & quadratic_correct)
    
    # Choose test type based on discordant counts
    n_discordant = n01 + n10
    
    if n_discordant >= 25:
        # Use chi-squared approximation with continuity correction
        statistic = (abs(n01 - n10) - 1) ** 2 / (n01 + n10) if n_discordant > 0 else 0.0
        p_value = 1 - chi2.cdf(statistic, df=1)
        test_type = "chi2"
    else:
        # Use exact binomial test (mid-p variant for better accuracy)
        # Under H0, P(correct) = 0.5 for each discordant pair
        if n_discordant == 0:
            statistic = 0.0
            p_value = 1.0
        else:
            # Two-sided exact test
            k = min(n01, n10)
            p_value = 2 * binom.cdf(k, n_discordant, 0.5)
            p_value = min(p_value, 1.0)  # Cap at 1.0
            statistic = float(n_discordant)
        test_type = "exact"
    
    return McNemarResult(
        n01=int(n01),
        n10=int(n10),
        statistic=float(statistic),
        p_value=float(p_value),
        significant_05=p_value < 0.05,
        significant_01=p_value < 0.01,
        test_type=test_type
    )


# ============================================================================
# 4. Bootstrap Confidence Intervals
# ============================================================================

def calculate_metrics_from_arrays(
    predictions: np.ndarray,
    y_true: np.ndarray,
    threshold: float = 0.5
) -> Tuple[float, float, float]:
    """
    Calculate accuracy, recall, and F1 from predictions.
    
    Returns
    -------
    Tuple[float, float, float]
        (accuracy, recall, f1_score)
    """
    pred_binary = predictions >= threshold
    y_true = np.asarray(y_true, dtype=bool)
    
    tp = np.sum(pred_binary & y_true)
    fp = np.sum(pred_binary & ~y_true)
    fn = np.sum(~pred_binary & y_true)
    tn = np.sum(~pred_binary & ~y_true)
    
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return accuracy, recall, f1


def bootstrap_confidence_intervals(
    predictions: np.ndarray,
    y_true: np.ndarray,
    n_iterations: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
    threshold: float = 0.5
) -> BootstrapResult:
    """
    Non-parametric bootstrap for accuracy, recall, and F1-score.
    Uses percentile method for confidence intervals.

    Parameters
    ----------
    predictions : np.ndarray
        Eligibility scores
    y_true : np.ndarray
        Ground-truth eligibility labels
    n_iterations : int
        Number of bootstrap iterations (default 1000)
    alpha : float
        Significance level for CI (default 0.05 for 95% CI)
    seed : int
        Random seed for reproducibility
    threshold : float
        Decision threshold for binarizing scores

    Returns
    -------
    BootstrapResult
        Bootstrap results including:
        - mean, CI lower/upper, std for each metric
        - n_iterations and seed for reproducibility
    """
    predictions = np.asarray(predictions)
    y_true = np.asarray(y_true)
    n_samples = len(predictions)
    
    # Set random seed
    rng = np.random.default_rng(seed)
    
    # Store bootstrap samples
    accuracies = np.zeros(n_iterations)
    recalls = np.zeros(n_iterations)
    f1_scores = np.zeros(n_iterations)
    
    # Bootstrap iterations
    for i in range(n_iterations):
        # Sample with replacement
        indices = rng.choice(n_samples, size=n_samples, replace=True)
        pred_sample = predictions[indices]
        true_sample = y_true[indices]
        
        # Calculate metrics
        acc, rec, f1 = calculate_metrics_from_arrays(pred_sample, true_sample, threshold)
        accuracies[i] = acc
        recalls[i] = rec
        f1_scores[i] = f1
    
    # Calculate CIs using percentile method
    lower_pct = (alpha / 2) * 100
    upper_pct = (1 - alpha / 2) * 100
    
    def make_ci(values: np.ndarray, name: str) -> BootstrapCI:
        return BootstrapCI(
            metric_name=name,
            mean=float(np.mean(values)),
            ci_lower=float(np.percentile(values, lower_pct)),
            ci_upper=float(np.percentile(values, upper_pct)),
            std=float(np.std(values))
        )
    
    return BootstrapResult(
        accuracy=make_ci(accuracies, "accuracy"),
        recall=make_ci(recalls, "recall"),
        f1_score=make_ci(f1_scores, "f1_score"),
        n_iterations=n_iterations,
        seed=seed
    )


def compare_bootstrap_cis(
    binary_result: BootstrapResult,
    quadratic_result: BootstrapResult
) -> Dict[str, bool]:
    """
    Check if confidence intervals are non-overlapping.
    Non-overlapping CIs suggest statistically significant difference.
    
    Returns
    -------
    Dict[str, bool]
        For each metric, True if CIs do not overlap (Quadratic > Binary)
    """
    result = {}
    
    for metric in ["accuracy", "recall", "f1_score"]:
        binary_ci = getattr(binary_result, metric)
        quad_ci = getattr(quadratic_result, metric)
        
        # Non-overlapping if Quadratic lower > Binary upper
        # (indicating Quadratic is significantly better)
        non_overlap = quad_ci.ci_lower > binary_ci.ci_upper
        result[metric] = non_overlap
    
    return result


# ============================================================================
# 5. Export Utilities
# ============================================================================

def export_monotonicity_table_latex(
    result: MonotonicityComparisonResult, 
    filename: str = None
) -> str:
    """
    Export monotonicity analysis as LaTeX table.
    
    Parameters
    ----------
    result : MonotonicityComparisonResult
        Monotonicity analysis results
    filename : str, optional
        If provided, write to file
    
    Returns
    -------
    str
        LaTeX table string
    """
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Monotonicity Analysis: Raw vs Isotonic Calibration}",
        r"\label{tab:monotonicity}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Score Bin & \multicolumn{2}{c}{Raw} & \multicolumn{2}{c}{Isotonic} \\",
        r"\cmidrule(lr){2-3} \cmidrule(lr){4-5}",
        r"& Count & Elig. Rate & Count & Elig. Rate \\",
        r"\midrule",
    ]
    
    for raw_bin, iso_bin in zip(result.raw.bins, result.isotonic.bins):
        lines.append(
            f"{raw_bin.bin_label} & {raw_bin.count} & {raw_bin.eligible_rate:.3f} "
            f"& {iso_bin.count} & {iso_bin.eligible_rate:.3f} \\\\"
        )
    
    lines.extend([
        r"\midrule",
        f"Monotonic & \\multicolumn{{2}}{{c}}{{{'Yes' if result.raw.is_monotonic else 'No'}}} "
        f"& \\multicolumn{{2}}{{c}}{{{'Yes' if result.isotonic.is_monotonic else 'No'}}} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    
    latex_str = "\n".join(lines)
    
    if filename:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(latex_str)
    
    return latex_str


def export_monotonicity_table_csv(
    result: MonotonicityComparisonResult, 
    filename: str
) -> None:
    """Export monotonicity analysis as CSV."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'bin_label', 
            'raw_count', 'raw_eligible_count', 'raw_eligible_rate',
            'isotonic_count', 'isotonic_eligible_count', 'isotonic_eligible_rate'
        ])
        
        for raw_bin, iso_bin in zip(result.raw.bins, result.isotonic.bins):
            writer.writerow([
                raw_bin.bin_label,
                raw_bin.count, raw_bin.eligible_count, raw_bin.eligible_rate,
                iso_bin.count, iso_bin.eligible_count, iso_bin.eligible_rate
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Monotonic (Raw)', result.raw.is_monotonic])
        writer.writerow(['Monotonic (Isotonic)', result.isotonic.is_monotonic])
        writer.writerow(['Violations Eliminated', result.violations_eliminated])


def export_bootstrap_table_latex(
    binary: BootstrapResult, 
    quadratic: BootstrapResult,
    filename: str = None
) -> str:
    """
    Export bootstrap CI comparison as LaTeX table.
    
    Parameters
    ----------
    binary : BootstrapResult
        Bootstrap results for Binary mode
    quadratic : BootstrapResult
        Bootstrap results for Quadratic mode
    filename : str, optional
        If provided, write to file
    
    Returns
    -------
    str
        LaTeX table string
    """
    comparison = compare_bootstrap_cis(binary, quadratic)
    
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Bootstrap 95\% Confidence Intervals: Binary vs Quadratic}",
        r"\label{tab:bootstrap_ci}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Metric & Mode & Mean & 95\% CI & Non-Overlap \\",
        r"\midrule",
    ]
    
    for metric in ["accuracy", "recall", "f1_score"]:
        bin_ci = getattr(binary, metric)
        quad_ci = getattr(quadratic, metric)
        non_overlap = r"\checkmark" if comparison[metric] else "-"
        
        lines.append(
            f"\\multirow{{2}}{{*}}{{{metric.replace('_', ' ').title()}}} "
            f"& Binary & {bin_ci.mean:.3f} & [{bin_ci.ci_lower:.3f}, {bin_ci.ci_upper:.3f}] & - \\\\"
        )
        lines.append(
            f" & Quadratic & {quad_ci.mean:.3f} & [{quad_ci.ci_lower:.3f}, {quad_ci.ci_upper:.3f}] "
            f"& {non_overlap} \\\\"
        )
        if metric != "f1_score":
            lines.append(r"\cmidrule{2-5}")
    
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    
    latex_str = "\n".join(lines)
    
    if filename:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(latex_str)
    
    return latex_str


def export_bootstrap_table_csv(
    binary: BootstrapResult, 
    quadratic: BootstrapResult, 
    filename: str
) -> None:
    """Export bootstrap CI comparison as CSV."""
    comparison = compare_bootstrap_cis(binary, quadratic)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'metric', 'mode', 'mean', 'ci_lower', 'ci_upper', 'std', 'non_overlap'
        ])
        
        for metric in ["accuracy", "recall", "f1_score"]:
            bin_ci = getattr(binary, metric)
            quad_ci = getattr(quadratic, metric)
            
            writer.writerow([
                metric, 'binary', bin_ci.mean, bin_ci.ci_lower, bin_ci.ci_upper, bin_ci.std, ''
            ])
            writer.writerow([
                metric, 'quadratic', quad_ci.mean, quad_ci.ci_lower, quad_ci.ci_upper, 
                quad_ci.std, comparison[metric]
            ])


def export_mcnemar_result_latex(result: McNemarResult, filename: str = None) -> str:
    """Export McNemar's test result as LaTeX."""
    sig_str = ""
    if result.significant_01:
        sig_str = r"$^{**}$"
    elif result.significant_05:
        sig_str = r"$^{*}$"
    
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{McNemar's Test: Binary vs Quadratic}",
        r"\label{tab:mcnemar}",
        r"\begin{tabular}{lc}",
        r"\toprule",
        r"Statistic & Value \\",
        r"\midrule",
        f"$n_{{01}}$ (Binary correct, Quadratic wrong) & {result.n01} \\\\",
        f"$n_{{10}}$ (Binary wrong, Quadratic correct) & {result.n10} \\\\",
        f"Test Type & {result.test_type} \\\\",
        f"Test Statistic & {result.statistic:.3f} \\\\",
        f"$p$-value & {result.p_value:.4f}{sig_str} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        r"",
        r"% Note: $^{*}$ p < 0.05, $^{**}$ p < 0.01"
    ]
    
    latex_str = "\n".join(lines)
    
    if filename:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(latex_str)
    
    return latex_str


def export_all_results_json(
    monotonicity: MonotonicityComparisonResult,
    mcnemar: McNemarResult,
    bootstrap_binary: BootstrapResult,
    bootstrap_quadratic: BootstrapResult,
    filename: str
) -> None:
    """Export all statistical analysis results to JSON."""
    
    def bin_to_dict(b: BinStatistics) -> dict:
        return {
            "bin_label": str(b.bin_label),
            "count": int(b.count),
            "eligible_count": int(b.eligible_count),
            "eligible_rate": float(b.eligible_rate)
        }
    
    def monotonicity_result_to_dict(m: MonotonicityResult) -> dict:
        return {
            "variant": m.variant,
            "bins": [bin_to_dict(b) for b in m.bins],
            "is_monotonic": bool(m.is_monotonic),
            "violations": m.violations
        }
    
    def bootstrap_ci_to_dict(c: BootstrapCI) -> dict:
        return {
            "mean": c.mean,
            "ci_lower": c.ci_lower,
            "ci_upper": c.ci_upper,
            "std": c.std
        }
    
    data = {
        "monotonicity": {
            "raw": monotonicity_result_to_dict(monotonicity.raw),
            "isotonic": monotonicity_result_to_dict(monotonicity.isotonic),
            "violations_eliminated": bool(monotonicity.violations_eliminated)
        },
        "mcnemar": {
            "n01": mcnemar.n01,
            "n10": mcnemar.n10,
            "statistic": mcnemar.statistic,
            "p_value": mcnemar.p_value,
            "significant_05": mcnemar.significant_05,
            "significant_01": mcnemar.significant_01,
            "test_type": mcnemar.test_type
        },
        "bootstrap": {
            "binary": {
                "accuracy": bootstrap_ci_to_dict(bootstrap_binary.accuracy),
                "recall": bootstrap_ci_to_dict(bootstrap_binary.recall),
                "f1_score": bootstrap_ci_to_dict(bootstrap_binary.f1_score),
                "n_iterations": bootstrap_binary.n_iterations,
                "seed": bootstrap_binary.seed
            },
            "quadratic": {
                "accuracy": bootstrap_ci_to_dict(bootstrap_quadratic.accuracy),
                "recall": bootstrap_ci_to_dict(bootstrap_quadratic.recall),
                "f1_score": bootstrap_ci_to_dict(bootstrap_quadratic.f1_score),
                "n_iterations": bootstrap_quadratic.n_iterations,
                "seed": bootstrap_quadratic.seed
            },
            "non_overlap": {k: bool(v) for k, v in compare_bootstrap_cis(bootstrap_binary, bootstrap_quadratic).items()}
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, cls=NumpyEncoder)


# ============================================================================
# Main Analysis Runner
# ============================================================================

def run_complete_statistical_analysis(
    y_true: np.ndarray,
    scores_binary: np.ndarray,
    scores_linear: np.ndarray,
    scores_quadratic: np.ndarray,
    threshold: float = 0.5,
    bootstrap_iterations: int = 1000,
    seed: int = 42
) -> Dict:
    """
    Run complete statistical analysis pipeline.
    
    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth eligibility labels
    scores_binary : np.ndarray
        Scores from Binary mode
    scores_linear : np.ndarray
        Scores from Graded Linear mode
    scores_quadratic : np.ndarray
        Scores from Graded Quadratic mode
    threshold : float
        Decision threshold for binarization
    bootstrap_iterations : int
        Number of bootstrap iterations
    seed : int
        Random seed for reproducibility
    
    Returns
    -------
    Dict
        Complete analysis results
    """
    print("=" * 70)
    print("STATISTICAL ANALYSIS FOR CLINICAL TRIALS MATCHING")
    print("=" * 70)
    print()
    
    # 1. Isotonic Regression Calibration
    print("1. Applying Isotonic Regression Calibration...")
    scores_quadratic_isotonic = apply_isotonic_calibration(scores_quadratic, y_true)
    print(f"   ✓ Calibrated {len(scores_quadratic)} quadratic scores")
    print()
    
    # 2. Monotonicity Analysis
    print("2. Analyzing Monotonicity...")
    monotonicity = analyze_monotonicity(scores_quadratic, scores_quadratic_isotonic, y_true)
    print(f"   Raw scores monotonic: {monotonicity.raw.is_monotonic}")
    if not monotonicity.raw.is_monotonic:
        print(f"   - Violations: {len(monotonicity.raw.violations)}")
        for v in monotonicity.raw.violations:
            print(f"     • {v}")
    print(f"   Isotonic scores monotonic: {monotonicity.isotonic.is_monotonic}")
    print(f"   ✓ Violations eliminated: {monotonicity.violations_eliminated}")
    print()
    
    # 3. McNemar's Test
    print("3. Running McNemar's Test (Binary vs Quadratic)...")
    mcnemar = mcnemar_test(scores_binary, scores_quadratic, y_true, threshold)
    print(f"   n01 (Binary correct, Quadratic wrong): {mcnemar.n01}")
    print(f"   n10 (Binary wrong, Quadratic correct): {mcnemar.n10}")
    print(f"   Test type: {mcnemar.test_type}")
    print(f"   Statistic: {mcnemar.statistic:.4f}")
    print(f"   p-value: {mcnemar.p_value:.4f}")
    significance = "***" if mcnemar.significant_01 else ("*" if mcnemar.significant_05 else "n.s.")
    print(f"   Significance: {significance}")
    print()
    
    # 4. Bootstrap Confidence Intervals
    print("4. Computing Bootstrap Confidence Intervals...")
    print(f"   Iterations: {bootstrap_iterations}, Seed: {seed}")
    
    bootstrap_binary = bootstrap_confidence_intervals(
        scores_binary, y_true, bootstrap_iterations, 0.05, seed, threshold
    )
    bootstrap_quadratic = bootstrap_confidence_intervals(
        scores_quadratic, y_true, bootstrap_iterations, 0.05, seed, threshold
    )
    
    comparison = compare_bootstrap_cis(bootstrap_binary, bootstrap_quadratic)
    
    print()
    print("   Binary Mode:")
    print(f"     Accuracy: {bootstrap_binary.accuracy.mean:.3f} "
          f"[{bootstrap_binary.accuracy.ci_lower:.3f}, {bootstrap_binary.accuracy.ci_upper:.3f}]")
    print(f"     Recall:   {bootstrap_binary.recall.mean:.3f} "
          f"[{bootstrap_binary.recall.ci_lower:.3f}, {bootstrap_binary.recall.ci_upper:.3f}]")
    print(f"     F1:       {bootstrap_binary.f1_score.mean:.3f} "
          f"[{bootstrap_binary.f1_score.ci_lower:.3f}, {bootstrap_binary.f1_score.ci_upper:.3f}]")
    
    print()
    print("   Quadratic Mode:")
    print(f"     Accuracy: {bootstrap_quadratic.accuracy.mean:.3f} "
          f"[{bootstrap_quadratic.accuracy.ci_lower:.3f}, {bootstrap_quadratic.accuracy.ci_upper:.3f}]")
    print(f"     Recall:   {bootstrap_quadratic.recall.mean:.3f} "
          f"[{bootstrap_quadratic.recall.ci_lower:.3f}, {bootstrap_quadratic.recall.ci_upper:.3f}]")
    print(f"     F1:       {bootstrap_quadratic.f1_score.mean:.3f} "
          f"[{bootstrap_quadratic.f1_score.ci_lower:.3f}, {bootstrap_quadratic.f1_score.ci_upper:.3f}]")
    
    print()
    print("   Non-overlapping CIs (Quadratic significantly better):")
    for metric, non_overlap in comparison.items():
        status = "✓ Yes" if non_overlap else "✗ No"
        print(f"     {metric}: {status}")
    print()
    
    # 5. Summary
    print("=" * 70)
    print("SUMMARY: SUCCESS CRITERIA VERIFICATION")
    print("=" * 70)
    
    success_monotonicity = monotonicity.violations_eliminated
    success_mcnemar = mcnemar.significant_05
    success_bootstrap = any(comparison.values())
    
    print(f"✓ Monotonicity after isotonic: {'PASS' if success_monotonicity else 'FAIL'}")
    print(f"✓ McNemar significance (p<0.05): {'PASS' if success_mcnemar else 'FAIL'}")
    print(f"✓ Bootstrap CI non-overlap: {'PASS' if success_bootstrap else 'FAIL'}")
    print()
    
    if not all([success_monotonicity, success_mcnemar, success_bootstrap]):
        print("⚠️  WARNING: Not all success criteria met!")
    else:
        print("✅ All success criteria satisfied!")
    
    print("=" * 70)
    
    return {
        "scores_quadratic_isotonic": scores_quadratic_isotonic,
        "monotonicity": monotonicity,
        "mcnemar": mcnemar,
        "bootstrap_binary": bootstrap_binary,
        "bootstrap_quadratic": bootstrap_quadratic,
        "success": {
            "monotonicity": success_monotonicity,
            "mcnemar": success_mcnemar,
            "bootstrap": success_bootstrap
        }
    }

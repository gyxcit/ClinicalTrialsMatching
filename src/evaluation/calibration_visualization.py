"""
Calibration Visualization Module for Workshop Submission

Implements:
1. Reliability Diagrams (publication-ready)
2. Expected Calibration Error (ECE)
3. Brier Score
4. Temperature Scaling (post-hoc)

Target: ML4H @ NeurIPS, CHIL, MLHC workshops

Author: Workshop Analysis Framework
Date: 2026-02-09
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import csv
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CalibrationBin:
    """Statistics for a single calibration bin"""
    bin_idx: int
    bin_lower: float
    bin_upper: float
    count: int
    mean_score: float  # Average predicted probability (confidence)
    mean_outcome: float  # Empirical accuracy (true positive rate)
    

@dataclass  
class CalibrationMetrics:
    """Complete calibration metrics for one scoring method"""
    method_name: str
    ece: float
    brier_score: float
    bins: List[CalibrationBin]
    n_samples: int


# ============================================================================
# Core Calibration Functions
# ============================================================================

def compute_calibration_bins(
    scores: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10
) -> List[CalibrationBin]:
    """
    Compute calibration statistics per bin.
    
    Parameters
    ----------
    scores : np.ndarray
        Predicted probabilities in [0, 1]
    y_true : np.ndarray
        Ground truth labels (0 or 1)
    n_bins : int
        Number of uniform bins (default 10)
    
    Returns
    -------
    List[CalibrationBin]
        Calibration statistics for each bin
    """
    scores = np.asarray(scores, dtype=np.float64)
    y_true = np.asarray(y_true, dtype=np.float64)
    
    bins = []
    bin_edges = np.linspace(0, 1, n_bins + 1)
    
    for i in range(n_bins):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]
        
        # Find samples in this bin
        if i == n_bins - 1:  # Last bin includes upper bound
            mask = (scores >= lower) & (scores <= upper)
        else:
            mask = (scores >= lower) & (scores < upper)
        
        count = np.sum(mask)
        
        if count > 0:
            mean_score = float(np.mean(scores[mask]))
            mean_outcome = float(np.mean(y_true[mask]))
        else:
            mean_score = (lower + upper) / 2
            mean_outcome = 0.0
        
        bins.append(CalibrationBin(
            bin_idx=i,
            bin_lower=lower,
            bin_upper=upper,
            count=int(count),
            mean_score=mean_score,
            mean_outcome=mean_outcome
        ))
    
    return bins


def compute_ece(
    scores: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10
) -> float:
    """
    Compute Expected Calibration Error.
    
    ECE = Σ_k (|B_k| / N) · |acc(B_k) − conf(B_k)|
    
    Parameters
    ----------
    scores : np.ndarray
        Predicted probabilities in [0, 1]
    y_true : np.ndarray
        Ground truth labels (0 or 1)
    n_bins : int
        Number of uniform bins (default 10)
    
    Returns
    -------
    float
        Expected Calibration Error
    """
    bins = compute_calibration_bins(scores, y_true, n_bins)
    n_samples = len(scores)
    
    ece = 0.0
    for b in bins:
        if b.count > 0:
            weight = b.count / n_samples
            calibration_error = abs(b.mean_outcome - b.mean_score)
            ece += weight * calibration_error
    
    return float(ece)


def compute_brier_score(
    scores: np.ndarray,
    y_true: np.ndarray
) -> float:
    """
    Compute Brier Score.
    
    Brier = (1/N) Σ (p_i - y_i)²
    
    Parameters
    ----------
    scores : np.ndarray
        Predicted probabilities in [0, 1]
    y_true : np.ndarray
        Ground truth labels (0 or 1)
    
    Returns
    -------
    float
        Brier Score (lower is better)
    """
    scores = np.asarray(scores, dtype=np.float64)
    y_true = np.asarray(y_true, dtype=np.float64)
    
    return float(np.mean((scores - y_true) ** 2))


# ============================================================================
# Temperature Scaling
# ============================================================================

def _logit(p: np.ndarray, eps: float = 1e-7) -> np.ndarray:
    """Safe logit transform"""
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid function"""
    return 1 / (1 + np.exp(-x))


def apply_temperature_scaling(
    scores: np.ndarray,
    temperature: float
) -> np.ndarray:
    """
    Apply temperature scaling to probabilities.
    
    p_scaled = sigmoid(logit(p) / T)
    
    Parameters
    ----------
    scores : np.ndarray
        Original predicted probabilities
    temperature : float
        Temperature parameter (T > 1 softens, T < 1 sharpens)
    
    Returns
    -------
    np.ndarray
        Scaled probabilities
    """
    scores = np.asarray(scores, dtype=np.float64)
    logits = _logit(scores)
    scaled_logits = logits / temperature
    return _sigmoid(scaled_logits)


def optimize_temperature(
    scores: np.ndarray,
    y_true: np.ndarray,
    method: str = "ece"
) -> float:
    """
    Find optimal temperature to minimize calibration error.
    
    Parameters
    ----------
    scores : np.ndarray
        Predicted probabilities
    y_true : np.ndarray
        Ground truth labels
    method : str
        Optimization target: "ece" or "brier"
    
    Returns
    -------
    float
        Optimal temperature
    """
    scores = np.asarray(scores, dtype=np.float64)
    y_true = np.asarray(y_true, dtype=np.float64)
    
    def objective(T):
        if T <= 0:
            return float('inf')
        scaled = apply_temperature_scaling(scores, T)
        if method == "ece":
            return compute_ece(scaled, y_true)
        else:
            return compute_brier_score(scaled, y_true)
    
    result = minimize_scalar(objective, bounds=(0.1, 10.0), method='bounded')
    return float(result.x)


# ============================================================================
# Reliability Diagram Visualization
# ============================================================================

def reliability_diagram(
    scores: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10,
    title: str = "Reliability Diagram",
    filename: str = None,
    figsize: Tuple[int, int] = (6, 5),
    show_gap: bool = True,
    show_histogram: bool = True
) -> Dict:
    """
    Generate a publication-ready reliability diagram.
    
    Parameters
    ----------
    scores : np.ndarray
        Predicted probabilities in [0, 1]
    y_true : np.ndarray
        Ground truth labels (0 or 1)
    n_bins : int
        Number of uniform bins (default 10)
    title : str
        Plot title
    filename : str, optional
        If provided, save figure to this path
    figsize : Tuple[int, int]
        Figure size in inches
    show_gap : bool
        Show calibration gap bars
    show_histogram : bool
        Show sample count histogram below main plot
    
    Returns
    -------
    Dict
        Dictionary with bins, ECE, and Brier score
    """
    bins = compute_calibration_bins(scores, y_true, n_bins)
    ece = compute_ece(scores, y_true, n_bins)
    brier = compute_brier_score(scores, y_true)
    
    # Extract data for plotting
    bin_centers = np.array([(b.bin_lower + b.bin_upper) / 2 for b in bins])
    mean_scores = np.array([b.mean_score for b in bins])
    mean_outcomes = np.array([b.mean_outcome for b in bins])
    counts = np.array([b.count for b in bins])
    
    # Create figure
    if show_histogram:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, 
                                        gridspec_kw={'height_ratios': [3, 1]},
                                        sharex=True)
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=figsize)
    
    # Main reliability plot
    bar_width = 0.8 / n_bins
    
    # Perfect calibration line
    ax1.plot([0, 1], [0, 1], 'k--', linewidth=1.5, label='Perfect calibration', alpha=0.7)
    
    # Bar chart for mean outcomes
    mask = counts > 0
    ax1.bar(mean_scores[mask], mean_outcomes[mask], width=bar_width, 
            alpha=0.7, color='#2196F3', edgecolor='black', linewidth=0.5,
            label='Outputs')
    
    # Calibration gaps
    if show_gap:
        for i in range(n_bins):
            if counts[i] > 0:
                gap_color = '#F44336' if mean_outcomes[i] < mean_scores[i] else '#4CAF50'
                ax1.plot([mean_scores[i], mean_scores[i]], 
                        [mean_scores[i], mean_outcomes[i]],
                        color=gap_color, linewidth=2, alpha=0.8)
    
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.set_ylabel('Fraction of Positives', fontsize=11)
    ax1.set_title(f'{title}\nECE = {ece:.4f}, Brier = {brier:.4f}', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Histogram below
    if show_histogram:
        ax2.bar(bin_centers, counts, width=1/n_bins * 0.8, 
                color='#9E9E9E', edgecolor='black', linewidth=0.5, alpha=0.7)
        ax2.set_xlabel('Mean Predicted Probability', fontsize=11)
        ax2.set_ylabel('Count', fontsize=10)
        ax2.set_xlim(0, 1)
        ax2.grid(True, alpha=0.3, axis='y')
    else:
        ax1.set_xlabel('Mean Predicted Probability', fontsize=11)
    
    plt.tight_layout()
    
    # Save figure
    if filename:
        plt.savefig(filename, dpi=300, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        print(f"   ✓ Saved: {filename}")
    
    plt.close(fig)
    
    return {
        "bins": bins,
        "ece": ece,
        "brier_score": brier,
        "n_samples": len(scores)
    }


# ============================================================================
# Export Functions
# ============================================================================

def export_calibration_metrics_csv(
    metrics_list: List[CalibrationMetrics],
    filename: str
) -> None:
    """Export calibration metrics to CSV."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['method', 'ece', 'brier_score', 'n_samples'])
        for m in metrics_list:
            writer.writerow([m.method_name, m.ece, m.brier_score, m.n_samples])


def export_calibration_metrics_latex(
    metrics_list: List[CalibrationMetrics],
    filename: str = None
) -> str:
    """Export calibration metrics as LaTeX table."""
    
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Calibration Metrics Comparison}",
        r"\label{tab:calibration}",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Method & ECE $\downarrow$ & Brier $\downarrow$ \\",
        r"\midrule",
    ]
    
    for m in metrics_list:
        lines.append(f"{m.method_name} & {m.ece:.4f} & {m.brier_score:.4f} \\\\")
    
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


def export_workshop_results_json(
    metrics_list: List[CalibrationMetrics],
    temperature: float,
    filename: str
) -> None:
    """Export complete workshop analysis results to JSON."""
    
    data = {
        "calibration_metrics": [
            {
                "method": m.method_name,
                "ece": m.ece,
                "brier_score": m.brier_score,
                "n_samples": m.n_samples,
                "bins": [
                    {
                        "bin_idx": b.bin_idx,
                        "bin_lower": b.bin_lower,
                        "bin_upper": b.bin_upper,
                        "count": b.count,
                        "mean_score": b.mean_score,
                        "mean_outcome": b.mean_outcome
                    }
                    for b in m.bins
                ]
            }
            for m in metrics_list
        ],
        "optimal_temperature": temperature
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# Main Analysis Function
# ============================================================================

def run_calibration_analysis(
    scores_binary: np.ndarray,
    scores_quadratic: np.ndarray,
    scores_quadratic_isotonic: np.ndarray,
    y_true: np.ndarray,
    output_dir: str = ".",
    n_bins: int = 10
) -> Dict:
    """
    Run complete calibration analysis for workshop submission.
    
    Parameters
    ----------
    scores_binary : np.ndarray
        Binary scoring predictions
    scores_quadratic : np.ndarray
        Quadratic raw scoring predictions
    scores_quadratic_isotonic : np.ndarray
        Quadratic scores after isotonic calibration
    y_true : np.ndarray
        Ground truth labels
    output_dir : str
        Directory for output files
    n_bins : int
        Number of bins for reliability diagrams
    
    Returns
    -------
    Dict
        Complete analysis results
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 70)
    print("WORKSHOP CALIBRATION ANALYSIS")
    print("=" * 70)
    print()
    
    metrics_list = []
    
    # 1. Binary scoring
    print("1. Analyzing Binary Scoring...")
    result_binary = reliability_diagram(
        scores_binary, y_true, n_bins=n_bins,
        title="Binary Scoring",
        filename=os.path.join(output_dir, "reliability_diagram_binary.png")
    )
    metrics_list.append(CalibrationMetrics(
        method_name="Binary",
        ece=result_binary["ece"],
        brier_score=result_binary["brier_score"],
        bins=result_binary["bins"],
        n_samples=result_binary["n_samples"]
    ))
    print(f"   ECE: {result_binary['ece']:.4f}, Brier: {result_binary['brier_score']:.4f}")
    print()
    
    # 2. Quadratic raw scoring
    print("2. Analyzing Quadratic Raw Scoring...")
    result_quad_raw = reliability_diagram(
        scores_quadratic, y_true, n_bins=n_bins,
        title="Graded Quadratic (Raw)",
        filename=os.path.join(output_dir, "reliability_diagram_quadratic_raw.png")
    )
    metrics_list.append(CalibrationMetrics(
        method_name="Quadratic (Raw)",
        ece=result_quad_raw["ece"],
        brier_score=result_quad_raw["brier_score"],
        bins=result_quad_raw["bins"],
        n_samples=result_quad_raw["n_samples"]
    ))
    print(f"   ECE: {result_quad_raw['ece']:.4f}, Brier: {result_quad_raw['brier_score']:.4f}")
    print()
    
    # 3. Quadratic isotonic scoring
    print("3. Analyzing Quadratic Isotonic Scoring...")
    result_quad_iso = reliability_diagram(
        scores_quadratic_isotonic, y_true, n_bins=n_bins,
        title="Graded Quadratic (Isotonic)",
        filename=os.path.join(output_dir, "reliability_diagram_quadratic_isotonic.png")
    )
    metrics_list.append(CalibrationMetrics(
        method_name="Quadratic (Isotonic)",
        ece=result_quad_iso["ece"],
        brier_score=result_quad_iso["brier_score"],
        bins=result_quad_iso["bins"],
        n_samples=result_quad_iso["n_samples"]
    ))
    print(f"   ECE: {result_quad_iso['ece']:.4f}, Brier: {result_quad_iso['brier_score']:.4f}")
    print()
    
    # 4. Temperature scaling for Binary
    print("4. Optimizing Temperature Scaling for Binary...")
    optimal_temp = optimize_temperature(scores_binary, y_true, method="ece")
    scores_binary_scaled = apply_temperature_scaling(scores_binary, optimal_temp)
    print(f"   Optimal Temperature: T = {optimal_temp:.4f}")
    
    result_binary_ts = reliability_diagram(
        scores_binary_scaled, y_true, n_bins=n_bins,
        title=f"Binary + Temp Scaling (T={optimal_temp:.2f})",
        filename=os.path.join(output_dir, "reliability_diagram_binary_tempscaled.png")
    )
    metrics_list.append(CalibrationMetrics(
        method_name=f"Binary (T={optimal_temp:.2f})",
        ece=result_binary_ts["ece"],
        brier_score=result_binary_ts["brier_score"],
        bins=result_binary_ts["bins"],
        n_samples=result_binary_ts["n_samples"]
    ))
    print(f"   ECE after scaling: {result_binary_ts['ece']:.4f}")
    print(f"   Brier after scaling: {result_binary_ts['brier_score']:.4f}")
    print()
    
    # Export results
    print("5. Exporting Results...")
    
    csv_path = os.path.join(output_dir, "calibration_metrics.csv")
    export_calibration_metrics_csv(metrics_list, csv_path)
    print(f"   ✓ CSV: {csv_path}")
    
    latex_path = os.path.join(output_dir, "calibration_metrics_latex.txt")
    export_calibration_metrics_latex(metrics_list, latex_path)
    print(f"   ✓ LaTeX: {latex_path}")
    
    json_path = os.path.join(output_dir, "workshop_analysis_results.json")
    export_workshop_results_json(metrics_list, optimal_temp, json_path)
    print(f"   ✓ JSON: {json_path}")
    print()
    
    # Summary
    print("=" * 70)
    print("CALIBRATION SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Method':<25} {'ECE':>10} {'Brier':>10}")
    print("-" * 50)
    for m in metrics_list:
        print(f"{m.method_name:<25} {m.ece:>10.4f} {m.brier_score:>10.4f}")
    print()
    
    # Verify expected ordering
    ece_binary = result_binary["ece"]
    ece_quad_raw = result_quad_raw["ece"]
    ece_quad_iso = result_quad_iso["ece"]
    
    print("ECE Ordering Check:")
    if ece_binary > ece_quad_raw:
        print("   ✓ Binary > Quadratic Raw")
    else:
        print("   ⚠️ Binary <= Quadratic Raw (unexpected)")
    
    if ece_quad_raw > ece_quad_iso:
        print("   ✓ Quadratic Raw > Quadratic Isotonic")
    else:
        print("   ⚠️ Quadratic Raw <= Quadratic Isotonic (unexpected)")
    
    print("=" * 70)
    
    return {
        "metrics": metrics_list,
        "optimal_temperature": optimal_temp,
        "ece_ordering_correct": ece_binary > ece_quad_raw > ece_quad_iso
    }

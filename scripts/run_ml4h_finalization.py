#!/usr/bin/env python
"""
ML4H Finalization Script

Generates publication-ready outputs for ML4H @ NeurIPS workshop:
1. Consolidated performance table (all methods, all metrics)
2. Score distribution figure (Binary vs Quadratic by ground truth)
3. Bootstrap CIs for ECE and Brier score

Usage:
    python scripts/run_ml4h_finalization.py
"""

import sys
import os
import json
import csv
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.ablation_runner import generate_test_dataset, run_ablation
from src.evaluation.statistical_analysis import apply_isotonic_calibration
from src.evaluation.calibration_visualization import (
    compute_ece, compute_brier_score, apply_temperature_scaling, optimize_temperature
)


# ============================================================================
# Performance Metrics
# ============================================================================

def compute_classification_metrics(scores, y_true, threshold=0.5):
    """Compute accuracy, precision, recall, F1."""
    pred = np.asarray(scores) >= threshold
    y_true = np.asarray(y_true, dtype=bool)
    
    tp = np.sum(pred & y_true)
    fp = np.sum(pred & ~y_true)
    fn = np.sum(~pred & y_true)
    tn = np.sum(~pred & ~y_true)
    
    accuracy = (tp + tn) / len(y_true)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "accuracy": round(accuracy, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3)
    }


def compute_all_metrics(scores, y_true, method_name, threshold=0.5):
    """Compute all metrics for a method."""
    clf_metrics = compute_classification_metrics(scores, y_true, threshold)
    ece = round(compute_ece(scores, y_true), 3)
    brier = round(compute_brier_score(scores, y_true), 3)
    
    return {
        "method": method_name,
        **clf_metrics,
        "ece": ece,
        "brier": brier
    }


# ============================================================================
# Bootstrap CIs for ECE and Brier
# ============================================================================

def bootstrap_calibration_ci(scores, y_true, n_iterations=1000, alpha=0.05, seed=42):
    """Bootstrap CI for ECE and Brier score."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    
    eces = np.zeros(n_iterations)
    briers = np.zeros(n_iterations)
    
    for i in range(n_iterations):
        idx = rng.choice(n, size=n, replace=True)
        eces[i] = compute_ece(scores[idx], y_true[idx])
        briers[i] = compute_brier_score(scores[idx], y_true[idx])
    
    lower = alpha / 2 * 100
    upper = (1 - alpha / 2) * 100
    
    return {
        "ece_mean": round(np.mean(eces), 4),
        "ece_ci_lower": round(np.percentile(eces, lower), 4),
        "ece_ci_upper": round(np.percentile(eces, upper), 4),
        "brier_mean": round(np.mean(briers), 4),
        "brier_ci_lower": round(np.percentile(briers, lower), 4),
        "brier_ci_upper": round(np.percentile(briers, upper), 4)
    }


# ============================================================================
# Score Distribution Visualization
# ============================================================================

def plot_score_distribution(scores_binary, scores_quadratic, y_true, filename):
    """Create violin plots comparing score distributions by ground truth."""
    y_true = np.asarray(y_true, dtype=bool)
    
    fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    
    # Prepare data
    binary_eligible = scores_binary[y_true]
    binary_ineligible = scores_binary[~y_true]
    quad_eligible = scores_quadratic[y_true]
    quad_ineligible = scores_quadratic[~y_true]
    
    # Binary plot
    ax = axes[0]
    parts = ax.violinplot([binary_ineligible, binary_eligible], positions=[0, 1], 
                          showmeans=True, showmedians=True)
    for pc in parts['bodies']:
        pc.set_facecolor('#F44336')
        pc.set_alpha(0.7)
    parts['cmeans'].set_color('black')
    parts['cmedians'].set_color('white')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Ineligible', 'Eligible'])
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Binary Scoring', fontsize=13, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='threshold')
    
    # Quadratic plot
    ax = axes[1]
    parts = ax.violinplot([quad_ineligible, quad_eligible], positions=[0, 1],
                          showmeans=True, showmedians=True)
    for pc in parts['bodies']:
        pc.set_facecolor('#2196F3')
        pc.set_alpha(0.7)
    parts['cmeans'].set_color('black')
    parts['cmedians'].set_color('white')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Ineligible', 'Eligible'])
    ax.set_title('Graded Quadratic Scoring', fontsize=13, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
    
    plt.suptitle('Score Distribution by Ground Truth', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✓ Saved: {filename}")


# ============================================================================
# Export Functions
# ============================================================================

def export_performance_table_csv(metrics_list, filename):
    """Export performance metrics to CSV."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['method', 'accuracy', 'precision', 'recall', 'f1', 'ece', 'brier'])
        writer.writeheader()
        writer.writerows(metrics_list)
    print(f"   ✓ Saved: {filename}")


def export_performance_table_latex(metrics_list, filename):
    """Export performance metrics as LaTeX table."""
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Performance Comparison on Synthetic Dataset (N=1000)}",
        r"\label{tab:performance}",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"Method & Acc & Prec & Recall & F1 & ECE$\downarrow$ & Brier$\downarrow$ \\",
        r"\midrule",
    ]
    
    for m in metrics_list:
        lines.append(
            f"{m['method']} & {m['accuracy']:.3f} & {m['precision']:.3f} & "
            f"{m['recall']:.3f} & {m['f1']:.3f} & {m['ece']:.3f} & {m['brier']:.3f} \\\\"
        )
    
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"   ✓ Saved: {filename}")


def export_bootstrap_ci_latex(ci_binary, ci_quadratic, filename):
    """Export bootstrap CIs as LaTeX."""
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Bootstrap 95\% CI for Calibration Metrics (N=1000, B=1000)}",
        r"\label{tab:bootstrap_calibration}",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Method & ECE [95\% CI] & Brier [95\% CI] \\",
        r"\midrule",
        f"Binary & {ci_binary['ece_mean']:.3f} [{ci_binary['ece_ci_lower']:.3f}, {ci_binary['ece_ci_upper']:.3f}] "
        f"& {ci_binary['brier_mean']:.3f} [{ci_binary['brier_ci_lower']:.3f}, {ci_binary['brier_ci_upper']:.3f}] \\\\",
        f"Quadratic & {ci_quadratic['ece_mean']:.3f} [{ci_quadratic['ece_ci_lower']:.3f}, {ci_quadratic['ece_ci_upper']:.3f}] "
        f"& {ci_quadratic['brier_mean']:.3f} [{ci_quadratic['brier_ci_lower']:.3f}, {ci_quadratic['brier_ci_upper']:.3f}] \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"   ✓ Saved: {filename}")


# ============================================================================
# Main
# ============================================================================

def main():
    # Ensure output directories exist
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(root, "results", "figures"), exist_ok=True)
    os.makedirs(os.path.join(root, "results", "tables"), exist_ok=True)
    os.makedirs(os.path.join(root, "results", "json"), exist_ok=True)

    print()
    print("=" * 70)
    print("ML4H FINALIZATION")
    print("=" * 70)
    print()
    
    # Generate data
    print("1. Loading synthetic dataset (N=1000, seed=42)...")
    dataset = generate_test_dataset(n_cases=1000, seed=42)
    results = run_ablation(dataset)
    
    y_true = np.array([case.ground_truth for case in dataset])
    scores_binary = np.array(results["binary"].scores)
    scores_linear = np.array(results["graded_linear"].scores)
    scores_quadratic = np.array(results["graded_quadratic"].scores)
    print(f"   ✓ {len(y_true)} cases loaded")
    print()
    
    # Temperature scaling for Binary
    print("2. Optimizing temperature scaling for Binary...")
    optimal_temp = optimize_temperature(scores_binary, y_true)
    scores_binary_ts = apply_temperature_scaling(scores_binary, optimal_temp)
    print(f"   ✓ Optimal T = {optimal_temp:.2f}")
    print()
    
    # Compute all metrics
    print("3. Computing performance metrics...")
    metrics_list = [
        compute_all_metrics(scores_binary, y_true, "Binary"),
        compute_all_metrics(scores_linear, y_true, "Graded Linear"),
        compute_all_metrics(scores_quadratic, y_true, "Graded Quadratic"),
        compute_all_metrics(scores_binary_ts, y_true, f"Binary + TempScale (T={optimal_temp:.1f})"),
    ]
    
    for m in metrics_list:
        print(f"   {m['method']}: Acc={m['accuracy']}, F1={m['f1']}, ECE={m['ece']}, Brier={m['brier']}")
    print()
    
    # Export performance table
    print("4. Exporting performance table...")
    export_performance_table_csv(metrics_list, os.path.join(root, "results", "tables", "performance_table.csv"))
    export_performance_table_latex(metrics_list, os.path.join(root, "results", "tables", "performance_table_latex.txt"))
    print()
    
    # Score distribution figure
    print("5. Generating score distribution figure...")
    plot_score_distribution(scores_binary, scores_quadratic, y_true, 
                           os.path.join(root, "results", "figures", "score_distribution_binary_vs_quadratic.png"))
    print()
    
    # Bootstrap CIs for ECE and Brier
    print("6. Computing bootstrap CIs for calibration metrics...")
    print("   (1000 iterations, seed=42)")
    ci_binary = bootstrap_calibration_ci(scores_binary, y_true)
    ci_quadratic = bootstrap_calibration_ci(scores_quadratic, y_true)
    
    print(f"   Binary - ECE: {ci_binary['ece_mean']:.3f} [{ci_binary['ece_ci_lower']:.3f}, {ci_binary['ece_ci_upper']:.3f}]")
    print(f"   Binary - Brier: {ci_binary['brier_mean']:.3f} [{ci_binary['brier_ci_lower']:.3f}, {ci_binary['brier_ci_upper']:.3f}]")
    print(f"   Quadratic - ECE: {ci_quadratic['ece_mean']:.3f} [{ci_quadratic['ece_ci_lower']:.3f}, {ci_quadratic['ece_ci_upper']:.3f}]")
    print(f"   Quadratic - Brier: {ci_quadratic['brier_mean']:.3f} [{ci_quadratic['brier_ci_lower']:.3f}, {ci_quadratic['brier_ci_upper']:.3f}]")
    
    export_bootstrap_ci_latex(ci_binary, ci_quadratic, os.path.join(root, "results", "tables", "bootstrap_calibration_ci_latex.txt"))
    print()
    
    # Save JSON summary
    print("7. Saving JSON summary...")
    summary = {
        "performance_metrics": metrics_list,
        "bootstrap_ci": {
            "binary": ci_binary,
            "quadratic": ci_quadratic
        },
        "optimal_temperature": optimal_temp,
        "n_cases": 1000,
        "seed": 42
    }
    json_path = os.path.join(root, "results", "json", "ml4h_finalization_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"   ✓ Saved: {json_path}")
    print()
    
    print("=" * 70)
    print("ML4H FINALIZATION COMPLETE")
    print("=" * 70)
    print()
    print("Generated files in results/:")
    print("  • tables/performance_table.csv")
    print("  • tables/performance_table_latex.txt")
    print("  • figures/score_distribution_binary_vs_quadratic.png")
    print("  • tables/bootstrap_calibration_ci_latex.txt")
    print("  • json/ml4h_finalization_results.json")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

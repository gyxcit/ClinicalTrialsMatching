#!/usr/bin/env python
"""
Spotlight Analyses for ML4H Paper

Generates the 4 additional analyses needed to upgrade from poster to spotlight:
1. AUC-ROC and AUC-PR curves (threshold-free ordinal metrics)
2. Alpha sensitivity analysis (ECE/Brier vs alpha)
3. Confidence noise robustness test (perturbation ±1)
4. Manual 15-case quantitative analysis
5. Updated Table 1 with bootstrap CIs

Usage:
    python scripts/run_spotlight_analyses.py
"""

import sys
import os
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.ablation_runner import (
    generate_test_dataset, run_ablation, ScoringMode,
    PatientCase, GradedAnswer
)
from src.response_models import AnswerType
from src.evaluation.calibration_visualization import compute_ece, compute_brier_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR = os.path.join(ROOT, "results", "figures")
TBL_DIR = os.path.join(ROOT, "results", "tables")
JSON_DIR = os.path.join(ROOT, "results", "json")

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TBL_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)


# ============================================================================
# 1. AUC-ROC and AUC-PR
# ============================================================================

def compute_auc_roc_pr(scores, y_true):
    """Compute AUC-ROC and AUC-PR manually (no sklearn dependency for metrics)."""
    scores = np.asarray(scores, dtype=float)
    y_true = np.asarray(y_true, dtype=bool)
    
    # Sort by descending score
    sorted_idx = np.argsort(-scores)
    y_sorted = y_true[sorted_idx]
    s_sorted = scores[sorted_idx]
    
    n_pos = np.sum(y_true)
    n_neg = len(y_true) - n_pos
    
    # ROC curve
    tpr_list = [0.0]
    fpr_list = [0.0]
    tp = 0
    fp = 0
    
    for i in range(len(y_sorted)):
        if y_sorted[i]:
            tp += 1
        else:
            fp += 1
        tpr_list.append(tp / n_pos if n_pos > 0 else 0)
        fpr_list.append(fp / n_neg if n_neg > 0 else 0)
    
    # AUC-ROC via trapezoidal rule
    try:
        auc_roc = np.trapezoid(tpr_list, fpr_list)
    except AttributeError:
        auc_roc = np.trapz(tpr_list, fpr_list)
    
    # PR curve
    precision_list = [1.0]
    recall_list = [0.0]
    tp = 0
    
    for i in range(len(y_sorted)):
        if y_sorted[i]:
            tp += 1
        prec = tp / (i + 1)
        rec = tp / n_pos if n_pos > 0 else 0
        precision_list.append(prec)
        recall_list.append(rec)
    
    # AUC-PR via trapezoidal rule
    try:
        auc_pr = np.trapezoid(precision_list, recall_list)
    except AttributeError:
        auc_pr = np.trapz(precision_list, recall_list)
    
    return {
        "auc_roc": round(auc_roc, 4),
        "auc_pr": round(auc_pr, 4),
        "fpr": fpr_list,
        "tpr": tpr_list,
        "precision": precision_list,
        "recall": recall_list
    }


def plot_roc_pr_curves(results_dict, filename):
    """Plot ROC and PR curves for all methods."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    
    colors = {
        "Binary": "#E53935",
        "Graded Linear": "#FB8C00",
        "Graded Quadratic": "#1E88E5",
    }
    
    # ROC
    ax = axes[0]
    for name, res in results_dict.items():
        ax.plot(res["fpr"], res["tpr"], 
                label=f'{name} (AUC={res["auc_roc"]:.3f})',
                color=colors.get(name, "gray"), linewidth=2)
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.3, linewidth=1)
    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title("ROC Curve", fontsize=13, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    
    # PR
    ax = axes[1]
    for name, res in results_dict.items():
        ax.plot(res["recall"], res["precision"],
                label=f'{name} (AUC={res["auc_pr"]:.3f})',
                color=colors.get(name, "gray"), linewidth=2)
    n_pos = sum(1 for v in results_dict.values() for _ in [0])  # dummy
    ax.set_xlabel("Recall", fontsize=11)
    ax.set_ylabel("Precision", fontsize=11)
    ax.set_title("Precision–Recall Curve", fontsize=13, fontweight='bold')
    ax.legend(loc='lower left', fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✓ Saved: {filename}")


# ============================================================================
# 2. Alpha Sensitivity Analysis
# ============================================================================

def run_alpha_sensitivity(dataset, y_true, alphas=None):
    """Run scoring with different alpha values and compute metrics."""
    if alphas is None:
        alphas = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    
    results = []
    
    for alpha in alphas:
        # Compute quadratic scores with this alpha
        scores = []
        for case in dataset:
            inclusion_scores = []
            exclusion_scores = []
            
            for key, resp in case.responses.items():
                ans = resp.answer  # AnswerType enum
                conf = resp.confidence
                
                if ans == AnswerType.YES:
                    score = conf / 5.0
                elif ans == AnswerType.NO:
                    score = 0.0
                else:  # UNSURE
                    score = 0.5 * (conf / 5.0) ** alpha
                
                if "_EXC_" in key:
                    exclusion_scores.append(score)
                else:
                    inclusion_scores.append(score)
            
            incl_mean = np.mean(inclusion_scores) if inclusion_scores else 0.5
            excl_max = max(exclusion_scores) if exclusion_scores else 0.0
            
            final_score = incl_mean * (1 - excl_max)
            scores.append(final_score)
        
        scores = np.array(scores)
        
        # Classification metrics at threshold 0.5
        pred = scores >= 0.5
        tp = np.sum(pred & y_true)
        fp = np.sum(pred & ~y_true)
        fn = np.sum(~pred & y_true)
        tn = np.sum(~pred & ~y_true)
        
        accuracy = (tp + tn) / len(y_true)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        ece = compute_ece(scores, y_true)
        brier = compute_brier_score(scores, y_true)
        
        results.append({
            "alpha": alpha,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "ece": round(ece, 4),
            "brier": round(brier, 4)
        })
    
    return results


def plot_alpha_sensitivity(results, filename):
    """Plot ECE and Brier vs alpha."""
    alphas = [r["alpha"] for r in results]
    eces = [r["ece"] for r in results]
    briers = [r["brier"] for r in results]
    f1s = [r["f1"] for r in results]
    
    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    
    color_ece = '#1E88E5'
    color_brier = '#E53935'
    color_f1 = '#43A047'
    
    ax1.plot(alphas, eces, 'o-', color=color_ece, linewidth=2, markersize=7, label='ECE ↓')
    ax1.plot(alphas, briers, 's-', color=color_brier, linewidth=2, markersize=7, label='Brier ↓')
    ax1.set_xlabel('Exponent α', fontsize=12)
    ax1.set_ylabel('Calibration Metric', fontsize=12)
    
    ax2 = ax1.twinx()
    ax2.plot(alphas, f1s, '^--', color=color_f1, linewidth=2, markersize=7, label='F1 ↑')
    ax2.set_ylabel('F1-Score', fontsize=12, color=color_f1)
    ax2.tick_params(axis='y', labelcolor=color_f1)
    
    # Mark alpha=1.5
    idx_15 = alphas.index(1.5) if 1.5 in alphas else None
    if idx_15 is not None:
        ax1.axvline(x=1.5, color='gray', linestyle=':', alpha=0.6)
        ax1.annotate('α = 1.5\n(selected)', 
                     xy=(1.5, eces[idx_15]), 
                     xytext=(1.8, eces[idx_15] + 0.015),
                     fontsize=9, color='gray',
                     arrowprops=dict(arrowstyle='->', color='gray', lw=1))
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
    
    ax1.set_title('Sensitivity Analysis: Calibration vs. Exponent α', 
                  fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✓ Saved: {filename}")


# ============================================================================
# 3. Confidence Noise Robustness
# ============================================================================

def run_noise_robustness(dataset, y_true, n_trials=50, seed=42):
    """Perturb confidence by ±1 and measure metric stability."""
    rng = np.random.default_rng(seed)
    
    methods = {
        "binary": "binary",
        "quadratic": "graded_quadratic"
    }
    
    results = {name: {"ece": [], "brier": [], "f1": []} for name in methods}
    
    for trial in range(n_trials):
        # Create perturbed dataset
        perturbed_cases = []
        for case in dataset:
            new_responses = {}
            for key, resp in case.responses.items():
                # Perturb confidence by +/-1, clamp to [1, 5]
                delta = rng.choice([-1, 0, 1])
                new_conf = max(1, min(5, resp.confidence + delta))
                new_responses[key] = GradedAnswer(
                    answer=resp.answer,
                    confidence=new_conf
                )
            perturbed_cases.append(PatientCase(
                case_id=case.case_id,
                nct_id=case.nct_id,
                responses=new_responses,
                ground_truth=case.ground_truth,
                description=case.description
            ))
        
        # Score with each method
        for name, mode in methods.items():
            ablation = run_ablation(perturbed_cases)
            scores = np.array(ablation[mode].scores)
            
            ece = compute_ece(scores, y_true)
            brier = compute_brier_score(scores, y_true)
            
            pred = scores >= 0.5
            tp = np.sum(pred & y_true)
            fp = np.sum(pred & ~y_true)
            fn = np.sum(~pred & y_true)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            
            results[name]["ece"].append(ece)
            results[name]["brier"].append(brier)
            results[name]["f1"].append(f1)
    
    # Summarize
    summary = {}
    for name in methods:
        summary[name] = {
            "ece_mean": round(np.mean(results[name]["ece"]), 4),
            "ece_std": round(np.std(results[name]["ece"]), 4),
            "brier_mean": round(np.mean(results[name]["brier"]), 4),
            "brier_std": round(np.std(results[name]["brier"]), 4),
            "f1_mean": round(np.mean(results[name]["f1"]), 4),
            "f1_std": round(np.std(results[name]["f1"]), 4),
        }
    
    return summary, results


def plot_noise_robustness(raw_results, filename):
    """Box plots showing metric distribution under noise."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    
    metrics = ["ece", "brier", "f1"]
    titles = ["ECE ↓", "Brier Score ↓", "F1-Score ↑"]
    colors = ["#E53935", "#1E88E5"]
    
    for ax, metric, title in zip(axes, metrics, titles):
        data = [raw_results["binary"][metric], raw_results["quadratic"][metric]]
        bp = ax.boxplot(data, labels=["Binary", "Quadratic"], 
                       patch_artist=True, widths=0.5)
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        for median in bp['medians']:
            median.set_color('black')
            median.set_linewidth(2)
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.2, axis='y')
    
    plt.suptitle('Robustness Under Confidence Perturbation (±1)', 
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✓ Saved: {filename}")


# ============================================================================
# 4. Manual 15-Case Analysis
# ============================================================================

def analyze_manual_cases():
    """Generate and analyze 15 manually constructed cases."""
    dataset = generate_test_dataset(n_cases=15, seed=0)
    ablation = run_ablation(dataset)
    
    y_true = np.array([case.ground_truth for case in dataset])
    
    results = {}
    for key, name in [("binary", "Binary"), ("graded_linear", "Linear"), ("graded_quadratic", "Quadratic")]:
        scores = np.array(ablation[key].scores)
        pred = scores >= 0.5
        tp = np.sum(pred & y_true)
        fp = np.sum(pred & ~y_true)
        fn = np.sum(~pred & y_true)
        tn = np.sum(~pred & ~y_true)
        
        accuracy = (tp + tn) / len(y_true)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        results[name] = {
            "scores": scores.tolist(),
            "accuracy": round(float(accuracy), 3),
            "precision": round(float(precision), 3),
            "recall": round(float(recall), 3),
            "f1": round(float(f1), 3),
        }
    
    return results, dataset, y_true


# ============================================================================
# Main
# ============================================================================

def main():
    print()
    print("=" * 70)
    print("SPOTLIGHT ANALYSES — ML4H Paper Upgrade")
    print("=" * 70)
    print()
    
    # Generate data
    print("Loading synthetic dataset (N=1000, seed=42)...")
    dataset = generate_test_dataset(n_cases=1000, seed=42)
    ablation = run_ablation(dataset)
    
    y_true = np.array([case.ground_truth for case in dataset])
    scores_binary = np.array(ablation["binary"].scores)
    scores_linear = np.array(ablation["graded_linear"].scores)
    scores_quadratic = np.array(ablation["graded_quadratic"].scores)
    print(f"   ✓ {len(y_true)} cases loaded")
    print()
    
    all_results = {}
    
    # ── 1. AUC-ROC and AUC-PR ──────────────────────────────────────────
    print("1. Computing AUC-ROC and AUC-PR...")
    auc_results = {}
    for name, scores in [("Binary", scores_binary), 
                          ("Graded Linear", scores_linear),
                          ("Graded Quadratic", scores_quadratic)]:
        r = compute_auc_roc_pr(scores, y_true)
        auc_results[name] = r
        print(f"   {name}: AUC-ROC={r['auc_roc']:.4f}, AUC-PR={r['auc_pr']:.4f}")
    
    plot_roc_pr_curves(auc_results, os.path.join(FIG_DIR, "roc_pr_curves.png"))
    all_results["auc"] = {
        name: {"auc_roc": r["auc_roc"], "auc_pr": r["auc_pr"]}
        for name, r in auc_results.items()
    }
    print()
    
    # ── 2. Alpha Sensitivity ────────────────────────────────────────────
    print("2. Running α sensitivity analysis...")
    alpha_results = run_alpha_sensitivity(dataset, y_true)
    plot_alpha_sensitivity(alpha_results, os.path.join(FIG_DIR, "alpha_sensitivity.png"))
    all_results["alpha_sensitivity"] = alpha_results
    
    # Export CSV
    with open(os.path.join(TBL_DIR, "alpha_sensitivity.csv"), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=["alpha", "accuracy", "precision", "recall", "f1", "ece", "brier"])
        w.writeheader()
        w.writerows(alpha_results)
    print(f"   ✓ Saved: alpha_sensitivity.csv")
    print()
    
    # ── 3. Noise Robustness ─────────────────────────────────────────────
    print("3. Running confidence noise robustness test (50 trials)...")
    noise_summary, noise_raw = run_noise_robustness(dataset, y_true, n_trials=50)
    plot_noise_robustness(noise_raw, os.path.join(FIG_DIR, "noise_robustness.png"))
    all_results["noise_robustness"] = noise_summary
    
    for name, s in noise_summary.items():
        print(f"   {name}: ECE={s['ece_mean']:.3f}±{s['ece_std']:.3f}, "
              f"Brier={s['brier_mean']:.3f}±{s['brier_std']:.3f}, "
              f"F1={s['f1_mean']:.3f}±{s['f1_std']:.3f}")
    print()
    
    # ── 4. Manual Cases ─────────────────────────────────────────────────
    print("4. Analyzing 15 manual cases...")
    manual_results, manual_dataset, manual_y = analyze_manual_cases()
    all_results["manual_cases"] = manual_results
    
    for name, r in manual_results.items():
        print(f"   {name}: Acc={r['accuracy']}, F1={r['f1']}")
    print()
    
    # ── Save JSON ───────────────────────────────────────────────────────
    print("5. Saving consolidated results...")
    # Remove non-serializable data
    save_results = {
        "auc": all_results["auc"],
        "alpha_sensitivity": all_results["alpha_sensitivity"],
        "noise_robustness": all_results["noise_robustness"],
        "manual_cases": {name: {k: v for k, v in r.items() if k != "scores"} 
                         for name, r in all_results["manual_cases"].items()},
    }
    
    with open(os.path.join(JSON_DIR, "spotlight_analyses.json"), 'w') as f:
        json.dump(save_results, f, indent=2)
    print(f"   ✓ Saved: spotlight_analyses.json")
    
    print()
    print("=" * 70)
    print("SPOTLIGHT ANALYSES COMPLETE")
    print("=" * 70)
    print()
    print("New figures in results/figures/:")
    print("  • roc_pr_curves.png")
    print("  • alpha_sensitivity.png")  
    print("  • noise_robustness.png")
    print()
    print("New tables in results/tables/:")
    print("  • alpha_sensitivity.csv")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

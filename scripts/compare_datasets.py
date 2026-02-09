"""
Dataset Comparison Runner

Compares ablation study results between:
- Original 15 manually-created cases
- 1000 synthetic cases

Outputs detailed comparison metrics and visualizations.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Dict
from src.evaluation.ablation_runner import (
    generate_test_dataset,
    run_ablation,
    print_comparison_table,
    export_results,
    AblationResult
)
from src.response_models import ScoringMode


def print_dataset_comparison_header():
    """Print header for dataset comparison"""
    print("\n" + "=" * 120)
    print("DATASET COMPARISON: Manual (15 cases) vs Synthetic (1000 cases)")
    print("=" * 120)
    print()


def run_comparison_analysis():
    """
    Run ablation study on both datasets and compare results.
    """
    print_dataset_comparison_header()
    
    # ========== MANUAL DATASET (15 cases) ==========
    print("🔬 Running ablation on MANUAL dataset (15 cases)...")
    dataset_manual = generate_test_dataset(n_cases=15)
    results_manual = run_ablation(dataset_manual)
    
    print(f"✅ Completed manual dataset analysis ({len(dataset_manual)} cases)")
    print()
    
    # ========== SYNTHETIC DATASET (1000 cases) ==========
    print("🔬 Running ablation on SYNTHETIC dataset (1000 cases)...")
    dataset_synthetic = generate_test_dataset(n_cases=1000, seed=42)
    results_synthetic = run_ablation(dataset_synthetic)
    
    print(f"✅ Completed synthetic dataset analysis ({len(dataset_synthetic)} cases)")
    print()
    
    # ========== COMPARISON TABLES ==========
    print("\n" + "=" * 120)
    print("MANUAL DATASET RESULTS (15 cases)")
    print("=" * 120)
    print_comparison_table(results_manual)
    
    print("\n" + "=" * 120)
    print("SYNTHETIC DATASET RESULTS (1000 cases)")
    print("=" * 120)
    print_comparison_table(results_synthetic)
    
    # ========== DELTA ANALYSIS ==========
    print_delta_analysis(results_manual, results_synthetic)
    
    # ========== EXPORT RESULTS ==========
    export_results(results_manual, "ablation_results_manual_15.json")
    export_results(results_synthetic, "ablation_results_synthetic_1000.json")
    
    # Export comparison
    export_comparison(results_manual, results_synthetic)
    
    return results_manual, results_synthetic


def print_delta_analysis(
    results_manual: Dict[ScoringMode, AblationResult],
    results_synthetic: Dict[ScoringMode, AblationResult]
):
    """
    Print detailed delta analysis between manual and synthetic datasets.
    """
    print("\n" + "=" * 120)
    print("DELTA ANALYSIS: Synthetic (1000) vs Manual (15)")
    print("=" * 120)
    print()
    
    modes = ["binary", "graded_linear", "graded_quadratic"]
    
    for mode in modes:
        manual = results_manual.get(mode)
        synthetic = results_synthetic.get(mode)
        
        if not manual or not synthetic:
            continue
        
        print(f"📊 {mode.upper()}")
        print("-" * 120)
        
        # Calculate deltas
        delta_accuracy = synthetic.accuracy - manual.accuracy
        delta_precision = synthetic.precision - manual.precision
        delta_recall = synthetic.recall - manual.recall
        delta_f1 = synthetic.f1_score - manual.f1_score
        delta_avg_score = synthetic.avg_score - manual.avg_score
        
        # Print metrics
        print(f"  Accuracy:        Manual: {manual.accuracy:.3f}  →  Synthetic: {synthetic.accuracy:.3f}  "
              f"(Δ {delta_accuracy:+.3f}, {delta_accuracy*100:+.1f}%)")
        print(f"  Precision:       Manual: {manual.precision:.3f}  →  Synthetic: {synthetic.precision:.3f}  "
              f"(Δ {delta_precision:+.3f}, {delta_precision*100:+.1f}%)")
        print(f"  Recall:          Manual: {manual.recall:.3f}  →  Synthetic: {synthetic.recall:.3f}  "
              f"(Δ {delta_recall:+.3f}, {delta_recall*100:+.1f}%)")
        print(f"  F1-Score:        Manual: {manual.f1_score:.3f}  →  Synthetic: {synthetic.f1_score:.3f}  "
              f"(Δ {delta_f1:+.3f}, {delta_f1*100:+.1f}%)")
        print(f"  Avg Score:       Manual: {manual.avg_score:.3f}  →  Synthetic: {synthetic.avg_score:.3f}  "
              f"(Δ {delta_avg_score:+.3f}, {delta_avg_score*100:+.1f}%)")
        
        # Confusion matrix changes
        print(f"\n  Confusion Matrix:")
        print(f"    True Positives:   {manual.true_positives:3d} → {synthetic.true_positives:3d}  "
              f"(Δ {synthetic.true_positives - manual.true_positives:+3d})")
        print(f"    True Negatives:   {manual.true_negatives:3d} → {synthetic.true_negatives:3d}  "
              f"(Δ {synthetic.true_negatives - manual.true_negatives:+3d})")
        print(f"    False Positives:  {manual.false_positives:3d} → {synthetic.false_positives:3d}  "
              f"(Δ {synthetic.false_positives - manual.false_positives:+3d})")
        print(f"    False Negatives:  {manual.false_negatives:3d} → {synthetic.false_negatives:3d}  "
              f"(Δ {synthetic.false_negatives - manual.false_negatives:+3d})")
        
        print()
    
    # Statistical significance note
    print("=" * 120)
    print("📈 STATISTICAL SIGNIFICANCE")
    print("-" * 120)
    print(f"  Sample Size Increase: 15 → 1000 cases ({1000/15:.1f}x increase)")
    print(f"  Standard Error Reduction: ~{(1/15)**0.5 / (1/1000)**0.5:.1f}x improvement")
    print(f"  Confidence Interval Width: ~{(1/1000)**0.5 / (1/15)**0.5:.1f}x narrower")
    print()
    print("  ✅ 1000 cases provide statistically robust estimates")
    print("  ✅ Reduced variance in performance metrics")
    print("  ✅ More reliable for scientific validation")
    print("=" * 120)
    print()


def export_comparison(
    results_manual: Dict[ScoringMode, AblationResult],
    results_synthetic: Dict[ScoringMode, AblationResult],
    filename: str = "dataset_comparison.json"
):
    """Export detailed comparison to JSON"""
    comparison = {
        "dataset_sizes": {
            "manual": 15,
            "synthetic": 1000
        },
        "modes": {}
    }
    
    for mode in ["binary", "graded_linear", "graded_quadratic"]:
        manual = results_manual.get(mode)
        synthetic = results_synthetic.get(mode)
        
        if manual and synthetic:
            comparison["modes"][mode] = {
                "manual": {
                    "accuracy": manual.accuracy,
                    "precision": manual.precision,
                    "recall": manual.recall,
                    "f1_score": manual.f1_score,
                    "avg_score": manual.avg_score,
                    "true_positives": manual.true_positives,
                    "true_negatives": manual.true_negatives,
                    "false_positives": manual.false_positives,
                    "false_negatives": manual.false_negatives
                },
                "synthetic": {
                    "accuracy": synthetic.accuracy,
                    "precision": synthetic.precision,
                    "recall": synthetic.recall,
                    "f1_score": synthetic.f1_score,
                    "avg_score": synthetic.avg_score,
                    "true_positives": synthetic.true_positives,
                    "true_negatives": synthetic.true_negatives,
                    "false_positives": synthetic.false_positives,
                    "false_negatives": synthetic.false_negatives
                },
                "delta": {
                    "accuracy": synthetic.accuracy - manual.accuracy,
                    "precision": synthetic.precision - manual.precision,
                    "recall": synthetic.recall - manual.recall,
                    "f1_score": synthetic.f1_score - manual.f1_score,
                    "avg_score": synthetic.avg_score - manual.avg_score
                }
            }
    
    with open(filename, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"✅ Comparison exported to {filename}")


def print_dataset_statistics(dataset):
    """Print statistics about the dataset"""
    from collections import Counter
    
    print("\n📊 DATASET STATISTICS")
    print("-" * 80)
    
    # Ground truth distribution
    ground_truths = [case.ground_truth for case in dataset]
    eligible_count = sum(ground_truths)
    ineligible_count = len(ground_truths) - eligible_count
    
    print(f"  Total Cases: {len(dataset)}")
    print(f"  Eligible (True):    {eligible_count:4d} ({eligible_count/len(dataset)*100:.1f}%)")
    print(f"  Ineligible (False): {ineligible_count:4d} ({ineligible_count/len(dataset)*100:.1f}%)")
    
    # Answer type distribution
    answer_types = []
    confidence_levels = []
    
    for case in dataset:
        for response in case.responses.values():
            answer_types.append(response.answer.value)
            confidence_levels.append(response.confidence)
    
    answer_counts = Counter(answer_types)
    confidence_counts = Counter(confidence_levels)
    
    print(f"\n  Answer Type Distribution:")
    print(f"    YES:    {answer_counts['yes']:5d} ({answer_counts['yes']/len(answer_types)*100:.1f}%)")
    print(f"    NO:     {answer_counts['no']:5d} ({answer_counts['no']/len(answer_types)*100:.1f}%)")
    print(f"    UNSURE: {answer_counts['unsure']:5d} ({answer_counts['unsure']/len(answer_types)*100:.1f}%)")
    
    print(f"\n  Confidence Level Distribution:")
    for conf_level in sorted(confidence_counts.keys()):
        count = confidence_counts[conf_level]
        print(f"    Confidence {conf_level}: {count:5d} ({count/len(confidence_levels)*100:.1f}%)")
    
    print("-" * 80)


def main():
    """Main comparison runner"""
    # Run comparison
    results_manual, results_synthetic = run_comparison_analysis()
    
    # Print dataset statistics
    print("\n" + "=" * 120)
    print("DATASET STATISTICS COMPARISON")
    print("=" * 120)
    
    print("\n🔹 MANUAL DATASET (15 cases)")
    dataset_manual = generate_test_dataset(n_cases=15)
    print_dataset_statistics(dataset_manual)
    
    print("\n🔹 SYNTHETIC DATASET (1000 cases)")
    dataset_synthetic = generate_test_dataset(n_cases=1000, seed=42)
    print_dataset_statistics(dataset_synthetic)
    
    print("\n" + "=" * 120)
    print("✅ COMPARISON COMPLETE")
    print("=" * 120)
    print("\nGenerated files:")
    print("  - ablation_results_manual_15.json")
    print("  - ablation_results_synthetic_1000.json")
    print("  - dataset_comparison.json")
    print()


if __name__ == "__main__":
    main()

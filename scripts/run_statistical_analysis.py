#!/usr/bin/env python
"""
Statistical Analysis Runner Script

Executes complete statistical analysis pipeline:
1. Generates synthetic dataset (1000 cases, seed=42)
2. Runs ablation to get scores for Binary, Linear, Quadratic
3. Applies isotonic calibration to Quadratic scores
4. Runs monotonicity analysis (before/after)
5. Runs McNemar's test (Binary vs Quadratic)
6. Runs bootstrap CI for accuracy, recall, F1
7. Exports results as JSON, CSV, and LaTeX tables

Usage:
    python scripts/run_statistical_analysis.py [--n_cases N] [--seed SEED]
"""

import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.evaluation.ablation_runner import generate_test_dataset, run_ablation
from src.evaluation.statistical_analysis import (
    run_complete_statistical_analysis,
    export_all_results_json,
    export_monotonicity_table_csv,
    export_monotonicity_table_latex,
    export_bootstrap_table_csv,
    export_bootstrap_table_latex,
    export_mcnemar_result_latex,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run statistical analysis for clinical trials matching evaluation"
    )
    parser.add_argument(
        "--n_cases", type=int, default=1000,
        help="Number of synthetic cases (default: 1000)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Decision threshold for binarization (default: 0.5)"
    )
    parser.add_argument(
        "--bootstrap_iterations", type=int, default=1000,
        help="Number of bootstrap iterations (default: 1000)"
    )
    parser.add_argument(
        "--output_dir", type=str, default="results",
        help="Output directory for results (default: results/)"
    )
    
    args = parser.parse_args()
    
    print()
    print("=" * 70)
    print("STATISTICAL ANALYSIS RUNNER")
    print("=" * 70)
    print(f"  Cases: {args.n_cases}")
    print(f"  Seed: {args.seed}")
    print(f"  Threshold: {args.threshold}")
    print(f"  Bootstrap Iterations: {args.bootstrap_iterations}")
    print(f"  Output Directory: {args.output_dir}")
    print("=" * 70)
    print()
    
    # 1. Generate dataset
    print("Step 1: Generating synthetic dataset...")
    dataset = generate_test_dataset(n_cases=args.n_cases, seed=args.seed)
    print(f"   Generated {len(dataset)} patient cases")
    print()
    
    # 2. Run ablation to get scores
    print("Step 2: Running ablation study...")
    ablation_results = run_ablation(dataset)
    
    # Extract scores and ground truth
    y_true = np.array([case.ground_truth for case in dataset])
    scores_binary = np.array(ablation_results["binary"].scores)
    scores_linear = np.array(ablation_results["graded_linear"].scores)
    scores_quadratic = np.array(ablation_results["graded_quadratic"].scores)
    
    print(f"   Binary scores: {len(scores_binary)}")
    print(f"   Linear scores: {len(scores_linear)}")
    print(f"   Quadratic scores: {len(scores_quadratic)}")
    print()
    
    # 3. Run complete statistical analysis
    print("Step 3: Running statistical analysis...")
    print()
    
    results = run_complete_statistical_analysis(
        y_true=y_true,
        scores_binary=scores_binary,
        scores_linear=scores_linear,
        scores_quadratic=scores_quadratic,
        threshold=args.threshold,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed
    )
    
    # 4. Export results
    print()
    print("Step 4: Exporting results...")
    
    # Create output directory if needed
    os.makedirs(args.output_dir, exist_ok=True)
    
    # JSON
    json_path = os.path.join(args.output_dir, "statistical_analysis_results.json")
    export_all_results_json(
        monotonicity=results["monotonicity"],
        mcnemar=results["mcnemar"],
        bootstrap_binary=results["bootstrap_binary"],
        bootstrap_quadratic=results["bootstrap_quadratic"],
        filename=json_path
    )
    print(f"   ✓ JSON: {json_path}")
    
    # CSV files
    monotonicity_csv = os.path.join(args.output_dir, "monotonicity_table.csv")
    export_monotonicity_table_csv(results["monotonicity"], monotonicity_csv)
    print(f"   ✓ CSV: {monotonicity_csv}")
    
    bootstrap_csv = os.path.join(args.output_dir, "bootstrap_ci_table.csv")
    export_bootstrap_table_csv(
        results["bootstrap_binary"],
        results["bootstrap_quadratic"],
        bootstrap_csv
    )
    print(f"   ✓ CSV: {bootstrap_csv}")
    
    # LaTeX files
    latex_path = os.path.join(args.output_dir, "tables_latex.txt")
    with open(latex_path, 'w', encoding='utf-8') as f:
        f.write("% Monotonicity Table\n")
        f.write(export_monotonicity_table_latex(results["monotonicity"]))
        f.write("\n\n")
        f.write("% McNemar's Test Table\n")
        f.write(export_mcnemar_result_latex(results["mcnemar"]))
        f.write("\n\n")
        f.write("% Bootstrap CI Table\n")
        f.write(export_bootstrap_table_latex(
            results["bootstrap_binary"],
            results["bootstrap_quadratic"]
        ))
    print(f"   ✓ LaTeX: {latex_path}")
    
    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Return exit code based on success criteria
    all_success = all(results["success"].values())
    if not all_success:
        print()
        print("⚠️  WARNING: Not all success criteria were met!")
        print("   Review results carefully before publication.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

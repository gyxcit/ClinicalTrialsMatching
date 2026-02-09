#!/usr/bin/env python
"""
Workshop Analysis Runner Script

Executes complete calibration analysis for workshop submission:
1. Generates synthetic dataset (1000 cases, seed=42)
2. Runs ablation for Binary/Quadratic scores
3. Applies isotonic calibration
4. Generates reliability diagrams
5. Computes ECE and Brier scores
6. Applies temperature scaling
7. Exports all results (PNG, CSV, LaTeX, JSON)

Target: ML4H @ NeurIPS, CHIL, MLHC workshops

Usage:
    python scripts/run_workshop_analysis.py [--n_cases N] [--seed SEED]
"""

import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.evaluation.ablation_runner import generate_test_dataset, run_ablation
from src.evaluation.statistical_analysis import apply_isotonic_calibration
from src.evaluation.calibration_visualization import run_calibration_analysis


def main():
    parser = argparse.ArgumentParser(
        description="Run workshop calibration analysis"
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
        "--n_bins", type=int, default=10,
        help="Number of bins for reliability diagrams (default: 10)"
    )
    parser.add_argument(
        "--output_dir", type=str, default="results",
        help="Output directory for results (default: results/)"
    )
    
    args = parser.parse_args()
    
    print()
    print("=" * 70)
    print("WORKSHOP ANALYSIS RUNNER")
    print("=" * 70)
    print(f"  Cases: {args.n_cases}")
    print(f"  Seed: {args.seed}")
    print(f"  Bins: {args.n_bins}")
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
    scores_quadratic = np.array(ablation_results["graded_quadratic"].scores)
    
    print(f"   Binary scores: {len(scores_binary)}")
    print(f"   Quadratic scores: {len(scores_quadratic)}")
    print()
    
    # 3. Apply isotonic calibration to quadratic scores
    print("Step 3: Applying isotonic calibration...")
    scores_quadratic_isotonic = apply_isotonic_calibration(scores_quadratic, y_true)
    print(f"   ✓ Isotonic calibration applied")
    print()
    
    # 4. Run complete calibration analysis
    print("Step 4: Running calibration analysis...")
    print()
    
    results = run_calibration_analysis(
        scores_binary=scores_binary,
        scores_quadratic=scores_quadratic,
        scores_quadratic_isotonic=scores_quadratic_isotonic,
        y_true=y_true,
        output_dir=args.output_dir,
        n_bins=args.n_bins
    )
    
    print()
    print("=" * 70)
    print("WORKSHOP ANALYSIS COMPLETE")
    print("=" * 70)
    print()
    print("Generated Files:")
    print(f"  • reliability_diagram_binary.png")
    print(f"  • reliability_diagram_quadratic_raw.png")
    print(f"  • reliability_diagram_quadratic_isotonic.png")
    print(f"  • reliability_diagram_binary_tempscaled.png")
    print(f"  • calibration_metrics.csv")
    print(f"  • calibration_metrics_latex.txt")
    print(f"  • workshop_analysis_results.json")
    print()
    
    if results["ece_ordering_correct"]:
        print("✅ ECE ordering verified: Binary > Quadratic > Isotonic")
        return 0
    else:
        print("⚠️ ECE ordering unexpected - review results")
        return 1


if __name__ == "__main__":
    sys.exit(main())

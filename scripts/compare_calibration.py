"""
Calibration Comparison Script

Compare calibration analysis between:
- 15 manual cases
- 1000 synthetic cases
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.calibration_analysis import run_calibration_analysis, print_calibration_table, generate_scientific_summary, export_calibration_results


def main():
    """Run calibration analysis for both datasets"""
    
    print("\n" + "=" * 100)
    print("CALIBRATION ANALYSIS COMPARISON: 15 Manual vs 1000 Synthetic Cases")
    print("=" * 100)
    print()
    
    # === MANUAL DATASET (15 cases) ===
    print("\n" + "🔬" * 50)
    print("RUNNING CALIBRATION ANALYSIS: MANUAL DATASET (15 cases)")
    print("🔬" * 50)
    
    results_manual = run_calibration_analysis(n_cases=15)
    
    for mode_name, result in results_manual.items():
        print_calibration_table(result)
    
    summary_manual = generate_scientific_summary(results_manual)
    print(summary_manual)
    
    export_calibration_results(results_manual, "calibration_results_manual_15.json")
    
    # === SYNTHETIC DATASET (1000 cases) ===
    print("\n\n" + "🔬" * 50)
    print("RUNNING CALIBRATION ANALYSIS: SYNTHETIC DATASET (1000 cases)")
    print("🔬" * 50)
    
    results_synthetic = run_calibration_analysis(n_cases=1000)
    
    for mode_name, result in results_synthetic.items():
        print_calibration_table(result)
    
    summary_synthetic = generate_scientific_summary(results_synthetic)
    print(summary_synthetic)
    
    export_calibration_results(results_synthetic, "calibration_results_synthetic_1000.json")
    
    # === COMPARISON ===
    print("\n\n" + "=" * 100)
    print("COMPARATIVE ANALYSIS")
    print("=" * 100)
    
    for mode in ["binary", "graded_linear", "graded_quadratic"]:
        manual = results_manual.get(mode)
        synthetic = results_synthetic.get(mode)
        
        if not manual or not synthetic:
            continue
        
        print(f"\n📊 {mode.upper()}")
        print("-" * 100)
        
        print(f"  Spearman Correlation:")
        print(f"    Manual (15):      ρ = {manual.spearman_correlation:.3f} (p = {manual.spearman_p_value:.4f})")
        print(f"    Synthetic (1000): ρ = {synthetic.spearman_correlation:.3f} (p = {synthetic.spearman_p_value:.4f})")
        
        delta_corr = synthetic.spearman_correlation - manual.spearman_correlation
        print(f"    Δ Correlation:    {delta_corr:+.3f}")
        
        print(f"\n  Monotonicity:")
        print(f"    Manual (15):      {'✅ YES' if manual.is_monotonic else f'❌ NO ({len(manual.violations)} violations)'}")
        print(f"    Synthetic (1000): {'✅ YES' if synthetic.is_monotonic else f'❌ NO ({len(synthetic.violations)} violations)'}")
        
        if not manual.is_monotonic or not synthetic.is_monotonic:
            print(f"\n  Violations:")
            if not manual.is_monotonic:
                for v in manual.violations:
                    print(f"    Manual: {v}")
            if not synthetic.is_monotonic:
                for v in synthetic.violations:
                    print(f"    Synthetic: {v}")
    
    print("\n" + "=" * 100)
    print("✅ CALIBRATION COMPARISON COMPLETE")
    print("=" * 100)
    print("\nGenerated files:")
    print("  - calibration_results_manual_15.json")
    print("  - calibration_results_synthetic_1000.json")
    print()


if __name__ == "__main__":
    main()

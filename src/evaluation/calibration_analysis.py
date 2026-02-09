"""
Calibration and Monotonicity Analysis

Verifies that eligibility scores are ordinally meaningful:
    Higher score → Higher probability of real eligibility

This analysis strengthens scientific credibility WITHOUT modifying scoring logic.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict
import json
from scipy import stats

from src.evaluation.ablation_runner import run_ablation, generate_test_dataset, PatientCase, AblationResult


@dataclass
class ScoreBin:
    """A score bin with empirical statistics"""
    bin_range: Tuple[float, float]
    bin_label: str
    count: int
    eligible_count: int
    eligible_rate: float


@dataclass
class CalibrationResult:
    """Results of calibration analysis for one scoring mode"""
    mode: str
    bins: List[ScoreBin]
    is_monotonic: bool
    violations: List[str]
    spearman_correlation: float
    spearman_p_value: float


def create_score_bins() -> List[Tuple[float, float, str]]:
    """
    Create fixed score bins for calibration analysis.
    
    Returns:
        List of (lower, upper, label) tuples
    """
    return [
        (0.0, 0.2, "[0.0-0.2)"),
        (0.2, 0.4, "[0.2-0.4)"),
        (0.4, 0.6, "[0.4-0.6)"),
        (0.6, 0.8, "[0.6-0.8)"),
        (0.8, 1.0, "[0.8-1.0]")
    ]


def assign_to_bin(score: float, bins: List[Tuple[float, float, str]]) -> Tuple[float, float, str]:
    """
    Assign a score to its bin.
    
    Args:
        score: Eligibility score (0.0 to 1.0)
        bins: List of bin definitions
    
    Returns:
        The bin (lower, upper, label) that contains this score
    """
    for lower, upper, label in bins:
        if lower <= score < upper:
            return (lower, upper, label)
        # Special case for exactly 1.0
        if score == 1.0 and upper == 1.0:
            return (lower, upper, label)
    
    # Shouldn't happen if score is in [0, 1]
    return bins[-1]


def analyze_calibration(
    scores: List[float],
    ground_truth: List[bool],
    mode: str
) -> CalibrationResult:
    """
    Analyze calibration and monotonicity of scores.
    
    Args:
        scores: List of eligibility scores
        ground_truth: List of true eligibility labels
        mode: Scoring mode name
    
    Returns:
        CalibrationResult with bins, monotonicity check, and correlation
    """
    bins_def = create_score_bins()
    
    # Initialize bins
    bin_data = {label: {"count": 0, "eligible": 0} for _, _, label in bins_def}
    
    # Assign each score to a bin
    for score, truth in zip(scores, ground_truth):
        _, _, label = assign_to_bin(score, bins_def)
        bin_data[label]["count"] += 1
        if truth:
            bin_data[label]["eligible"] += 1
    
    # Create ScoreBin objects
    score_bins = []
    for lower, upper, label in bins_def:
        count = bin_data[label]["count"]
        eligible_count = bin_data[label]["eligible"]
        eligible_rate = eligible_count / count if count > 0 else 0.0
        
        score_bins.append(ScoreBin(
            bin_range=(lower, upper),
            bin_label=label,
            count=count,
            eligible_count=eligible_count,
            eligible_rate=eligible_rate
        ))
    
    # Check monotonicity
    is_monotonic = True
    violations = []
    
    for i in range(len(score_bins) - 1):
        current_bin = score_bins[i]
        next_bin = score_bins[i + 1]
        
        # Skip empty bins
        if current_bin.count == 0 or next_bin.count == 0:
            continue
        
        # Monotonicity: rate should not decrease
        if next_bin.eligible_rate < current_bin.eligible_rate:
            is_monotonic = False
            violations.append(
                f"{current_bin.bin_label} ({current_bin.eligible_rate:.2f}) > "
                f"{next_bin.bin_label} ({next_bin.eligible_rate:.2f})"
            )
    
    # Calculate Spearman correlation
    spearman_corr, spearman_p = stats.spearmanr(scores, [int(t) for t in ground_truth])
    
    return CalibrationResult(
        mode=mode,
        bins=score_bins,
        is_monotonic=is_monotonic,
        violations=violations,
        spearman_correlation=spearman_corr,
        spearman_p_value=spearman_p
    )


def run_calibration_analysis(n_cases: int = 15) -> Dict[str, CalibrationResult]:
    """
    Run calibration analysis on all scoring modes.
    
    Args:
        n_cases: Number of cases to generate (default: 15 for manual dataset)
    
    Returns:
        Dictionary mapping mode to calibration results
    """
    # Get dataset and ablation results
    dataset = generate_test_dataset(n_cases=n_cases)
    ablation_results = run_ablation(dataset)
    
    # Extract ground truth
    ground_truth = [case.ground_truth for case in dataset]
    
    # Analyze each mode
    calibration_results = {}
    
    for mode_name, ablation_result in ablation_results.items():
        calibration_results[mode_name] = analyze_calibration(
            scores=ablation_result.scores,
            ground_truth=ground_truth,
            mode=mode_name
        )
    
    return calibration_results


def print_calibration_table(result: CalibrationResult):
    """Print calibration table for one mode"""
    print(f"\n{'='*80}")
    print(f"CALIBRATION ANALYSIS: {result.mode.upper()}")
    print(f"{'='*80}\n")
    
    # Table header
    print(f"{'Score Bin':<15} {'#Cases':<10} {'#Eligible':<12} {'Eligible Rate':<15}")
    print("-" * 80)
    
    # Bins
    for bin_obj in result.bins:
        if bin_obj.count > 0:
            print(f"{bin_obj.bin_label:<15} {bin_obj.count:<10} "
                  f"{bin_obj.eligible_count:<12} {bin_obj.eligible_rate:<15.3f}")
        else:
            print(f"{bin_obj.bin_label:<15} {bin_obj.count:<10} {'N/A':<12} {'N/A':<15}")
    
    print("-" * 80)
    
    # Monotonicity check
    if result.is_monotonic:
        print("✅ Monotonicity: VERIFIED (no violations)")
    else:
        print(f"❌ Monotonicity: VIOLATED ({len(result.violations)} violations)")
        for violation in result.violations:
            print(f"   - {violation}")
    
    # Correlation
    print(f"\n📊 Spearman Correlation: {result.spearman_correlation:.3f} (p={result.spearman_p_value:.4f})")
    
    if result.spearman_p_value < 0.05:
        print("   ✅ Statistically significant correlation (p < 0.05)")
    else:
        print("   ⚠️  Correlation not statistically significant (p >= 0.05)")
    
    print()


def generate_scientific_summary(results: Dict[str, CalibrationResult]) -> str:
    """
    Generate publication-ready scientific summary.
    
    Args:
        results: Dictionary of calibration results
    
    Returns:
        Formatted scientific summary text
    """
    summary = []
    summary.append("=" * 80)
    summary.append("SCIENTIFIC SUMMARY: Calibration & Monotonicity Analysis")
    summary.append("=" * 80)
    summary.append("")
    
    for mode_name, result in results.items():
        summary.append(f"### {mode_name.replace('_', ' ').title()}")
        summary.append("")
        
        # Monotonicity statement
        if result.is_monotonic:
            summary.append(
                f"✅ Eligibility scores exhibited **monotonic behavior** with respect to "
                f"ground-truth eligibility likelihood. Higher score bins were consistently "
                f"associated with equal or higher proportions of eligible cases."
            )
        else:
            summary.append(
                f"⚠️  Monotonicity violations detected ({len(result.violations)} instances). "
                f"Some higher score bins exhibited lower eligibility rates than preceding bins."
            )
        
        summary.append("")
        
        # Correlation statement
        if result.spearman_correlation > 0:
            strength = "strong" if result.spearman_correlation > 0.7 else "moderate" if result.spearman_correlation > 0.4 else "weak"
            significance = "statistically significant" if result.spearman_p_value < 0.05 else "not statistically significant"
            
            summary.append(
                f"📊 Spearman rank correlation: ρ = {result.spearman_correlation:.3f} "
                f"(p = {result.spearman_p_value:.4f}), indicating a **{strength}** "
                f"and **{significance}** ordinal relationship between predicted scores "
                f"and ground-truth eligibility."
            )
        
        summary.append("")
        summary.append("-" * 80)
        summary.append("")
    
    # Overall conclusion
    summary.append("### Overall Conclusion")
    summary.append("")
    
    all_monotonic = all(r.is_monotonic for r in results.values())
    avg_correlation = sum(r.spearman_correlation for r in results.values()) / len(results)
    
    if all_monotonic:
        summary.append(
            "✅ **All scoring modes demonstrated ordinal validity**: Scores are monotonic "
            "with respect to ground-truth eligibility likelihood. This confirms that the "
            "continuous eligibility scores (0-1) are **ordinally meaningful** and suitable "
            "for clinical decision support."
        )
    else:
        summary.append(
            "⚠️  **Some scoring modes exhibited monotonicity violations**. Further analysis "
            "may be needed to understand edge cases or refine binning strategy."
        )
    
    summary.append("")
    summary.append(
        f"📈 **Average Spearman correlation across modes**: ρ̄ = {avg_correlation:.3f}"
    )
    
    summary.append("")
    summary.append("=" * 80)
    
    return "\n".join(summary)


def export_calibration_results(results: Dict[str, CalibrationResult], filename: str = "calibration_results.json"):
    """Export calibration results to JSON"""
    export_data = {}
    
    for mode, result in results.items():
        export_data[mode] = {
            "bins": [
                {
                    "range": result.bins[i].bin_label,
                    "count": result.bins[i].count,
                    "eligible_count": result.bins[i].eligible_count,
                    "eligible_rate": result.bins[i].eligible_rate
                }
                for i in range(len(result.bins))
            ],
            "is_monotonic": result.is_monotonic,
            "violations": result.violations,
            "spearman_correlation": result.spearman_correlation,
            "spearman_p_value": result.spearman_p_value
        }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Calibration results exported to {filename}")


def main(n_cases: int = 15):
    """
    Run calibration analysis and display results
    
    Args:
        n_cases: Number of cases to analyze (default: 15)
    """
    print("\n" + "=" * 80)
    print(f"RUNNING CALIBRATION & MONOTONICITY ANALYSIS ({n_cases} cases)")
    print("=" * 80)
    print()
    print("Objective: Verify ordinal significance of eligibility scores")
    print("Method: Fixed binning + empirical probability estimation")
    print()
    
    # Run analysis
    results = run_calibration_analysis(n_cases=n_cases)
    
    # Print tables for each mode
    for mode_name, result in results.items():
        print_calibration_table(result)
    
    # Print scientific summary
    summary = generate_scientific_summary(results)
    print(summary)
    
    # Export results
    suffix = f"_{n_cases}" if n_cases != 15 else ""
    export_calibration_results(results, f"calibration_results{suffix}.json")
    
    print("\n✅ Calibration analysis complete!")
    print()


if __name__ == "__main__":
    main()

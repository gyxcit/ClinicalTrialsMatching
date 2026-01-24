"""
Exponent Sensitivity Analysis Calculator
Calculates UNSURE scores for different exponent values
Formula: score = 0.5 * (confidence / 5) ** exponent
"""

import pandas as pd
import numpy as np

def calculate_unsure_score(confidence: int, exponent: float) -> float:
    """Calculate UNSURE score with given exponent"""
    return 0.5 * (confidence / 5.0) ** exponent

def main():
    # Define confidence levels and exponents to test
    confidence_levels = [1, 2, 3, 4, 5]
    exponents = [1.0, 1.25, 1.5, 1.75, 2.0]
    
    print("=" * 80)
    print("EXPONENT SENSITIVITY ANALYSIS - UNSURE SCORING")
    print("Formula: score = 0.5 × (confidence / 5)^exponent")
    print("=" * 80)
    print()
    
    # Calculate all scores
    results = {}
    for exp in exponents:
        results[f"exp={exp}"] = [calculate_unsure_score(c, exp) for c in confidence_levels]
    
    # Create DataFrame for scores
    df_scores = pd.DataFrame(results, index=confidence_levels)
    df_scores.index.name = "Confidence"
    
    print("TABLE 1: ABSOLUTE SCORES")
    print("-" * 80)
    print(df_scores.round(3))
    print()
    
    # Calculate incremental changes (Δ score)
    print("TABLE 2: INCREMENTAL CHANGES (Δ score when confidence increases by 1)")
    print("-" * 80)
    
    incremental_changes = {}
    for exp in exponents:
        scores = results[f"exp={exp}"]
        changes = [scores[i] - scores[i-1] for i in range(1, len(scores))]
        incremental_changes[f"exp={exp}"] = changes
    
    transitions = ["1→2", "2→3", "3→4", "4→5"]
    df_incremental = pd.DataFrame(incremental_changes, index=transitions)
    df_incremental.index.name = "Transition"
    print(df_incremental.round(3))
    print()
    
    # Calculate percentage difference vs linear (exp=1.0)
    print("TABLE 3: PERCENTAGE DIFFERENCE VS LINEAR (exp=1.0)")
    print("-" * 80)
    
    linear_scores = results["exp=1.0"]
    pct_diff = {}
    
    for exp in exponents:
        if exp == 1.0:
            pct_diff[f"exp={exp}"] = [0.0] * len(confidence_levels)
        else:
            scores = results[f"exp={exp}"]
            pct_diff[f"exp={exp}"] = [
                ((scores[i] - linear_scores[i]) / linear_scores[i] * 100) 
                for i in range(len(scores))
            ]
    
    df_pct_diff = pd.DataFrame(pct_diff, index=confidence_levels)
    df_pct_diff.index.name = "Confidence"
    print(df_pct_diff.round(1))
    print()
    
    # Calculate ratio of incremental changes vs linear
    print("TABLE 4: INCREMENTAL CHANGE RATIO VS LINEAR")
    print("-" * 80)
    
    linear_changes = incremental_changes["exp=1.0"]
    ratio_changes = {}
    
    for exp in exponents:
        changes = incremental_changes[f"exp={exp}"]
        ratio_changes[f"exp={exp}"] = [
            changes[i] / linear_changes[i] for i in range(len(changes))
        ]
    
    df_ratio = pd.DataFrame(ratio_changes, index=transitions)
    df_ratio.index.name = "Transition"
    print(df_ratio.round(2))
    print()
    
    # Highlight key findings for exp=1.5
    print("=" * 80)
    print("KEY FINDINGS FOR exp=1.5 (IMPLEMENTED)")
    print("=" * 80)
    
    exp_15_scores = results["exp=1.5"]
    exp_15_incremental = incremental_changes["exp=1.5"]
    exp_15_pct = pct_diff["exp=1.5"]
    
    print(f"\nAbsolute Scores:")
    for i, conf in enumerate(confidence_levels):
        print(f"  Confidence {conf}: {exp_15_scores[i]:.3f}")
    
    print(f"\nIncremental Changes:")
    for i, trans in enumerate(transitions):
        ratio = exp_15_incremental[i] / linear_changes[i]
        print(f"  {trans}: +{exp_15_incremental[i]:.3f} ({ratio:.2f}x linear)")
    
    print(f"\nPercentage vs Linear:")
    for i, conf in enumerate(confidence_levels):
        print(f"  Confidence {conf}: {exp_15_pct[i]:+.1f}%")
    
    print()
    print("=" * 80)
    print("VALIDATION: exp=2.0 CALCULATION CHECK")
    print("=" * 80)
    
    # Manually calculate exp=2.0 for verification
    print("\nManual calculation for exp=2.0:")
    for conf in confidence_levels:
        normalized = conf / 5.0
        squared = normalized ** 2.0
        score = 0.5 * squared
        print(f"  Confidence {conf}: 0.5 × ({conf}/5)² = 0.5 × {normalized:.1f}² = 0.5 × {squared:.2f} = {score:.3f}")
    
    # Export to CSV for documentation
    print("\n" + "=" * 80)
    print("Exporting results to CSV files...")
    
    df_scores.to_csv("exponent_scores.csv")
    df_incremental.to_csv("exponent_incremental.csv")
    df_pct_diff.to_csv("exponent_pct_diff.csv")
    
    print("✅ Exported: exponent_scores.csv")
    print("✅ Exported: exponent_incremental.csv")
    print("✅ Exported: exponent_pct_diff.csv")
    print()

if __name__ == "__main__":
    main()

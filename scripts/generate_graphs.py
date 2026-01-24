"""
Generate publication-quality graphs for exponent sensitivity analysis
Uses matplotlib and seaborn for professional scientific visualization
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

# Set publication-quality style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['font.size'] = 10

def calculate_unsure_score(confidence: np.ndarray, exponent: float) -> np.ndarray:
    """Calculate UNSURE score with given exponent"""
    return 0.5 * (confidence / 5.0) ** exponent

def generate_comparison_graph():
    """Generate main comparison graph: Linear vs Quadratic modulation"""
    
    confidence_levels = np.array([1, 2, 3, 4, 5])
    
    # Calculate scores
    linear_scores = calculate_unsure_score(confidence_levels, 1.0)
    quadratic_scores = calculate_unsure_score(confidence_levels, 1.5)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), 
                                    gridspec_kw={'height_ratios': [2, 1]})
    
    # Top plot: Absolute scores
    ax1.plot(confidence_levels, linear_scores, 'o--', linewidth=2.5, 
             markersize=8, color='#3498db', label='Linear (old): 0.5 × conf/5', alpha=0.7)
    ax1.plot(confidence_levels, quadratic_scores, 'o-', linewidth=3, 
             markersize=10, color='#e74c3c', label='Quadratic (new): 0.5 × (conf/5)^1.5')
    
    # Add data labels
    for i, (c, lin, quad) in enumerate(zip(confidence_levels, linear_scores, quadratic_scores)):
        if i in [0, 1, 2, 4]:  # Show labels for specific points
            ax1.text(c, lin + 0.02, f'{lin:.2f}', ha='center', va='bottom', 
                    fontsize=8, color='#3498db', fontweight='bold')
            ax1.text(c, quad - 0.02, f'{quad:.2f}', ha='center', va='top', 
                    fontsize=8, color='#e74c3c', fontweight='bold')
    
    ax1.set_xlabel('Confidence Level', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Eligibility Score', fontsize=12, fontweight='bold')
    ax1.set_title('UNSURE Response Scoring: Linear vs Quadratic Modulation', 
                  fontsize=14, fontweight='bold', pad=15)
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0.5, 5.5)
    ax1.set_ylim(0, 0.55)
    ax1.set_xticks(confidence_levels)
    
    # Bottom plot: Percentage difference
    pct_diff = ((quadratic_scores - linear_scores) / linear_scores * 100)
    
    colors = ['#e74c3c' if diff < 0 else '#27ae60' for diff in pct_diff]
    bars = ax2.bar(confidence_levels, pct_diff, color=colors, alpha=0.7, edgecolor='black')
    
    # Annotate key differences
    for i, (c, diff) in enumerate(zip(confidence_levels, pct_diff)):
        if i == 1:  # Highlight conf=2
            ax2.text(c, diff - 5, f'{diff:.0f}%', ha='center', va='top', 
                    fontsize=11, color='white', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#e74c3c', alpha=0.8))
        elif abs(diff) > 5:
            ax2.text(c, diff + (3 if diff > 0 else -3), f'{diff:.0f}%', 
                    ha='center', va='bottom' if diff > 0 else 'top', 
                    fontsize=9, fontweight='bold')
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax2.set_xlabel('Confidence Level', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Difference vs Linear (%)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_xlim(0.5, 5.5)
    ax2.set_xticks(confidence_levels)
    
    plt.tight_layout()
    plt.savefig('documentation/images/scoring_curve_corrected.png', bbox_inches='tight')
    print("✅ Generated: scoring_curve_corrected.png")
    plt.close()

def generate_sensitivity_analysis():
    """Generate comprehensive sensitivity analysis with multiple exponents"""
    
    confidence_levels = np.array([1, 2, 3, 4, 5])
    exponents = [1.0, 1.25, 1.5, 1.75, 2.0]
    
    # Calculate all scores
    scores = {}
    for exp in exponents:
        scores[exp] = calculate_unsure_score(confidence_levels, exp)
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), 
                                    gridspec_kw={'height_ratios': [3, 2]})
    
    # Define colors
    colors = {
        1.0: '#3498db',    # Blue
        1.25: '#5dade2',   # Light blue
        1.5: '#e74c3c',    # Red (highlighted)
        1.75: '#e67e22',   # Orange
        2.0: '#8b0000'     # Dark red
    }
    
    line_styles = {
        1.0: '--',
        1.25: '-',
        1.5: '-',
        1.75: '-',
        2.0: '-'
    }
    
    line_widths = {
        1.0: 2,
        1.25: 2,
        1.5: 3.5,  # Highlighted
        1.75: 2,
        2.0: 2
    }
    
    # Top plot: All curves
    for exp in exponents:
        label = f'exp={exp}' + (' (Implemented)' if exp == 1.5 else ' (Linear)' if exp == 1.0 else '')
        ax1.plot(confidence_levels, scores[exp], 
                marker='o', linestyle=line_styles[exp], 
                linewidth=line_widths[exp], markersize=8, 
                color=colors[exp], label=label, alpha=0.85)
    
    ax1.set_xlabel('Confidence Level', fontsize=13, fontweight='bold')
    ax1.set_ylabel('UNSURE Score', fontsize=13, fontweight='bold')
    ax1.set_title('Exponent Sensitivity Analysis: UNSURE Scoring Modulation', 
                  fontsize=15, fontweight='bold', pad=15)
    ax1.legend(loc='upper left', fontsize=10, framealpha=0.95)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0.5, 5.5)
    ax1.set_ylim(0, 0.55)
    ax1.set_xticks(confidence_levels)
    
    # Bottom plot: Percentage difference vs linear
    linear_scores = scores[1.0]
    
    for exp in [1.25, 1.5, 1.75, 2.0]:
        pct_diff = ((scores[exp] - linear_scores) / linear_scores * 100)
        
        label = f'exp={exp}' + (' (Implemented)' if exp == 1.5 else '')
        lw = 3.5 if exp == 1.5 else 2
        
        ax2.plot(confidence_levels, pct_diff, 
                marker='o', linestyle='-', linewidth=lw, 
                markersize=8, color=colors[exp], label=label, alpha=0.85)
        
        # Annotate exp=1.5 at conf=2
        if exp == 1.5:
            idx = 1  # confidence = 2
            ax2.annotate(f'{pct_diff[idx]:.0f}%', 
                        xy=(confidence_levels[idx], pct_diff[idx]), 
                        xytext=(confidence_levels[idx] + 0.5, pct_diff[idx] - 8),
                        fontsize=12, fontweight='bold', color='#e74c3c',
                        arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=2))
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.5)
    ax2.set_xlabel('Confidence Level', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Difference vs Linear (%)', fontsize=13, fontweight='bold')
    ax2.legend(loc='lower right', fontsize=10, framealpha=0.95)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0.5, 5.5)
    ax2.set_xticks(confidence_levels)
    
    plt.tight_layout()
    plt.savefig('documentation/images/exponent_analysis_corrected.png', bbox_inches='tight')
    print("✅ Generated: exponent_analysis_corrected.png")
    plt.close()

def generate_incremental_changes():
    """Generate visualization of incremental score changes"""
    
    confidence_levels = np.array([1, 2, 3, 4, 5])
    exponents = [1.0, 1.5, 2.0]
    
    # Calculate incremental changes
    transitions = ['1→2', '2→3', '3→4', '4→5']
    
    data = []
    for exp in exponents:
        scores = calculate_unsure_score(confidence_levels, exp)
        changes = np.diff(scores)
        
        for i, (trans, change) in enumerate(zip(transitions, changes)):
            data.append({
                'Transition': trans,
                'Exponent': f'exp={exp}' + (' (Implemented)' if exp == 1.5 else ' (Linear)' if exp == 1.0 else ' (Quadratic)'),
                'Change': change
            })
    
    df = pd.DataFrame(data)
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    exp_order = ['exp=1.0 (Linear)', 'exp=1.5 (Implemented)', 'exp=2.0 (Quadratic)']
    colors_map = {
        'exp=1.0 (Linear)': '#3498db',
        'exp=1.5 (Implemented)': '#e74c3c',
        'exp=2.0 (Quadratic)': '#8b0000'
    }
    
    x = np.arange(len(transitions))
    width = 0.25
    
    for i, exp_label in enumerate(exp_order):
        exp_data = df[df['Exponent'] == exp_label]
        offset = width * (i - 1)
        bars = ax.bar(x + offset, exp_data['Change'], width, 
                     label=exp_label, color=colors_map[exp_label], alpha=0.8)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}',
                   ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    ax.set_xlabel('Confidence Transition', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score Increase', fontsize=12, fontweight='bold')
    ax.set_title('Incremental Score Changes by Exponent', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(transitions)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('documentation/images/incremental_changes.png', bbox_inches='tight')
    print("✅ Generated: incremental_changes.png")
    plt.close()

def main():
    print("=" * 80)
    print("GENERATING PUBLICATION-QUALITY GRAPHS")
    print("=" * 80)
    print()
    
    print("1. Generating Linear vs Quadratic comparison...")
    generate_comparison_graph()
    
    print("2. Generating comprehensive sensitivity analysis...")
    generate_sensitivity_analysis()
    
    print("3. Generating incremental changes visualization...")
    generate_incremental_changes()
    
    print()
    print("=" * 80)
    print("✅ ALL GRAPHS GENERATED SUCCESSFULLY!")
    print("=" * 80)
    print()
    print("Output files:")
    print("  - documentation/images/scoring_curve_corrected.png")
    print("  - documentation/images/exponent_analysis_corrected.png")
    print("  - documentation/images/incremental_changes.png")

if __name__ == "__main__":
    main()

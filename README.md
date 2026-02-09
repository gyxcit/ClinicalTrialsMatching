# Uncertainty-Aware and Ordinally Calibrated Scoring for AI-Based Clinical Trial Matching

> **ML4H @ NeurIPS Workshop Submission**
> Lightweight, uncertainty-aware eligibility scoring framework with graded answers and calibration analysis.

---

## Repository Structure

```
├── src/evaluation/              # Core research modules
│   ├── ablation_runner.py       # Controlled ablation study (Binary/Linear/Quadratic)
│   ├── calibration_analysis.py  # Bin-based calibration & monotonicity
│   ├── calibration_visualization.py  # Reliability diagrams, ECE, Brier, temp scaling
│   ├── statistical_analysis.py  # McNemar, bootstrap CI, isotonic regression
│   └── simple_metrics.py        # Basic classification metrics
│
├── scripts/                     # Reproducible runner scripts
│   ├── run_ml4h_finalization.py      # [START HERE] Full ML4H analysis
│   ├── run_workshop_analysis.py      # Calibration-focused analysis
│   ├── run_statistical_analysis.py   # Statistical tests (McNemar, bootstrap)
│   ├── compare_calibration.py        # Calibration comparison
│   ├── compare_datasets.py           # Manual vs synthetic dataset comparison
│   ├── calculate_exponent_sensitivity.py  # α sensitivity analysis
│   └── generate_graphs.py            # Visualization generation
│
├── tests/                       # Unit tests (18 tests)
│   ├── test_ablation.py
│   ├── test_graded_logic.py
│   └── test_statistical_analysis.py
│
├── results/                     # Pre-computed outputs (reproducible)
│   ├── figures/                 # Publication-ready diagrams (300 DPI)
│   ├── tables/                  # CSV + LaTeX tables
│   └── json/                    # Raw result data
│
├── documentation/               # Project documentation
│   ├── paper/                   # Paper PDFs
│   ├── SCIENTIFIC_RATIONALE.md  # Detailed scientific justification
│   ├── CALIBRATION_ANALYSIS_REPORT.md
│   ├── DATASET_ANALYSIS_REPORT.md
│   └── ARCHITECTURE.md
│
├── appendix.md                  # Supplementary material (formulas, tables, proofs)
├── main.py                      # Flask web application entry point
└── requirements.txt
```

---

## Quick Start — Reproducing Results

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the full ML4H analysis

```bash
python scripts/run_ml4h_finalization.py
```

This generates all outputs in `results/`:
- **Performance table** (Table 1): `results/tables/performance_table.csv`
- **Score distributions** (Figure 2): `results/figures/score_distribution_binary_vs_quadratic.png`
- **Bootstrap CIs**: `results/tables/bootstrap_calibration_ci_latex.txt`

### 3. Run calibration analysis (reliability diagrams)

```bash
python scripts/run_workshop_analysis.py
```

### 4. Run statistical analysis (McNemar, bootstrap)

```bash
python scripts/run_statistical_analysis.py
```

### 5. Run tests

```bash
python -m pytest tests/ -v
```

---

## Key Results

| Method | Accuracy | Precision | Recall | F1 | ECE ↓ | Brier ↓ |
|--------|----------|-----------|--------|-----|-------|---------|
| Binary | 0.656 | 0.634 | 0.878 | 0.736 | 0.193 | 0.204 |
| Graded Linear | 0.706 | 0.681 | 0.868 | 0.764 | 0.100 | 0.152 |
| **Graded Quadratic** | **0.688** | **0.679** | **0.815** | **0.741** | **0.108** | **0.155** |
| Binary + Temp. Scaling | 0.656 | 0.634 | 0.878 | 0.736 | 0.090 | 0.166 |

- **ECE reduction**: −44% (Binary → Quadratic)
- **Brier improvement**: −24% (Binary → Quadratic)
- **McNemar's test**: χ² = 7.88, p = 0.005 (significant)
- **Bootstrap CIs**: Non-overlapping for ECE and Brier

---

## Scoring Functions

**Binary**: Responses mapped to {0, 0.5, 1} ignoring confidence.

**Graded Quadratic** (proposed): Uncertain responses modulated by confidence via power-law:

```
s(unsure, c) = 0.5 × (c/5)^α,  α = 1.5
```

See `appendix.md` for full mathematical formulations and derivations.

---

## Technical Stack

- **Python 3.12** with NumPy, Matplotlib, scikit-learn
- **Flask** web application for interactive trial matching
- All analyses are **deterministic** (seed = 42) and **reproducible**

---

## License

MIT

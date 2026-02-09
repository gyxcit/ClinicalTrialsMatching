"""
Tests for Statistical Analysis Module

Validates:
1. Isotonic regression produces monotonic output
2. McNemar's test statistic computation correctness
3. Bootstrap CI contains expected values
4. Reproducibility with fixed seed
"""

import pytest
import numpy as np

from src.evaluation.statistical_analysis import (
    apply_isotonic_calibration,
    compute_bin_statistics,
    check_monotonicity,
    analyze_monotonicity,
    mcnemar_test,
    bootstrap_confidence_intervals,
    compare_bootstrap_cis,
    get_default_bins,
)


class TestIsotonicCalibration:
    """Tests for isotonic regression calibration"""
    
    def test_output_shape_matches_input(self):
        """Calibrated scores should have same shape as input"""
        scores = np.array([0.1, 0.5, 0.8, 0.3, 0.9])
        y_true = np.array([0, 1, 1, 0, 1])
        
        calibrated = apply_isotonic_calibration(scores, y_true)
        
        assert calibrated.shape == scores.shape
    
    def test_calibrated_values_in_range(self):
        """Calibrated scores should be in [0, 1]"""
        np.random.seed(42)
        scores = np.random.uniform(0, 1, 100)
        y_true = np.random.randint(0, 2, 100)
        
        calibrated = apply_isotonic_calibration(scores, y_true)
        
        assert np.all(calibrated >= 0)
        assert np.all(calibrated <= 1)
    
    def test_monotonicity_after_calibration(self):
        """Calibration should produce monotonic bin-wise eligibility rates"""
        np.random.seed(42)
        # Create scores with known non-monotonic pattern
        scores = np.concatenate([
            np.random.uniform(0.0, 0.2, 50),  # Low scores
            np.random.uniform(0.2, 0.4, 50),  # Mid-low scores
            np.random.uniform(0.6, 0.8, 50),  # Mid-high scores
            np.random.uniform(0.8, 1.0, 50),  # High scores
        ])
        # Create non-monotonic truth pattern
        y_true = np.array(
            [0] * 30 + [1] * 20 +  # 40% eligible in low
            [1] * 40 + [0] * 10 +  # 80% eligible in mid-low (violation!)
            [0] * 25 + [1] * 25 +  # 50% eligible in mid-high
            [1] * 45 + [0] * 5     # 90% eligible in high
        )
        
        calibrated = apply_isotonic_calibration(scores, y_true)
        
        # Check bin-wise monotonicity
        bins = compute_bin_statistics(calibrated, y_true)
        is_mono, _ = check_monotonicity(bins)
        
        assert is_mono, "Isotonic calibration should produce monotonic bin rates"


class TestMonotonicityAnalysis:
    """Tests for monotonicity analysis"""
    
    def test_detects_monotonic_scores(self):
        """Should correctly identify monotonic scores"""
        scores = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
        y_true = np.array([0, 0, 0, 1, 1, 1])
        
        bins = compute_bin_statistics(scores, y_true)
        is_mono, violations = check_monotonicity(bins)
        
        assert is_mono
        assert len(violations) == 0
    
    def test_detects_violations(self):
        """Should detect monotonicity violations"""
        # Construct scores that definitely violate monotonicity
        scores = np.array([
            0.1, 0.1, 0.1,  # 3 in [0.0-0.2)
            0.3, 0.3, 0.3,  # 3 in [0.2-0.4)
            0.5, 0.5, 0.5,  # 3 in [0.4-0.6)
        ])
        # Mid bin has highest rate, which violates monotonicity
        y_true = np.array([
            0, 0, 1,  # 1/3 = 33% eligible in [0.0-0.2)
            1, 1, 1,  # 3/3 = 100% eligible in [0.2-0.4)
            1, 0, 0,  # 1/3 = 33% eligible in [0.4-0.6)
        ])
        
        bins = compute_bin_statistics(scores, y_true)
        is_mono, violations = check_monotonicity(bins)
        
        assert not is_mono
        assert len(violations) >= 1
    
    def test_empty_bins_skipped(self):
        """Empty bins should not cause violations"""
        scores = np.array([0.1, 0.1, 0.9, 0.9])  # Only low and high bins
        y_true = np.array([0, 0, 1, 1])
        
        bins = compute_bin_statistics(scores, y_true)
        is_mono, violations = check_monotonicity(bins)
        
        # Should be monotonic (0% -> 100%, empty bins skipped)
        assert is_mono


class TestMcNemarTest:
    """Tests for McNemar's test"""
    
    def test_contingency_counts(self):
        """Should correctly compute contingency table"""
        # Binary: 3 correct (indices 0, 1, 4)
        # Quadratic: 4 correct (indices 0, 2, 3, 4)
        scores_binary = np.array([0.6, 0.6, 0.4, 0.4, 0.6])
        scores_quad = np.array([0.6, 0.4, 0.6, 0.6, 0.6])
        y_true = np.array([True, True, True, True, True])
        
        result = mcnemar_test(scores_binary, scores_quad, y_true, threshold=0.5)
        
        # n01: Binary correct, Quad wrong -> index 1 (binary=0.6>=0.5, quad=0.4<0.5)
        # n10: Binary wrong, Quad correct -> indices 2, 3
        assert result.n01 == 1
        assert result.n10 == 2
    
    def test_significant_difference(self):
        """Should detect significant difference with large discordant pairs"""
        np.random.seed(42)
        n = 100
        
        # Create scores where Quadratic is clearly better
        scores_binary = np.random.uniform(0.3, 0.7, n)
        scores_quad = np.random.uniform(0.5, 0.9, n)
        y_true = np.ones(n, dtype=bool)  # All eligible
        
        result = mcnemar_test(scores_binary, scores_quad, y_true, threshold=0.5)
        
        # With more Quadratic correct, n10 > n01
        assert result.n10 > result.n01
    
    def test_exact_test_for_small_samples(self):
        """Should use exact test for small discordant pairs"""
        scores_binary = np.array([0.6, 0.4])
        scores_quad = np.array([0.6, 0.6])
        y_true = np.array([True, True])
        
        result = mcnemar_test(scores_binary, scores_quad, y_true, threshold=0.5)
        
        assert result.test_type == "exact"
    
    def test_chi2_test_for_large_samples(self):
        """Should use chi2 test for large discordant pairs"""
        np.random.seed(42)
        n = 200
        
        scores_binary = np.random.uniform(0.3, 0.7, n)
        scores_quad = np.random.uniform(0.4, 0.8, n)
        y_true = np.ones(n, dtype=bool)
        
        result = mcnemar_test(scores_binary, scores_quad, y_true, threshold=0.5)
        
        if result.n01 + result.n10 >= 25:
            assert result.test_type == "chi2"


class TestBootstrapCI:
    """Tests for bootstrap confidence intervals"""
    
    def test_ci_contains_point_estimate(self):
        """CI should contain the point estimate (mean)"""
        np.random.seed(42)
        scores = np.random.uniform(0.4, 0.8, 100)
        y_true = np.random.randint(0, 2, 100)
        
        result = bootstrap_confidence_intervals(
            scores, y_true, n_iterations=500, seed=42
        )
        
        # Mean should be within CI bounds
        assert result.accuracy.ci_lower <= result.accuracy.mean <= result.accuracy.ci_upper
        assert result.recall.ci_lower <= result.recall.mean <= result.recall.ci_upper
        assert result.f1_score.ci_lower <= result.f1_score.mean <= result.f1_score.ci_upper
    
    def test_ci_bounds_ordered(self):
        """Lower bound should be less than upper bound"""
        np.random.seed(42)
        scores = np.random.uniform(0.3, 0.9, 100)
        y_true = np.random.randint(0, 2, 100)
        
        result = bootstrap_confidence_intervals(
            scores, y_true, n_iterations=500, seed=42
        )
        
        assert result.accuracy.ci_lower < result.accuracy.ci_upper
        assert result.recall.ci_lower < result.recall.ci_upper
        assert result.f1_score.ci_lower < result.f1_score.ci_upper
    
    def test_reproducibility(self):
        """Same seed should produce same results"""
        scores = np.array([0.3, 0.5, 0.7, 0.8, 0.9])
        y_true = np.array([0, 0, 1, 1, 1])
        
        result1 = bootstrap_confidence_intervals(
            scores, y_true, n_iterations=100, seed=42
        )
        result2 = bootstrap_confidence_intervals(
            scores, y_true, n_iterations=100, seed=42
        )
        
        assert result1.accuracy.mean == result2.accuracy.mean
        assert result1.accuracy.ci_lower == result2.accuracy.ci_lower
        assert result1.accuracy.ci_upper == result2.accuracy.ci_upper
    
    def test_different_seeds_different_results(self):
        """Different seeds should produce different results"""
        scores = np.array([0.3, 0.5, 0.7, 0.8, 0.9])
        y_true = np.array([0, 0, 1, 1, 1])
        
        result1 = bootstrap_confidence_intervals(
            scores, y_true, n_iterations=100, seed=42
        )
        result2 = bootstrap_confidence_intervals(
            scores, y_true, n_iterations=100, seed=123
        )
        
        # CI bounds should differ (extremely unlikely to be identical)
        assert (result1.accuracy.ci_lower != result2.accuracy.ci_lower or
                result1.accuracy.ci_upper != result2.accuracy.ci_upper)


class TestBootstrapComparison:
    """Tests for comparing bootstrap CIs"""
    
    def test_non_overlapping_detection(self):
        """Should detect when CIs don't overlap"""
        from src.evaluation.statistical_analysis import BootstrapResult, BootstrapCI
        
        # Create non-overlapping CIs
        binary = BootstrapResult(
            accuracy=BootstrapCI("accuracy", 0.6, 0.55, 0.65, 0.03),
            recall=BootstrapCI("recall", 0.5, 0.45, 0.55, 0.03),
            f1_score=BootstrapCI("f1_score", 0.55, 0.50, 0.60, 0.03),
            n_iterations=1000,
            seed=42
        )
        
        quadratic = BootstrapResult(
            accuracy=BootstrapCI("accuracy", 0.8, 0.75, 0.85, 0.03),  # Non-overlap
            recall=BootstrapCI("recall", 0.7, 0.65, 0.75, 0.03),      # Non-overlap
            f1_score=BootstrapCI("f1_score", 0.62, 0.57, 0.67, 0.03), # Overlaps
            n_iterations=1000,
            seed=42
        )
        
        comparison = compare_bootstrap_cis(binary, quadratic)
        
        assert comparison["accuracy"] == True   # 0.75 > 0.65
        assert comparison["recall"] == True     # 0.65 > 0.55
        assert comparison["f1_score"] == False  # 0.57 < 0.60 (overlaps)


class TestIntegration:
    """Integration tests for full analysis pipeline"""
    
    def test_full_analysis_runs(self):
        """Full analysis should complete without errors"""
        from src.evaluation.statistical_analysis import run_complete_statistical_analysis
        
        np.random.seed(42)
        n = 100
        
        y_true = np.random.randint(0, 2, n).astype(bool)
        scores_binary = np.random.uniform(0.2, 0.8, n)
        scores_linear = np.random.uniform(0.3, 0.9, n)
        scores_quadratic = np.random.uniform(0.3, 0.9, n)
        
        results = run_complete_statistical_analysis(
            y_true=y_true,
            scores_binary=scores_binary,
            scores_linear=scores_linear,
            scores_quadratic=scores_quadratic,
            threshold=0.5,
            bootstrap_iterations=100,  # Fewer for speed
            seed=42
        )
        
        # Check all expected keys present
        assert "scores_quadratic_isotonic" in results
        assert "monotonicity" in results
        assert "mcnemar" in results
        assert "bootstrap_binary" in results
        assert "bootstrap_quadratic" in results
        assert "success" in results
        
        # Check success dict
        assert "monotonicity" in results["success"]
        assert "mcnemar" in results["success"]
        assert "bootstrap" in results["success"]


class TestBinStatistics:
    """Tests for bin statistics computation"""
    
    def test_default_bins(self):
        """Should have 5 default bins"""
        bins = get_default_bins()
        assert len(bins) == 5
    
    def test_bin_assignment(self):
        """Scores should be assigned to correct bins"""
        scores = np.array([0.0, 0.19, 0.2, 0.5, 0.8, 1.0])
        y_true = np.array([1, 1, 1, 1, 1, 1])
        
        bins = compute_bin_statistics(scores, y_true)
        
        # Check counts
        assert bins[0].count == 2  # 0.0 and 0.19 in [0.0-0.2)
        assert bins[1].count == 1  # 0.2 in [0.2-0.4)
        assert bins[2].count == 1  # 0.5 in [0.4-0.6)
        assert bins[3].count == 0  # [0.6-0.8) is empty
        assert bins[4].count == 2  # 0.8 and 1.0 in [0.8-1.0]

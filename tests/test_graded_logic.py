"""
Tests for graded logic (logical_update branch)

Validates continuous scoring, categorization, and scientific metrics.
"""
import pytest
from src.response_models import GradedAnswer, AnswerType, TrialScore
from src.evaluation.simple_metrics import calculate_metrics, EligibilityMetrics


# ===== GradedAnswer Tests =====

def test_yes_high_confidence():
    """YES with confidence 5 → score = 1.0"""
    ans = GradedAnswer(answer=AnswerType.YES, confidence=5)
    assert ans.to_score() == 1.0


def test_yes_medium_confidence():
    """YES with confidence 3 → score = 0.6"""
    ans = GradedAnswer(answer=AnswerType.YES, confidence=3)
    assert ans.to_score() == 0.6


def test_yes_low_confidence():
    """YES with confidence 1 → score = 0.2"""
    ans = GradedAnswer(answer=AnswerType.YES, confidence=1)
    assert ans.to_score() == 0.2


def test_no_always_zero():
    """NO always gives 0, regardless of confidence"""
    ans = GradedAnswer(answer=AnswerType.NO, confidence=5)
    assert ans.to_score() == 0.0
    
    ans = GradedAnswer(answer=AnswerType.NO, confidence=1)
    assert ans.to_score() == 0.0


def test_unsure_high_confidence():
    """UNSURE with confidence 5 → score = 0.5 (quadratic: (5/5)^1.5 * 0.5)"""
    ans = GradedAnswer(answer=AnswerType.UNSURE, confidence=5)
    assert ans.to_score() == 0.5


def test_unsure_mid_confidence():
    """UNSURE with confidence 3 → score ≈ 0.23 (quadratic: (3/5)^1.5 * 0.5)"""
    ans = GradedAnswer(answer=AnswerType.UNSURE, confidence=3)
    expected = 0.5 * ((3 / 5.0) ** 1.5)  # ≈ 0.2327
    assert abs(ans.to_score() - expected) < 0.01


def test_unsure_low_confidence():
    """UNSURE with confidence 1 → score ≈ 0.09 (quadratic: (1/5)^1.5 * 0.5)"""
    ans = GradedAnswer(answer=AnswerType.UNSURE, confidence=1)
    expected = 0.5 * ((1 / 5.0) ** 1.5)  # ≈ 0.0894
    assert abs(ans.to_score() - expected) < 0.01


# ===== TrialScore Tests =====

def test_strong_match():
    """All YES with high confidence → Strong Match"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.YES, confidence=5),
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5),
        'NCT123_EXC_002': GradedAnswer(answer=AnswerType.NO, confidence=5),
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.inclusion_score == 1.0
    assert score.exclusion_score == 0.0
    assert score.overall_score == 1.0
    assert score.category == "Strong Match"
    assert score.uncertainty_count == 0


def test_potential_match():
    """Mixed YES/UNSURE → Potential Match"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),  # 1.0
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.UNSURE, confidence=4),  # ~0.36 (quadratic)
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5),  # 0.0
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    # Inclusion: (1.0 + 0.358) / 2 ≈ 0.68 (quadratic modulation)
    unsure_score = 0.5 * ((4 / 5.0) ** 1.5)  # ≈ 0.358
    expected_inclusion = (1.0 + unsure_score) / 2
    assert abs(score.inclusion_score - expected_inclusion) < 0.01
    assert score.exclusion_score == 0.0
    assert abs(score.overall_score - expected_inclusion) < 0.01
    assert score.category == "Potential Match"  # Still 0.6-0.8
    assert score.uncertainty_count == 1


def test_exclusion_triggers():
    """Exclusion YES should set overall score to 0"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.YES, confidence=5),
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.YES, confidence=4),  # Exclusion!
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.inclusion_score == 1.0  # Inclusion was good
    assert score.exclusion_score == 0.8  # But exclusion triggered (4/5)
    assert score.overall_score == 0.0  # Overall = 0 due to exclusion
    assert score.category == "Not Eligible"


def test_weak_exclusion_does_not_exclude():
    """Low confidence YES on exclusion (≤0.3) should NOT exclude"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),  # 1.0
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.YES, confidence=1),  # 0.2 (below threshold)
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.exclusion_score == 0.2  # Below 0.3 threshold
    assert score.overall_score == 1.0  # NOT excluded
    assert score.category == "Strong Match"


def test_uncertainty_count():
    """Count UNSURE responses correctly"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.UNSURE, confidence=3),
        'NCT123_INC_003': GradedAnswer(answer=AnswerType.UNSURE, confidence=2),
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5),
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.uncertainty_count == 2


def test_low_confidence_count():
    """Count responses with confidence ≤ 2"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=1),  # Low
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.YES, confidence=2),  # Low
        'NCT123_INC_003': GradedAnswer(answer=AnswerType.YES, confidence=3),  # OK
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=1),   # Low
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.low_confidence_count == 3


def test_dict_responses():
    """Should handle dict responses (from session storage)"""
    responses = {
        'NCT123_INC_001': {'answer': 'yes', 'confidence': 5},
        'NCT123_EXC_001': {'answer': 'no', 'confidence': 5},
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.overall_score == 1.0
    assert score.category == "Strong Match"


# ===== Comparison: Binary vs Graded =====

def test_comparison_binary_vs_graded():
    """
    Critical test: Compare binary logic vs graded logic
    
    Scenario: Patient is UNSURE about one inclusion criterion
    - Binary logic: UNSURE treated as NO → Patient rejected
    - Graded logic: UNSURE gives partial score → Patient may still qualify
    """
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),  # 1.0
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.UNSURE, confidence=4),  # ~0.36 (quadratic)
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5),  # 0.0
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    # Graded logic (quadratic modulation)
    unsure_score = 0.5 * ((4 / 5.0) ** 1.5)  # ≈ 0.358
    expected_graded = (1.0 + unsure_score) / 2  # ≈ 0.68
    graded_score = score.overall_score
    graded_eligible = graded_score >= 0.6  # Potential Match threshold
    
    # Binary logic (simulating UNSURE as NO)
    binary_score = 1.0 / 2  # Only 1 YES out of 2 questions = 0.5
    binary_eligible = binary_score >= 0.6  # Would be rejected
    
    # Assertions
    assert abs(graded_score - expected_graded) < 0.01
    assert graded_eligible == True  # Graded allows patient (0.68 > 0.6)
    assert binary_eligible == False  # Binary rejects patient (0.5 < 0.6)
    
    # This demonstrates the scientific value of graded responses


# ===== Metrics Tests =====

def test_perfect_metrics():
    """All predictions correct → perfect scores"""
    predictions = [True, True, False, False]
    ground_truth = [True, True, False, False]
    
    metrics = calculate_metrics(predictions, ground_truth)
    
    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0


def test_metrics_with_errors():
    """Test with some errors"""
    predictions = [True, True, False, True]  # Indices 1,3 are FP
    ground_truth = [True, False, False, False]  # Index 0 is TP
    
    metrics = calculate_metrics(predictions, ground_truth)
    
    # TP=1, FP=2, FN=0, TN=1
    assert metrics.accuracy == 0.5  # (1+1)/4
    assert abs(metrics.precision - 1/3) < 0.01  # 1/(1+2)
    assert metrics.recall == 1.0  # 1/(1+0) - all actual positives found


def test_uncertainty_rate():
    """Test uncertainty rate calculation"""
    predictions = [True, False]
    ground_truth = [True, False]
    
    metrics = calculate_metrics(
        predictions, 
        ground_truth,
        uncertainty_count=3,
        total_questions=10
    )
    
    assert metrics.uncertainty_rate == 0.3  # 3/10


# ===== Edge Cases =====

def test_no_inclusion_questions():
    """Handle trial with only exclusion questions"""
    responses = {
        'NCT123_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5),
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.inclusion_score == 0.5  # Default when no inclusion
    assert score.overall_score >= 0  # Should not crash


def test_no_exclusion_questions():
    """Handle trial with only inclusion questions"""
    responses = {
        'NCT123_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5),
        'NCT123_INC_002': GradedAnswer(answer=AnswerType.YES, confidence=4),
    }
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.exclusion_score == 0.0  # Default when no exclusion
    assert abs(score.overall_score - 0.9) < 0.01  # (1.0 + 0.8) / 2


def test_empty_responses():
    """Handle empty responses gracefully"""
    responses = {}
    
    score = TrialScore.calculate('NCT123', responses)
    
    assert score.inclusion_score == 0.5
    assert score.exclusion_score == 0.0
    assert score.overall_score == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

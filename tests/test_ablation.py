"""
Tests for Ablation Study

Validates scientific properties of the three scoring modes:
1. Invariance: High confidence should converge
2. Monotonicity: Quadratic ≤ Linear for UNSURE
3. Determinism: Same inputs = same outputs
"""

import pytest
from src.response_models import GradedAnswer, TrialScore, AnswerType


class TestScoringModeInvariance:
    """Test that at high confidence, all modes converge"""
    
    def test_yes_confidence_5_invariance(self):
        """At confidence=5, all modes should give same score for YES"""
        answer = GradedAnswer(answer=AnswerType.YES, confidence=5)
        
        binary = answer.to_score(mode="binary")
        linear = answer.to_score(mode="graded_linear")
        quadratic = answer.to_score(mode="graded_quadratic")
        
        assert binary == 1.0
        assert linear == 1.0
        assert quadratic == 1.0
    
    def test_no_invariance_across_modes(self):
        """NO should always be 0.0 regardless of mode or confidence"""
        for conf in [1, 2, 3, 4, 5]:
            answer = GradedAnswer(answer=AnswerType.NO, confidence=conf)
            
            binary = answer.to_score(mode="binary")
            linear = answer.to_score(mode="graded_linear")
            quadratic = answer.to_score(mode="graded_quadratic")
            
            assert binary == 0.0
            assert linear == 0.0
            assert quadratic == 0.0
    
    def test_unsure_confidence_5_convergence(self):
        """At confidence=5, graded modes should give same UNSURE score"""
        answer = GradedAnswer(answer=AnswerType.UNSURE, confidence=5)
        
        linear = answer.to_score(mode="graded_linear")
        quadratic = answer.to_score(mode="graded_quadratic")
        
        # Both should be 0.5 at max confidence
        assert linear == 0.5
        assert quadratic == 0.5


class TestScoringModeMonotonicity:
    """Test monotonicity properties: quadratic ≤ linear for UNSURE"""
    
    @pytest.mark.parametrize("confidence", [1, 2, 3, 4, 5])
    def test_quadratic_le_linear_for_unsure(self, confidence):
        """Quadratic should be ≤ linear for all UNSURE responses"""
        answer = GradedAnswer(answer=AnswerType.UNSURE, confidence=confidence)
        
        linear = answer.to_score(mode="graded_linear")
        quadratic = answer.to_score(mode="graded_quadratic")
        
        # Quadratic should penalize more (be smaller or equal)
        assert quadratic <= linear + 0.001  # Small tolerance for floating point
    
    @pytest.mark.parametrize("confidence", [1, 2, 3, 4, 5])
    def test_yes_identical_across_graded_modes(self, confidence):
        """YES should score identically in both graded modes"""
        answer = GradedAnswer(answer=AnswerType.YES, confidence=confidence)
        
        linear = answer.to_score(mode="graded_linear")
        quadratic = answer.to_score(mode="graded_quadratic")
        
        assert abs(linear - quadratic) < 0.001


class TestBinaryModeBehavior:
    """Test binary mode specific behavior"""
    
    def test_binary_treats_unsure_as_no(self):
        """Binary mode should treat UNSURE as NO (score=0)"""
        for conf in [1, 2, 3, 4, 5]:
            answer = GradedAnswer(answer=AnswerType.UNSURE, confidence=conf)
            score = answer.to_score(mode="binary")
            
            assert score == 0.0
    
    def test_binary_ignores_confidence_for_yes(self):
        """Binary mode should ignore YES confidence (always 1.0)"""
        for conf in [1, 2, 3, 4, 5]:
            answer = GradedAnswer(answer=AnswerType.YES, confidence=conf)
            score = answer.to_score(mode="binary")
            
            assert score == 1.0


class TestDeterminism:
    """Test that scoring is deterministic"""
    
    def test_same_inputs_same_outputs_binary(self):
        """Same inputs should produce same scores in binary mode"""
        responses = {
            'Q1': GradedAnswer(answer=AnswerType.YES, confidence=4).model_dump(),
            'Q2': GradedAnswer(answer=AnswerType.UNSURE, confidence=2).model_dump()
        }
        
        score1 = TrialScore.calculate("NCT123", responses, "binary")
        score2 = TrialScore.calculate("NCT123", responses, "binary")
        
        assert score1.overall_score == score2.overall_score
        assert score1.category == score2.category
    
    def test_same_inputs_same_outputs_linear(self):
        """Same inputs should produce same scores in linear mode"""
        responses = {
            'NCT_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5).model_dump(),
            'NCT_INC_002': GradedAnswer(answer=AnswerType.UNSURE, confidence=3).model_dump(),
            'NCT_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5).model_dump()
        }
        
        score1 = TrialScore.calculate("NCT123", responses, "graded_linear")
        score2 = TrialScore.calculate("NCT123", responses, "graded_linear")
        
        assert score1.overall_score == score2.overall_score
        assert score1.inclusion_score == score2.inclusion_score
        assert score1.exclusion_score == score2.exclusion_score
    
    def test_same_inputs_same_outputs_quadratic(self):
        """Same inputs should produce same scores in quadratic mode"""
        responses = {
            'TEST_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=4).model_dump(),
            'TEST_INC_002': GradedAnswer(answer=AnswerType.UNSURE, confidence=4).model_dump(),
            'TEST_EXC_001': GradedAnswer(answer=AnswerType.NO, confidence=5).model_dump()
        }
        
        score1 = TrialScore.calculate("TEST", responses, "graded_quadratic")
        score2 = TrialScore.calculate("TEST", responses, "graded_quadratic")
        
        assert score1.overall_score == score2.overall_score


class TestQuadraticModulation:
    """Test specific properties of quadratic modulation"""
    
    def test_low_confidence_penalty(self):
        """Quadratic should heavily penalize low confidence UNSURE"""
        answer_conf1 = GradedAnswer(answer=AnswerType.UNSURE, confidence=1)
        answer_conf2 = GradedAnswer(answer=AnswerType.UNSURE, confidence=2)
        
        linear_1 = answer_conf1.to_score(mode="graded_linear")
        quadratic_1 = answer_conf1.to_score(mode="graded_quadratic")
        
        linear_2 = answer_conf2.to_score(mode="graded_linear")
        quadratic_2 = answer_conf2.to_score(mode="graded_quadratic")
        
        # Quadratic penalty should be significant at low confidence
        penalty_1 = (linear_1 - quadratic_1) / linear_1
        penalty_2 = (linear_2 - quadratic_2) / linear_2
        
        assert penalty_1 > 0.3  # At least 30% penalty at conf=1
        assert penalty_2 > 0.2  # At least 20% penalty at conf=2
    
    def test_high_confidence_preserved(self):
        """Quadratic should preserve high confidence UNSURE"""
        answer = GradedAnswer(answer=AnswerType.UNSURE, confidence=5)
        
        linear = answer.to_score(mode="graded_linear")
        quadratic = answer.to_score(mode="graded_quadratic")
        
        # At max confidence, should be identical
        assert abs(linear - quadratic) < 0.001


class TestTrialScoreConsistency:
    """Test that TrialScore calculation is consistent across modes"""
    
    def test_exclusion_logic_consistent(self):
        """Exclusion logic should work identically across modes"""
        responses = {
            'T_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5).model_dump(),
            'T_EXC_001': GradedAnswer(answer=AnswerType.YES, confidence=4).model_dump()  # Triggers exclusion
        }
        
        binary = TrialScore.calculate("T", responses, "binary")
        linear = TrialScore.calculate("T", responses, "graded_linear")
        quadratic = TrialScore.calculate("T", responses, "graded_quadratic")
        
        # All should be excluded (overall_score = 0)
        assert binary.overall_score == 0.0
        assert linear.overall_score == 0.0
        assert quadratic.overall_score == 0.0
        
        # All should have same category
        assert binary.category == "Not Eligible"
        assert linear.category == "Not Eligible"
        assert quadratic.category == "Not Eligible"
    
    def test_category_thresholds_consistent(self):
        """Category thresholds should be same across modes"""
        # Test at exact boundary: 0.8
        responses_08 = {
            'X_INC_001': GradedAnswer(answer=AnswerType.YES, confidence=5).model_dump(),
            'X_INC_002': GradedAnswer(answer=AnswerType.YES, confidence=3).model_dump(),  # 0.6
        }
        
        # Average: (1.0 + 0.6) / 2 = 0.8 exactly
        for mode in ["binary", "graded_linear", "graded_quadratic"]:
            score = TrialScore.calculate("X", responses_08, mode)
            if abs(score.overall_score - 0.8) < 0.01:
                assert score.category == "Strong Match"


class TestAblationValidity:
    """Test that ablation study setup is valid"""
    
    def test_modes_differ_only_in_scoring(self):
        """Verify that modes differ only in how they score UNSURE"""
        yes_answer = GradedAnswer(answer=AnswerType.YES, confidence=3)
        no_answer = GradedAnswer(answer=AnswerType.NO, confidence=3)
        unsure_answer = GradedAnswer(answer=AnswerType.UNSURE, confidence=3)
        
        # YES and NO should be identical across graded modes
        assert yes_answer.to_score("graded_linear") == yes_answer.to_score("graded_quadratic")
        assert no_answer.to_score("graded_linear") == no_answer.to_score("graded_quadratic")
        
        # Only UNSURE should differ
        assert unsure_answer.to_score("graded_linear") != unsure_answer.to_score("graded_quadratic")
    
    def test_binary_baseline_validity(self):
        """Binary mode should represent true baseline (no grading)"""
        # In binary, confidence should not matter for YES
        yes_low = GradedAnswer(answer=AnswerType.YES, confidence=1)
        yes_high = GradedAnswer(answer=AnswerType.YES, confidence=5)
        
        assert yes_low.to_score("binary") == yes_high.to_score("binary")
        
        # UNSURE should always be 0 in binary
        for conf in range(1, 6):
            unsure = GradedAnswer(answer=AnswerType.UNSURE, confidence=conf)
            assert unsure.to_score("binary") == 0.0

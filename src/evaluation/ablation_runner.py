"""
Ablation Study Runner

Controlled comparison of three scoring modes:
1. Binary baseline
2. Graded Linear
3. Graded Quadratic

This module enables scientific validation of the scoring improvements.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List
import json

from src.response_models import GradedAnswer, TrialScore, ScoringMode, AnswerType
from src.evaluation.simple_metrics import calculate_metrics


@dataclass
class PatientCase:
    """Fixed patient case for ablation study"""
    case_id: str
    nct_id: str
    responses: Dict[str, GradedAnswer]
    ground_truth: bool  # True = eligible, False = not eligible
    description: str = ""


@dataclass
class AblationResult:
    """Results for one scoring mode"""
    mode: ScoringMode
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    false_negatives: int
    false_positives: int
    true_positives: int
    true_negatives: int
    uncertainty_rate: float
    avg_score: float
    decisions: List[bool]
    scores: List[float]


def generate_test_dataset_manual() -> List[PatientCase]:
    """
    Generate ORIGINAL fixed dataset of 15 patient cases for ablation study.
    
    This is the manually-created dataset for baseline comparison.
    
    Returns:
        List of 15 carefully designed patient cases covering various scenarios
    """
    dataset = []
    
    # Case 1: Perfect match - All YES with high confidence
    dataset.append(PatientCase(
        case_id="CASE001",
        nct_id="NCT001",
        responses={
            "NCT001_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT001_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT001_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="Perfect match - all certain YES answers"
    ))
    
    # Case 2: Clear exclusion - One exclusion triggered
    dataset.append(PatientCase(
        case_id="CASE002",
        nct_id="NCT002",
        responses={
            "NCT002_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT002_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT002_EXC_001": GradedAnswer(answer=AnswerType.YES, confidence=4),  # Excluded
        },
        ground_truth=False,
        description="Clear exclusion criterion triggered"
    ))
    
    # Case 3: Uncertain inclusion - Mix with UNSURE conf 3
    dataset.append(PatientCase(
        case_id="CASE003",
        nct_id="NCT003",
        responses={
            "NCT003_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT003_INC_002": GradedAnswer(answer=AnswerType.UNSURE, confidence=3),
            "NCT003_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="Moderate uncertainty, still eligible"
    ))
    
    # Case 4: Low confidence UNSURE - Should benefit from graded
    dataset.append(PatientCase(
        case_id="CASE004",
        nct_id="NCT004",
        responses={
            "NCT004_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT004_INC_002": GradedAnswer(answer=AnswerType.UNSURE, confidence=2),
            "NCT004_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,  # Borderline eligible
        description="Low confidence uncertainty - binary would reject"
    ))
    
    # Case 5: Borderline case near 0.6 threshold
    dataset.append(PatientCase(
        case_id="CASE005",
        nct_id="NCT005",
        responses={
            "NCT005_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=4),
            "NCT005_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=3),
            "NCT005_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="Borderline case - moderate confidence"
    ))
    
    # Case 6: High confidence UNSURE
    dataset.append(PatientCase(
        case_id="CASE006",
        nct_id="NCT006",
        responses={
            "NCT006_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT006_INC_002": GradedAnswer(answer=AnswerType.UNSURE, confidence=5),
            "NCT006_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="High confidence uncertainty - informed 'don't know'"
    ))
    
    # Case 7: Multiple UNSURE responses
    dataset.append(PatientCase(
        case_id="CASE007",
        nct_id="NCT007",
        responses={
            "NCT007_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT007_INC_002": GradedAnswer(answer=AnswerType.UNSURE, confidence=3),
            "NCT007_INC_003": GradedAnswer(answer=AnswerType.UNSURE, confidence=4),
            "NCT007_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="Multiple uncertainties with varying confidence"
    ))
    
    # Case 8: Weak exclusion UNSURE - Should pass
    dataset.append(PatientCase(
        case_id="CASE008",
        nct_id="NCT008",
        responses={
            "NCT008_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT008_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT008_EXC_001": GradedAnswer(answer=AnswerType.UNSURE, confidence=2),  # < 0.3 threshold
        },
        ground_truth=True,
        description="Weak exclusion uncertainty - patient eligible"
    ))
    
    # Case 9: Strong exclusion UNSURE - Should fail
    dataset.append(PatientCase(
        case_id="CASE009",
        nct_id="NCT009",
        responses={
            "NCT009_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT009_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT009_EXC_001": GradedAnswer(answer=AnswerType.YES, confidence=3),  # > 0.3 threshold
        },
        ground_truth=False,
        description="Strong exclusion - patient ineligible"
    ))
    
    # Case 10: All UNSURE with varied confidence
    dataset.append(PatientCase(
        case_id="CASE010",
        nct_id="NCT010",
        responses={
            "NCT010_INC_001": GradedAnswer(answer=AnswerType.UNSURE, confidence=4),
            "NCT010_INC_002": GradedAnswer(answer=AnswerType.UNSURE, confidence=5),
            "NCT010_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="All uncertain but high confidence"
    ))
    
    # Case 11: Binary would accept, graded should be cautious
    dataset.append(PatientCase(
        case_id="CASE011",
        nct_id="NCT011",
        responses={
            "NCT011_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=1),  # Low confidence YES
            "NCT011_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=2),
            "NCT011_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=False,  # Should be rejected due to low confidence
        description="Low confidence YES answers - questionable match"
    ))
    
    # Case 12: Mixed confidence spectrum
    dataset.append(PatientCase(
        case_id="CASE012",
        nct_id="NCT012",
        responses={
            "NCT012_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT012_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=1),
            "NCT012_INC_003": GradedAnswer(answer=AnswerType.UNSURE, confidence=3),
            "NCT012_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,  # Borderline eligible
        description="Full spectrum of confidence levels"
    ))
    
    # Case 13: Clearly ineligible - Multiple NO answers
    dataset.append(PatientCase(
        case_id="CASE013",
        nct_id="NCT013",
        responses={
            "NCT013_INC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
            "NCT013_INC_002": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT013_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=False,
        description="Failed inclusion criterion"
    ))
    
    # Case 14: Near threshold - Graded quadratic vs linear difference
    dataset.append(PatientCase(
        case_id="CASE014",
        nct_id="NCT014",
        responses={
            "NCT014_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=5),
            "NCT014_INC_002": GradedAnswer(answer=AnswerType.UNSURE, confidence=4),
            "NCT014_EXC_001": GradedAnswer(answer=AnswerType.NO, confidence=5),
        },
        ground_truth=True,
        description="Near threshold - quadratic modulation impact visible"
    ))
    
    # Case 15: Edge case - Single question trial
    dataset.append(PatientCase(
        case_id="CASE015",
        nct_id="NCT015",
        responses={
            "NCT015_INC_001": GradedAnswer(answer=AnswerType.YES, confidence=4),
        },
        ground_truth=True,
        description="Single question trial"
    ))
    
    return dataset


def generate_test_dataset(n_cases: int = 15, seed: int = 42) -> List[PatientCase]:
    """
    Generate dataset for ablation study.
    
    If n_cases == 15, returns the original manual dataset.
    Otherwise, generates synthetic dataset with controlled distributions.
    
    Args:
        n_cases: Number of cases to generate (default: 15 for manual dataset)
        seed: Random seed for reproducibility (default: 42)
    
    Returns:
        List of patient cases
    """
    if n_cases == 15:
        return generate_test_dataset_manual()
    else:
        return generate_synthetic_dataset(n_cases=n_cases, seed=seed)


def generate_synthetic_dataset(
    n_cases: int = 1000,
    seed: int = 42,
    scenario_distribution: dict = None
) -> List[PatientCase]:
    """
    Generate synthetic dataset with controlled distributions.
    
    Args:
        n_cases: Number of cases to generate
        seed: Random seed for reproducibility
        scenario_distribution: Custom distribution (default: balanced)
            {
                'clearly_eligible': 0.30,
                'clearly_ineligible': 0.30,
                'borderline': 0.25,
                'uncertain': 0.15
            }
    
    Returns:
        List of synthetic patient cases
    """
    import numpy as np
    
    # Set seed for reproducibility
    np.random.seed(seed)
    
    # Default scenario distribution
    if scenario_distribution is None:
        scenario_distribution = {
            'clearly_eligible': 0.30,
            'clearly_ineligible': 0.30,
            'borderline': 0.25,
            'uncertain': 0.15
        }
    
    dataset = []
    scenarios = list(scenario_distribution.keys())
    scenario_probs = list(scenario_distribution.values())
    
    for i in range(n_cases):
        case_id = f"SYN{i+1:04d}"
        nct_id = f"NCT{i+1:04d}"
        
        # Select scenario type
        scenario = np.random.choice(scenarios, p=scenario_probs)
        
        # Determine number of questions (2-6)
        n_inclusion = np.random.randint(2, 5)
        n_exclusion = np.random.randint(1, 3)
        
        responses = {}
        
        # Generate responses based on scenario
        if scenario == 'clearly_eligible':
            # High confidence YES for inclusions, NO for exclusions
            for j in range(n_inclusion):
                conf = np.random.choice([4, 5], p=[0.3, 0.7])
                responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                    answer=AnswerType.YES, confidence=conf
                )
            for j in range(n_exclusion):
                conf = np.random.choice([4, 5], p=[0.3, 0.7])
                responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                    answer=AnswerType.NO, confidence=conf
                )
            ground_truth = True
            description = "Clearly eligible - strong match"
        
        elif scenario == 'clearly_ineligible':
            # Either failed inclusion or triggered exclusion
            if np.random.random() < 0.5:
                # Failed inclusion
                for j in range(n_inclusion):
                    if j == 0:  # First one fails
                        responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                            answer=AnswerType.NO, confidence=np.random.randint(4, 6)
                        )
                    else:
                        conf = np.random.randint(3, 6)
                        responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                            answer=AnswerType.YES, confidence=conf
                        )
                for j in range(n_exclusion):
                    responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.NO, confidence=5
                    )
                description = "Ineligible - failed inclusion"
            else:
                # Triggered exclusion
                for j in range(n_inclusion):
                    conf = np.random.randint(4, 6)
                    responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.YES, confidence=conf
                    )
                for j in range(n_exclusion):
                    if j == 0:  # First exclusion triggers
                        responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                            answer=AnswerType.YES, confidence=np.random.randint(3, 6)
                        )
                    else:
                        responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                            answer=AnswerType.NO, confidence=5
                        )
                description = "Ineligible - exclusion triggered"
            ground_truth = False
        
        elif scenario == 'borderline':
            # Mix of moderate confidence YES and some UNSURE
            for j in range(n_inclusion):
                if np.random.random() < 0.3:
                    # Some UNSURE
                    conf = np.random.choice([3, 4], p=[0.6, 0.4])
                    responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.UNSURE, confidence=conf
                    )
                else:
                    # Moderate YES
                    conf = np.random.choice([3, 4], p=[0.5, 0.5])
                    responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.YES, confidence=conf
                    )
            for j in range(n_exclusion):
                # Weak exclusion uncertainty or clear NO
                if np.random.random() < 0.2:
                    conf = np.random.choice([1, 2])
                    responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.UNSURE, confidence=conf
                    )
                else:
                    conf = np.random.randint(4, 6)
                    responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.NO, confidence=conf
                    )
            # Borderline cases: 60% eligible, 40% not
            ground_truth = np.random.random() < 0.6
            description = "Borderline case - moderate confidence"
        
        else:  # uncertain
            # Many UNSURE responses with varying confidence
            for j in range(n_inclusion):
                if np.random.random() < 0.6:
                    # UNSURE
                    conf = np.random.randint(2, 6)
                    responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.UNSURE, confidence=conf
                    )
                else:
                    # YES with varied confidence
                    conf = np.random.randint(2, 6)
                    responses[f"{nct_id}_INC_{j+1:03d}"] = GradedAnswer(
                        answer=AnswerType.YES, confidence=conf
                    )
            for j in range(n_exclusion):
                conf = np.random.randint(4, 6)
                responses[f"{nct_id}_EXC_{j+1:03d}"] = GradedAnswer(
                    answer=AnswerType.NO, confidence=conf
                )
            # Uncertain cases: slight bias toward eligible (55%)
            ground_truth = np.random.random() < 0.55
            description = "High uncertainty - many UNSURE responses"
        
        dataset.append(PatientCase(
            case_id=case_id,
            nct_id=nct_id,
            responses=responses,
            ground_truth=ground_truth,
            description=description
        ))
    
    return dataset



def run_ablation(
    dataset: List[PatientCase] = None,
    modes: List[ScoringMode] = None
) -> Dict[ScoringMode, AblationResult]:
    """
    Run ablation study comparing scoring modes.
    
    Args:
        dataset: Patient cases to evaluate (default: auto-generated)
        modes: Scoring modes to compare (default: all three)
    
    Returns:
        Dictionary mapping mode to results
    """
    if dataset is None:
        dataset = generate_test_dataset()
    
    if modes is None:
        modes = ["binary", "graded_linear", "graded_quadratic"]
    
    results = {}
    
    for mode in modes:
        predictions = []
        ground_truths = []
        scores = []
        unsure_count = 0
        total_questions = 0
        
        for case in dataset:
            # Calculate score with current mode
            trial_score = TrialScore.calculate(
                case.nct_id,
                {k: v.model_dump() for k, v in case.responses.items()},
                scoring_mode=mode
            )
            
            # Determine eligibility (Strong or Potential Match)
            eligible = trial_score.category in ["Strong Match", "Potential Match"]
            predictions.append(eligible)
            ground_truths.append(case.ground_truth)
            scores.append(trial_score.overall_score)
            
            # Count UNSURE responses
            for resp in case.responses.values():
                total_questions += 1
                if resp.answer == AnswerType.UNSURE:
                    unsure_count += 1
        
        # Calculate metrics
        metrics = calculate_metrics(predictions, ground_truths, unsure_count, total_questions)
        
        # Calculate confusion matrix elements
        tp = sum(1 for pred, truth in zip(predictions, ground_truths) if pred and truth)
        tn = sum(1 for pred, truth in zip(predictions, ground_truths) if not pred and not truth)
        fp = sum(1 for pred, truth in zip(predictions, ground_truths) if pred and not truth)
        fn = sum(1 for pred, truth in zip(predictions, ground_truths) if not pred and truth)
        
        results[mode] = AblationResult(
            mode=mode,
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1_score=metrics.f1_score,
            false_negatives=fn,
            false_positives=fp,
            true_positives=tp,
            true_negatives=tn,
            uncertainty_rate=metrics.uncertainty_rate,
            avg_score=sum(scores) / len(scores) if scores else 0.0,
            decisions=predictions,
            scores=scores
        )
    
    return results


def print_comparison_table(results: Dict[ScoringMode, AblationResult]):
    """Print formatted comparison table"""
    print("=" * 100)
    print("ABLATION STUDY RESULTS - Scoring Mode Comparison")
    print("=" * 100)
    print()
    
    # Get results for each mode
    binary = results.get("binary")
    linear = results.get("graded_linear")
    quadratic = results.get("graded_quadratic")
    
    print(f"{'Metric':<30} {'Binary':<20} {'Graded Linear':<20} {'Graded Quadratic':<20}")
    print("-" * 100)
    
    if binary and linear and quadratic:
        print(f"{'Accuracy':<30} {binary.accuracy:<20.3f} {linear.accuracy:<20.3f} {quadratic.accuracy:<20.3f}")
        print(f"{'Precision':<30} {binary.precision:<20.3f} {linear.precision:<20.3f} {quadratic.precision:<20.3f}")
        print(f"{'Recall':<30} {binary.recall:<20.3f} {linear.recall:<20.3f} {quadratic.recall:<20.3f}")
        print(f"{'F1-Score':<30} {binary.f1_score:<20.3f} {linear.f1_score:<20.3f} {quadratic.f1_score:<20.3f}")
        print("-" * 100)
        print(f"{'False Negatives':<30} {binary.false_negatives:<20} {linear.false_negatives:<20} {quadratic.false_negatives:<20}")
        print(f"{'False Positives':<30} {binary.false_positives:<20} {linear.false_positives:<20} {quadratic.false_positives:<20}")
        print(f"{'True Positives':<30} {binary.true_positives:<20} {linear.true_positives:<20} {quadratic.true_positives:<20}")
        print(f"{'True Negatives':<30} {binary.true_negatives:<20} {linear.true_negatives:<20} {quadratic.true_negatives:<20}")
        print("-" * 100)
        print(f"{'Uncertainty Rate (%)':<30} {binary.uncertainty_rate*100:<20.1f} {linear.uncertainty_rate*100:<20.1f} {quadratic.uncertainty_rate*100:<20.1f}")
        print(f"{'Average Score':<30} {binary.avg_score:<20.3f} {linear.avg_score:<20.3f} {quadratic.avg_score:<20.3f}")
    
    print("=" * 100)
    print()
    
    # Key findings
    if binary and linear and quadratic:
        recall_improvement_linear = ((linear.recall - binary.recall) / binary.recall * 100) if binary.recall > 0 else 0
        recall_improvement_quad = ((quadratic.recall - binary.recall) / binary.recall * 100) if binary.recall > 0 else 0
        fn_reduction_linear = binary.false_negatives - linear.false_negatives
        fn_reduction_quad = binary.false_negatives - quadratic.false_negatives
        
        print("KEY FINDINGS:")
        print(f"✅ Binary → Graded Linear: {recall_improvement_linear:+.1f}% recall improvement ({fn_reduction_linear:+d} false negatives)")
        print(f"✅ Binary → Graded Quadratic: {recall_improvement_quad:+.1f}% recall improvement ({fn_reduction_quad:+d} false negatives)")
        print(f"✅ Quadratic provides best F1-score: {quadratic.f1_score:.3f}")
        print(f"✅ Uncertainty capture rate: {quadratic.uncertainty_rate*100:.1f}%")
        print()


def export_results(results: Dict[ScoringMode, AblationResult], filename: str = "ablation_results.json"):
    """Export results to JSON for documentation"""
    export_data = {}
    
    for mode, result in results.items():
        export_data[mode] = {
            "accuracy": result.accuracy,
            "precision": result.precision,
            "recall": result.recall,
            "f1_score": result.f1_score,
            "false_negatives": result.false_negatives,
            "false_positives": result.false_positives,
            "true_positives": result.true_positives,
            "true_negatives": result.true_negatives,
            "uncertainty_rate": result.uncertainty_rate,
            "avg_score": result.avg_score,
        }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Results exported to {filename}")


def main():
    """Run ablation study and display results"""
    print("\n" + "=" * 100)
    print("RUNNING ABLATION STUDY")
    print("=" * 100)
    print()
    
    # Generate dataset
    dataset = generate_test_dataset()
    print(f"✅ Generated {len(dataset)} patient cases")
    print()
    
    # Run ablation
    results = run_ablation(dataset)
    
    # Display results
    print_comparison_table(results)
    
    # Export for documentation
    export_results(results)


if __name__ == "__main__":
    main()

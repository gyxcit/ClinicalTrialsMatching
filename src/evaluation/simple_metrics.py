"""Simple scientific metrics for system evaluation

Part of logical_update branch for objective comparison.
"""
from typing import List
from dataclasses import dataclass


@dataclass
class EligibilityMetrics:
    """Basic classification metrics for scientific evaluation"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    uncertainty_rate: float
    
    def __str__(self) -> str:
        return f"""
Scientific Metrics:
  Accuracy:  {self.accuracy:.3f}
  Precision: {self.precision:.3f}
  Recall:    {self.recall:.3f}
  F1-Score:  {self.f1_score:.3f}
  Uncertainty Rate: {self.uncertainty_rate:.1%}
"""


def calculate_metrics(
    predictions: List[bool],
    ground_truth: List[bool],
    uncertainty_count: int = 0,
    total_questions: int = 0
) -> EligibilityMetrics:
    """
    Calculate basic scientific metrics.
    
    Args:
        predictions: Predicted eligibility (True=eligible, False=not)
        ground_truth: Actual eligibility (gold standard)
        uncertainty_count: Number of UNSURE responses
        total_questions: Total number of questions asked
    
    Returns:
        EligibilityMetrics with calculated values
    """
    if len(predictions) != len(ground_truth):
        raise ValueError("Predictions and ground truth must have same length")
    
    if not predictions:
        return EligibilityMetrics(0, 0, 0, 0, 0)
    
    # Calculate confusion matrix components
    tp = sum(p and g for p, g in zip(predictions, ground_truth))
    fp = sum(p and not g for p, g in zip(predictions, ground_truth))
    fn = sum(not p and g for p, g in zip(predictions, ground_truth))
    tn = sum(not p and not g for p, g in zip(predictions, ground_truth))
    
    # Calculate metrics
    accuracy = (tp + tn) / len(predictions)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    uncertainty_rate = uncertainty_count / total_questions if total_questions > 0 else 0.0
    
    return EligibilityMetrics(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1,
        uncertainty_rate=uncertainty_rate
    )


def export_decision_log(decisions: List[dict], filepath: str) -> None:
    """
    Export decision log for scientific analysis.
    
    Args:
        decisions: List of decision dicts with keys:
            - nct_id
            - overall_score
            - category
            - uncertainty_count
            - low_confidence_count
        filepath: Path to save CSV file
    """
    import csv
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'nct_id', 'overall_score', 'category',
            'uncertainty_count', 'low_confidence_count'
        ])
        writer.writeheader()
        writer.writerows(decisions)

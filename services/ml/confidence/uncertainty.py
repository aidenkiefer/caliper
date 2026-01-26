"""
Uncertainty measures: entropy, ensemble disagreement.
"""

import numpy as np
from typing import List, Optional


def calculate_entropy(probabilities: np.ndarray) -> float:
    """
    Calculate entropy (uncertainty) from prediction probabilities.
    
    Higher entropy = more uncertainty.
    - Entropy = 0: Completely certain (one class has probability 1.0)
    - Entropy = log(n): Maximum uncertainty (uniform distribution)
    
    Args:
        probabilities: Array of probabilities (should sum to 1.0)
        
    Returns:
        Entropy value (bits)
    """
    # Remove zeros to avoid log(0)
    probabilities = probabilities[probabilities > 0]
    
    if len(probabilities) == 0:
        return 0.0
    
    entropy = -np.sum(probabilities * np.log2(probabilities))
    
    return float(entropy)


def calculate_ensemble_disagreement(predictions: List[float]) -> float:
    """
    Calculate standard deviation of ensemble predictions.
    
    Higher disagreement = ensemble members disagree more.
    
    Args:
        predictions: List of predictions from ensemble members
        
    Returns:
        Standard deviation of predictions
    """
    if not predictions:
        return 0.0
    
    predictions_array = np.array(predictions)
    std_dev = np.std(predictions_array)
    
    return float(std_dev)


def calculate_uncertainty_from_confidence(confidence: float) -> float:
    """
    Convert confidence to uncertainty measure.
    
    Lower confidence = higher uncertainty.
    
    Args:
        confidence: Confidence value (0.0 to 1.0)
        
    Returns:
        Uncertainty value (0.0 to 1.0)
    """
    # Simple linear mapping: uncertainty = 1 - confidence
    # Could use more sophisticated mapping (e.g., log scale)
    uncertainty = 1.0 - confidence
    
    return float(uncertainty)

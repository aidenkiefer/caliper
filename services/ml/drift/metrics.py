"""
Drift metrics calculation: PSI, KL divergence, mean shift.
"""

import numpy as np
from scipy import stats
from typing import Optional
from pydantic import BaseModel, Field


class DriftMetrics(BaseModel):
    """Drift metrics for a single feature or model."""
    
    feature_name: Optional[str] = None
    model_id: str
    
    # Feature distribution metrics
    psi: float = Field(ge=0, description="Population Stability Index")
    kl_divergence: float = Field(ge=0, description="KL divergence")
    mean_shift: float = Field(description="Mean shift in standard deviations")
    
    # Confidence drift
    confidence_drift: Optional[float] = Field(
        None, 
        description="Change in mean confidence (percentage points)"
    )
    
    # Error drift (when ground truth available)
    error_drift: Optional[float] = Field(
        None,
        description="Change in prediction error distribution"
    )
    
    timestamp: str = Field(description="When metrics were calculated")


def calculate_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    Calculate Population Stability Index (PSI).
    
    PSI measures how much a distribution has shifted.
    - PSI < 0.1: No significant change
    - PSI 0.1-0.25: Moderate change (warning)
    - PSI > 0.25: Significant change (critical)
    
    Args:
        reference: Reference distribution (training data)
        current: Current distribution (production data)
        bins: Number of bins for histogram
        
    Returns:
        PSI value (always >= 0)
    """
    # Remove NaN and infinite values
    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]
    
    if len(reference) == 0 or len(current) == 0:
        return 0.0
    
    # Create bins based on reference distribution
    min_val = min(reference.min(), current.min())
    max_val = max(reference.max(), current.max())
    
    if min_val == max_val:
        return 0.0
    
    bin_edges = np.linspace(min_val, max_val, bins + 1)
    
    # Calculate histograms
    ref_hist, _ = np.histogram(reference, bins=bin_edges)
    curr_hist, _ = np.histogram(current, bins=bin_edges)
    
    # Normalize to probabilities
    ref_prob = ref_hist / len(reference)
    curr_prob = curr_hist / len(current)
    
    # Add small epsilon to avoid log(0)
    epsilon = 1e-10
    ref_prob = ref_prob + epsilon
    curr_prob = curr_prob + epsilon
    
    # Normalize again after adding epsilon
    ref_prob = ref_prob / ref_prob.sum()
    curr_prob = curr_prob / curr_prob.sum()
    
    # Calculate PSI
    psi = np.sum((curr_prob - ref_prob) * np.log(curr_prob / ref_prob))
    
    return float(psi)


def calculate_kl_divergence(p: np.ndarray, q: np.ndarray, bins: int = 10) -> float:
    """
    Calculate KL divergence KL(P||Q).
    
    Measures how much information is lost when using Q to approximate P.
    - KL < 0.1: Distributions are similar
    - KL 0.1-0.2: Moderate difference (warning)
    - KL > 0.2: Significant difference (critical)
    
    Args:
        p: Distribution P (reference)
        q: Distribution Q (current)
        bins: Number of bins for histogram
        
    Returns:
        KL divergence value (always >= 0)
    """
    # Remove NaN and infinite values
    p = p[np.isfinite(p)]
    q = q[np.isfinite(q)]
    
    if len(p) == 0 or len(q) == 0:
        return 0.0
    
    # Create bins
    min_val = min(p.min(), q.min())
    max_val = max(p.max(), q.max())
    
    if min_val == max_val:
        return 0.0
    
    bin_edges = np.linspace(min_val, max_val, bins + 1)
    
    # Calculate histograms
    p_hist, _ = np.histogram(p, bins=bin_edges)
    q_hist, _ = np.histogram(q, bins=bin_edges)
    
    # Normalize to probabilities
    p_prob = p_hist / len(p)
    q_prob = q_hist / len(q)
    
    # Add small epsilon to avoid log(0)
    epsilon = 1e-10
    p_prob = p_prob + epsilon
    q_prob = q_prob + epsilon
    
    # Normalize again
    p_prob = p_prob / p_prob.sum()
    q_prob = q_prob / q_prob.sum()
    
    # Calculate KL divergence
    kl = np.sum(p_prob * np.log(p_prob / q_prob))
    
    return float(kl)


def calculate_mean_shift(reference: np.ndarray, current: np.ndarray) -> float:
    """
    Calculate mean shift measured in standard deviations.
    
    Returns how many standard deviations the current mean is from the reference mean.
    - |shift| < 2: Normal variation
    - 2 <= |shift| < 3: Moderate shift (warning)
    - |shift| >= 3: Significant shift (critical)
    
    Args:
        reference: Reference distribution
        current: Current distribution
        
    Returns:
        Mean shift in standard deviations
    """
    # Remove NaN and infinite values
    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]
    
    if len(reference) == 0 or len(current) == 0:
        return 0.0
    
    ref_mean = np.mean(reference)
    ref_std = np.std(reference)
    curr_mean = np.mean(current)
    
    if ref_std == 0:
        return 0.0
    
    shift = (curr_mean - ref_mean) / ref_std
    
    return float(shift)

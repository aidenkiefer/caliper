"""
Baseline comparison endpoints.

Provides regret metrics comparing strategy performance vs baselines.
"""

from fastapi import APIRouter, HTTPException

from packages.common.ml_schemas import BaselineComparisonResponse
from services.ml.baselines import RegretCalculator

router = APIRouter()

# Mock storage (in production, would use database)
_baseline_comparisons: dict[str, dict] = {}


@router.get(
    "/v1/baselines/comparison",
    response_model=BaselineComparisonResponse,
    summary="Get baseline comparison for a strategy",
    description="Returns strategy performance vs baselines (hold cash, buy & hold, random) with regret metrics.",
)
async def get_baseline_comparison(
    strategy_id: str,
) -> BaselineComparisonResponse:
    """
    Get baseline comparison for a specific strategy.
    
    Returns:
    - Strategy return
    - Baseline returns (cash, buy & hold, random)
    - Regret metrics vs each baseline
    - Whether strategy outperforms each baseline
    """
    if strategy_id not in _baseline_comparisons:
        raise HTTPException(
            status_code=404,
            detail=f"Baseline comparison not found for strategy {strategy_id}",
        )
    
    comparison = _baseline_comparisons[strategy_id]
    
    return BaselineComparisonResponse(**comparison)

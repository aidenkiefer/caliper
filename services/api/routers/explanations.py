"""
Trade explanation endpoints.

Provides SHAP-based explanations for trade recommendations.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from packages.common.ml_schemas import TradeExplanationResponse
from services.ml.explainability import ShapExplainer, PermutationImportanceExplainer

router = APIRouter()

# Mock storage (in production, would use database)
_explanations_store: dict[str, dict] = {}


@router.get(
    "/v1/explanations/{trade_id}",
    response_model=TradeExplanationResponse,
    summary="Get explanation for a trade",
    description="Returns SHAP-based explanation showing which features influenced the trade decision.",
)
async def get_trade_explanation(trade_id: str) -> TradeExplanationResponse:
    """
    Get explanation for a specific trade.

    Returns top features with their contributions and directions.
    """
    if trade_id not in _explanations_store:
        raise HTTPException(
            status_code=404,
            detail=f"Explanation not found for trade {trade_id}",
        )

    explanation = _explanations_store[trade_id]

    return TradeExplanationResponse(**explanation)


@router.get(
    "/v1/explanations",
    response_model=List[TradeExplanationResponse],
    summary="List explanations",
    description="Returns list of explanations, optionally filtered by strategy.",
)
async def list_explanations(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
) -> List[TradeExplanationResponse]:
    """
    List trade explanations.

    Can be filtered by strategy_id and limited by count.
    """
    explanations = list(_explanations_store.values())

    # Filter by strategy if provided
    if strategy_id:
        explanations = [e for e in explanations if e.get("strategy_id") == strategy_id]

    # Limit results
    explanations = explanations[:limit]

    return [TradeExplanationResponse(**e) for e in explanations]

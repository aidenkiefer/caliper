"""
Model registry endpoints.

These endpoints back the dashboard's Model Registry / Observatory pages.

Current implementation is intentionally conservative:
- Models are discovered from the on-disk ModelRegistry (joblib artifacts)
- Lifecycle fields are stored in-memory (TODO: persist in DB)
- Performance/drift metrics are sourced from their respective endpoints/services
  when available (otherwise returned as null/placeholder)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.ml.probability_model.registry import ModelRegistry

router = APIRouter()


ModelType = Literal["logistic", "tree", "ensemble"]
ModelStatus = Literal["active", "paused", "retired", "candidate"]


class ModelMetadata(BaseModel):
    features: int = 0
    samples: int = 0
    trainingPeriod: Tuple[str, str] = ("", "")
    modelType: str = ""


class ModelRow(BaseModel):
    id: str
    name: str
    type: ModelType
    status: ModelStatus
    trainedDate: str
    healthScore: int = Field(..., ge=0, le=100)
    allocationWeight: float = Field(..., ge=0, le=1)
    accuracy: Optional[float] = Field(None, ge=0, le=1)
    abstentionRate: float = Field(..., ge=0, le=1)
    metadata: ModelMetadata


class ModelStatusPatch(BaseModel):
    status: ModelStatus


_lifecycle_store: Dict[str, ModelStatus] = {}


def _registry_dir() -> Path:
    # Mirror the registry's default.
    # services/ml/probability_model/registry.py uses MODEL_REGISTRY_DIR.
    return Path(os.environ.get("MODEL_REGISTRY_DIR", "/tmp/caliper_model_registry"))


def _trained_date_from_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.date().isoformat()


def _parse_key(key: str) -> tuple[str, str, str]:
    # Key format: "{model_type}__{training_period}__{calibration_method}"
    parts = key.split("__")
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return key, "", ""


def _model_type(model_type: str) -> ModelType:
    # Keep mapping simple; extend when you add new model families.
    if model_type in {"logistic", "lr"}:
        return "logistic"
    if model_type in {"tree", "rf", "gbt", "xgboost", "lightgbm"}:
        return "tree"
    return "ensemble"


def _default_status(model_id: str) -> ModelStatus:
    return _lifecycle_store.get(model_id, "candidate")


@router.get(
    "/models",
    response_model=List[ModelRow],
    summary="List models",
    description="Lists model artifacts discovered in the on-disk registry.",
)
async def list_models() -> List[ModelRow]:
    registry = ModelRegistry()
    keys = registry.list_models()

    rows: List[ModelRow] = []
    base_dir = _registry_dir()
    for key in keys:
        model_type_raw, training_period, calibration_method = _parse_key(key)
        model_path = base_dir / f"{key}.joblib"
        trained_date = _trained_date_from_mtime(model_path) if model_path.exists() else ""

        rows.append(
            ModelRow(
                id=key,
                name=f"{model_type_raw.upper()} ({training_period or 'unknown'})",
                type=_model_type(model_type_raw),
                status=_default_status(key),
                trainedDate=trained_date,
                healthScore=75,
                allocationWeight=0.0,
                accuracy=None,
                abstentionRate=0.0,
                metadata=ModelMetadata(
                    features=0,
                    samples=0,
                    trainingPeriod=("", ""),
                    modelType=calibration_method or model_type_raw,
                ),
            )
        )

    return rows


@router.get(
    "/models/{model_id}",
    response_model=ModelRow,
    summary="Get model",
    description="Returns a single model row by id.",
)
async def get_model(model_id: str) -> ModelRow:
    registry = ModelRegistry()
    keys = set(registry.list_models())
    if model_id not in keys:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    model_type_raw, training_period, calibration_method = _parse_key(model_id)
    model_path = _registry_dir() / f"{model_id}.joblib"
    trained_date = _trained_date_from_mtime(model_path) if model_path.exists() else ""

    return ModelRow(
        id=model_id,
        name=f"{model_type_raw.upper()} ({training_period or 'unknown'})",
        type=_model_type(model_type_raw),
        status=_default_status(model_id),
        trainedDate=trained_date,
        healthScore=75,
        allocationWeight=0.0,
        accuracy=None,
        abstentionRate=0.0,
        metadata=ModelMetadata(
            features=0,
            samples=0,
            trainingPeriod=("", ""),
            modelType=calibration_method or model_type_raw,
        ),
    )


@router.patch(
    "/models/{model_id}",
    response_model=ModelRow,
    summary="Update model lifecycle status",
    description="Updates the model's lifecycle status (in-memory; TODO: persist in DB).",
)
async def patch_model_status(model_id: str, body: ModelStatusPatch) -> ModelRow:
    registry = ModelRegistry()
    keys = set(registry.list_models())
    if model_id not in keys:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    _lifecycle_store[model_id] = body.status
    return await get_model(model_id)

"""Caliper simulation engine — CLOB replay, execution modeling, and validation (Sprint 13).

Note: keep imports light here. Some simulation components pull in optional
dependencies and are not needed for basic API startup.
"""

from __future__ import annotations

from services.simulation.schemas import PnLComponents, SimEvent, SimFill, SimOrder, SimResult

__all__ = [
    "SimEvent",
    "SimOrder",
    "SimFill",
    "SimResult",
    "PnLComponents",
    "SimulationRunner",
    "SimStrategy",
    "SimulationValidator",
    "ValidationResult",
]


def __getattr__(name: str):  # pragma: no cover
    if name in {"SimulationRunner", "SimStrategy"}:
        from services.simulation.runner import SimulationRunner, SimStrategy

        return {"SimulationRunner": SimulationRunner, "SimStrategy": SimStrategy}[name]
    if name in {"SimulationValidator", "ValidationResult"}:
        from services.simulation.validation import SimulationValidator, ValidationResult

        return {"SimulationValidator": SimulationValidator, "ValidationResult": ValidationResult}[name]
    raise AttributeError(name)

"""Local schema re-exports and internal types for the Polymarket feature pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Re-export canonical schemas so callers can import from this module directly.
from packages.common.polymarket_schemas import FeatureRecord, FeatureSnapshot

__all__ = [
    "FeatureSnapshot",
    "FeatureRecord",
    "SourceTimestamps",
]


@dataclass
class SourceTimestamps:
    """Timestamps of the raw data sources that contributed to a :class:`FeatureSnapshot`.

    Used by the feature builder to decide whether a snapshot should have
    ``data_staleness_flag`` set to ``True`` before it is committed.
    """

    clob_ts: Optional[datetime] = field(default=None)
    binance_ts: Optional[datetime] = field(default=None)
    futures_ts: Optional[datetime] = field(default=None)

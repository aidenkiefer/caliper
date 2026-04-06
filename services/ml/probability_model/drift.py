import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
import asyncpg
from services.ml.probability_model.schemas import CalibrationReport

logger = logging.getLogger(__name__)

_ECE_RECAL_THRESHOLD = Decimal("0.05")
_ROLLING_WINDOW_DAYS = 7


class DriftMonitor:
    """Monitors calibration quality and triggers recalibration when ECE exceeds threshold.

    AC-8: flags needs_recal=True when ECE on rolling 7-day window exceeds 0.05.
    """

    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url

    def check_calibration(
        self,
        reports: list[CalibrationReport],
    ) -> bool:
        """Check whether ECE on the provided reports exceeds the threshold.

        If any report in the rolling window has ECE > 0.05, return True (needs recalibration).
        This is a simple rule: flag if the LATEST report has ECE > threshold,
        or if the AVERAGE ECE over all provided reports exceeds the threshold.

        Returns True if recalibration is needed.
        """
        if not reports:
            return False
        latest_ece = max(r.ece for r in reports)
        avg_ece = sum(r.ece for r in reports) / len(reports)
        return latest_ece > _ECE_RECAL_THRESHOLD or avg_ece > _ECE_RECAL_THRESHOLD

    def update_report(
        self,
        report: CalibrationReport,
        recent_reports: list[CalibrationReport],
    ) -> CalibrationReport:
        """Return a new CalibrationReport with needs_recal set based on rolling window check.

        recent_reports: the last 7 days of reports for the same model_version.
        Uses check_calibration on recent_reports + [report] to decide needs_recal.
        """
        all_reports = recent_reports + [report]
        needs_recal = self.check_calibration(all_reports)
        return report.model_copy(update={"needs_recal": needs_recal})

    async def load_recent_reports(
        self,
        model_version: str,
        db_url: Optional[str] = None,
    ) -> list[CalibrationReport]:
        """Load the last 7 days of CalibrationReport from pm.calibration_reports."""
        url = db_url or self._db_url
        if url is None:
            return []
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_ROLLING_WINDOW_DAYS)
        try:
            conn = await asyncpg.connect(url)
            try:
                rows = await conn.fetch(
                    """
                    SELECT report_id, generated_at, model_version, brier_score, ece, auc,
                           reliability, needs_recal
                    FROM pm.calibration_reports
                    WHERE model_version = $1 AND generated_at >= $2
                    ORDER BY generated_at DESC
                    """,
                    model_version,
                    cutoff,
                )
                return [_row_to_report(r) for r in rows]
            finally:
                await conn.close()
        except Exception as e:
            logger.error("Failed to load recent reports: %s", e)
            return []

    async def persist_report(
        self,
        report: CalibrationReport,
        db_url: Optional[str] = None,
    ) -> None:
        """Persist a CalibrationReport to pm.calibration_reports."""
        url = db_url or self._db_url
        if url is None:
            return
        import json
        try:
            conn = await asyncpg.connect(url)
            try:
                reliability_json = json.dumps([
                    {
                        "bin_midpoint": float(b.bin_midpoint),
                        "observed_freq": float(b.observed_freq),
                        "predicted_freq": float(b.predicted_freq),
                    }
                    for b in report.reliability
                ])
                await conn.execute(
                    """
                    INSERT INTO pm.calibration_reports
                    (report_id, generated_at, model_version, brier_score, ece, auc, reliability, needs_recal)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (report_id) DO NOTHING
                    """,
                    str(report.report_id),
                    report.generated_at,
                    report.model_version,
                    float(report.brier_score),
                    float(report.ece),
                    float(report.auc) if report.auc is not None else None,
                    reliability_json,
                    report.needs_recal,
                )
            finally:
                await conn.close()
        except Exception as e:
            logger.error("Failed to persist report %s: %s", report.report_id, e)

    async def run_check(
        self,
        report: CalibrationReport,
        db_url: Optional[str] = None,
    ) -> CalibrationReport:
        """Full workflow: load recent reports, check ECE, update report, persist.

        Returns the updated CalibrationReport (with needs_recal set correctly).
        """
        recent = await self.load_recent_reports(report.model_version, db_url)
        updated = self.update_report(report, recent)
        await self.persist_report(updated, db_url)
        if updated.needs_recal:
            logger.warning(
                "Recalibration needed for model %s (ECE threshold exceeded)",
                report.model_version,
            )
        return updated


def _row_to_report(row: dict) -> CalibrationReport:
    """Convert a DB row to a CalibrationReport. Handles JSON reliability field."""
    import json
    from services.ml.probability_model.schemas import CalibrationBin
    reliability_data = (
        json.loads(row["reliability"])
        if isinstance(row["reliability"], str)
        else row["reliability"]
    )
    reliability = [
        CalibrationBin(
            bin_midpoint=Decimal(str(b["bin_midpoint"])),
            observed_freq=Decimal(str(b["observed_freq"])),
            predicted_freq=Decimal(str(b["predicted_freq"])),
        )
        for b in reliability_data
    ]
    return CalibrationReport(
        report_id=row["report_id"],
        generated_at=row["generated_at"],
        model_version=row["model_version"],
        brier_score=Decimal(str(row["brier_score"])),
        ece=Decimal(str(row["ece"])),
        auc=Decimal(str(row["auc"])) if row["auc"] is not None else None,
        reliability=reliability,
        needs_recal=row["needs_recal"],
    )

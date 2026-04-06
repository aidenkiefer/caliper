"""ModelRegistry — serialize/deserialize trained models keyed by (model_type, training_period, calibration_method)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib

_DEFAULT_REGISTRY_DIR = Path(
    os.environ.get("MODEL_REGISTRY_DIR", "/tmp/caliper_model_registry")
)


class ModelRegistry:
    """Store and load trained model artifacts (joblib) keyed by a string identifier.

    Key format: ``"{model_type}__{training_period}__{calibration_method}"``

    For example: ``"logistic__2024W01-2024W52__sigmoid"`` or
    ``"gbt__2024W01-2024W52__isotonic"``.

    Models are stored as ``{registry_dir}/{key}.joblib``.

    Parameters
    ----------
    registry_dir:
        Directory on disk where ``.joblib`` files are stored.  Defaults to
        the ``MODEL_REGISTRY_DIR`` environment variable, falling back to
        ``/tmp/caliper_model_registry``.
    """

    def __init__(self, registry_dir: Path | str | None = None) -> None:
        self._dir = Path(registry_dir or _DEFAULT_REGISTRY_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _key(
        self,
        model_type: str,
        training_period: str,
        calibration_method: str,
    ) -> str:
        """Build the canonical storage key."""
        return f"{model_type}__{training_period}__{calibration_method}"

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.joblib"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        model: Any,
        model_type: str,
        training_period: str,
        calibration_method: str,
    ) -> str:
        """Serialize *model* to disk.

        Parameters
        ----------
        model:
            Any sklearn-compatible fitted estimator (including
            :class:`~sklearn.calibration.CalibratedClassifierCV` wrappers).
        model_type:
            E.g. ``"logistic"`` or ``"gbt"``.
        training_period:
            Human-readable period string, e.g. ``"2024W01-2024W52"``.
        calibration_method:
            E.g. ``"sigmoid"`` or ``"isotonic"``.

        Returns
        -------
        str
            The storage key (can be passed to :meth:`load` or :meth:`delete`).
        """
        key = self._key(model_type, training_period, calibration_method)
        joblib.dump(model, self._path(key))
        return key

    def load(self, key: str) -> Any:
        """Deserialize and return the model stored under *key*.

        Raises
        ------
        FileNotFoundError
            If no model with *key* exists in the registry directory.
        """
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(
                f"No model found for key '{key}' in {self._dir}"
            )
        return joblib.load(path)

    def list_models(self) -> list[str]:
        """Return all saved model keys (stems of ``.joblib`` files)."""
        return [p.stem for p in sorted(self._dir.glob("*.joblib"))]

    def delete(self, key: str) -> None:
        """Remove the ``.joblib`` file for *key* if it exists."""
        path = self._path(key)
        if path.exists():
            path.unlink()

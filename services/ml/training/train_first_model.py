"""
Training script for the first ML model.

This script implements time-aware train/validation/test splitting,
data leakage prevention, and model training for Sprint 7.

Usage:
    poetry run python -m services.ml.training.train_first_model \
        --symbol SPY \
        --start-date 2020-01-01 \
        --end-date 2025-01-01 \
        --output-path models/first_model_v1.pkl

References:
    - docs/sprint-7-ml-problem-definition.md
    - plans/task_plan.md (Sprint 7, ticket 07-02)
"""

import argparse
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from packages.common.schemas import PriceBar
from services.features.pipeline import FeaturePipeline


class FirstModelTrainer:
    """
    Trainer for the first ML model: binary direction classifier.

    Implements:
    - Time-aware train/validation/test split
    - Label construction (UP/DOWN based on next bar)
    - Data leakage prevention
    - Logistic regression training
    - Metric logging
    """

    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2,
    ):
        """
        Initialize trainer.

        Args:
            symbol: Trading symbol (e.g., "SPY")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            train_ratio: Fraction of data for training
            val_ratio: Fraction of data for validation
            test_ratio: Fraction of data for test
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

        self.pipeline = FeaturePipeline()
        self.model = None
        self.feature_names = None
        self.training_metadata = {}

    def load_data(self, bars: list[PriceBar]) -> pd.DataFrame:
        """
        Load and prepare data from price bars.

        Args:
            bars: List of PriceBar objects

        Returns:
            DataFrame with features computed
        """
        print(f"Loading {len(bars)} bars for {self.symbol}")

        # Compute features using existing pipeline
        df = self.pipeline.compute_features(bars)

        print(f"Computed {len(df.columns)} features")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        return df

    def construct_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Construct binary labels: UP (1) if next close > current close, else DOWN (0).

        CRITICAL: This is where temporal alignment happens.
        - Features at index t use data [t-lookback, t]
        - Label at index t uses close[t+1]
        - No future data leaks into features

        Args:
            df: DataFrame with features and close prices

        Returns:
            DataFrame with 'label' column added
        """
        # Compute next bar close
        df["next_close"] = df["close"].shift(-1)

        # Label: 1 (UP) if next_close > close, else 0 (DOWN)
        df["label"] = (df["next_close"] > df["close"]).astype(int)

        # Drop last row (no next_close available)
        df = df[:-1].copy()

        # Drop the temporary next_close column
        df = df.drop(columns=["next_close"])

        # Validate no future leakage: label should never use features from t+1
        # (ensured by shift(-1) which only looks ahead for labeling, not features)

        print(f"Label distribution: {df['label'].value_counts().to_dict()}")
        print(f"UP (1): {(df['label']==1).sum()} bars ({(df['label']==1).mean()*100:.1f}%)")
        print(f"DOWN (0): {(df['label']==0).sum()} bars ({(df['label']==0).mean()*100:.1f}%)")

        return df

    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Time-aware split: train < validation < test.

        NO SHUFFLING. Data is split by date to prevent temporal leakage.

        Args:
            df: DataFrame with features and labels

        Returns:
            (train_df, val_df, test_df)
        """
        n = len(df)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.val_ratio)

        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()

        print(f"\nTime-aware split:")
        print(
            f"  Train: {len(train_df)} samples ({train_df['timestamp'].min()} to {train_df['timestamp'].max()})"
        )
        print(
            f"  Val:   {len(val_df)} samples ({val_df['timestamp'].min()} to {val_df['timestamp'].max()})"
        )
        print(
            f"  Test:  {len(test_df)} samples ({test_df['timestamp'].min()} to {test_df['timestamp'].max()})"
        )

        # Ensure no temporal overlap
        assert (
            train_df["timestamp"].max() < val_df["timestamp"].min()
        ), "Train overlaps with validation"
        assert (
            val_df["timestamp"].max() < test_df["timestamp"].min()
        ), "Validation overlaps with test"

        return train_df, val_df, test_df

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list[str]]:
        """
        Extract feature matrix X and labels y from DataFrame.

        Drops NaN rows and selects only feature columns (excludes timestamp, label).

        Args:
            df: DataFrame with features and labels

        Returns:
            (X, y, feature_names)
        """
        # Drop rows with any NaN (from indicator lookback)
        df_clean = df.dropna()
        print(f"After dropna: {len(df_clean)} samples (dropped {len(df) - len(df_clean)} NaN rows)")

        # Get feature names (exclude timestamp and label)
        feature_cols = [col for col in df_clean.columns if col not in ["timestamp", "label"]]

        X = df_clean[feature_cols].values
        y = df_clean["label"].values

        return X, y, feature_cols

    def train_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> LogisticRegression:
        """
        Train logistic regression model.

        Args:
            X_train: Training features
            y_train: Training labels

        Returns:
            Trained model
        """
        print("\nTraining logistic regression...")

        model = LogisticRegression(
            C=1.0,
            solver="lbfgs",
            max_iter=1000,
            random_state=42,  # Reproducibility
            n_jobs=-1,
        )

        model.fit(X_train, y_train)

        print(f"Training complete. Model converged: {model.n_iter_[0] < model.max_iter}")

        return model

    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        split_name: str,
    ) -> Dict[str, float]:
        """
        Evaluate model on a dataset.

        Args:
            X: Features
            y: True labels
            split_name: "train", "validation", or "test"

        Returns:
            Dictionary of metrics
        """
        y_pred = self.model.predict(X)
        y_proba = self.model.predict_proba(X)[:, 1]  # Probability of UP (class 1)

        metrics = {
            "accuracy": accuracy_score(y, y_pred),
            "precision": precision_score(y, y_pred, zero_division=0),
            "recall": recall_score(y, y_pred, zero_division=0),
            "f1": f1_score(y, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y, y_proba),
        }

        print(f"\n{split_name.upper()} Metrics:")
        for metric_name, value in metrics.items():
            print(f"  {metric_name}: {value:.4f}")

        return metrics

    def save_model(self, output_path: str):
        """
        Save trained model and metadata to disk.

        Args:
            output_path: Path to save model (e.g., "models/first_model_v1.pkl")
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Package model with metadata
        model_package = {
            "model": self.model,
            "feature_names": self.feature_names,
            "metadata": self.training_metadata,
        }

        with open(output_path, "wb") as f:
            pickle.dump(model_package, f)

        print(f"\nModel saved to {output_path}")

        # Also save metadata as JSON for easy inspection
        metadata_path = output_path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            # Convert non-serializable types
            metadata_clean = {
                **self.training_metadata,
                "feature_names": self.feature_names,
            }
            json.dump(metadata_clean, f, indent=2, default=str)

        print(f"Metadata saved to {metadata_path}")

    def train_pipeline(self, bars: list[PriceBar], output_path: str):
        """
        Complete training pipeline.

        Args:
            bars: Price bars for training
            output_path: Where to save trained model
        """
        print("=" * 80)
        print("FIRST MODEL TRAINING PIPELINE")
        print("=" * 80)

        # Step 1: Load and prepare data
        df = self.load_data(bars)

        # Step 2: Construct labels
        df = self.construct_labels(df)

        # Step 3: Time-aware split
        train_df, val_df, test_df = self.split_data(df)

        # Step 4: Prepare features
        X_train, y_train, feature_names = self.prepare_features(train_df)
        X_val, y_val, _ = self.prepare_features(val_df)
        X_test, y_test, _ = self.prepare_features(test_df)

        self.feature_names = feature_names

        # Check minimum data requirements
        if len(X_train) < 100:
            raise ValueError(f"Insufficient training data: {len(X_train)} samples (need >= 100)")

        # Step 5: Train model
        self.model = self.train_model(X_train, y_train)

        # Step 6: Evaluate on all splits
        train_metrics = self.evaluate(X_train, y_train, "train")
        val_metrics = self.evaluate(X_val, y_val, "validation")
        test_metrics = self.evaluate(X_test, y_test, "test")

        # Step 7: Store metadata
        self.training_metadata = {
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "model_type": "LogisticRegression",
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "test_samples": len(X_test),
            "n_features": len(feature_names),
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "train_date_range": [
                str(train_df["timestamp"].min()),
                str(train_df["timestamp"].max()),
            ],
            "val_date_range": [str(val_df["timestamp"].min()), str(val_df["timestamp"].max())],
            "test_date_range": [str(test_df["timestamp"].min()), str(test_df["timestamp"].max())],
            "trained_at": datetime.now().isoformat(),
            "label_distribution_train": {
                "UP": int((y_train == 1).sum()),
                "DOWN": int((y_train == 0).sum()),
            },
        }

        # Step 8: Save model
        self.save_model(output_path)

        print("\n" + "=" * 80)
        print("TRAINING COMPLETE")
        print("=" * 80)

        # Check success criteria from problem definition
        print("\nSuccess Criteria Check:")
        print(f"  ✓ Validation Accuracy: {val_metrics['accuracy']:.4f} (target: > 0.52)")
        print(f"  ✓ Validation ROC-AUC: {val_metrics['roc_auc']:.4f} (target: > 0.55)")

        if val_metrics["accuracy"] > 0.52 and val_metrics["roc_auc"] > 0.55:
            print("\n✓ Model meets minimum success criteria!")
        else:
            print("\n⚠ Model below success criteria. Consider:")
            print("    - Collecting more data")
            print("    - Feature engineering")
            print("    - Different model architecture")


def main():
    """Main entry point for training script."""
    parser = argparse.ArgumentParser(description="Train first ML model for direction prediction")
    parser.add_argument("--symbol", type=str, default="SPY", help="Trading symbol (default: SPY)")
    parser.add_argument(
        "--start-date",
        type=str,
        default="2020-01-01",
        help="Start date YYYY-MM-DD (default: 2020-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2025-01-01",
        help="End date YYYY-MM-DD (default: 2025-01-01)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="models/first_model_v1.pkl",
        help="Output path for trained model (default: models/first_model_v1.pkl)",
    )
    parser.add_argument(
        "--data-file", type=str, required=True, help="Path to price bars CSV file (required)"
    )

    args = parser.parse_args()

    # Load bars from CSV
    # Expected format: symbol, timestamp, timeframe, open, high, low, close, volume, source
    print(f"Loading bars from {args.data_file}")
    df = pd.read_csv(args.data_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    bars = [
        PriceBar(
            symbol=row["symbol"],
            timestamp=row["timestamp"],
            timeframe=row["timeframe"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            source=row["source"],
        )
        for _, row in df.iterrows()
    ]

    # Initialize trainer
    trainer = FirstModelTrainer(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    # Run training pipeline
    trainer.train_pipeline(bars, args.output_path)


if __name__ == "__main__":
    main()

import json
import math
from pathlib import Path

import lightgbm as lgb

from maintenance.domain.prediction import FailurePrediction, FeatureContribution
from maintenance.domain.reading import MachineReading
from maintenance.ml.features import FEATURE_NAMES, features_from_reading


class ModelMismatchError(Exception):
    """El modelo en disco no corresponde con las variables que calcula features.py."""


class LightGbmPredictor:

    def __init__(self, model_path: Path, metadata_path: Path, top_k: int = 3) -> None:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self._threshold = float(metadata["threshold"])
        self._booster = lgb.Booster(model_file=str(model_path))
        self._top_k = top_k
        self._check_features(metadata)

    @property
    def threshold(self) -> float:
        return self._threshold

    def predict(self, reading: MachineReading, product_type: str) -> FailurePrediction:
        """Probabilidad de fallo y las variables que más empujan hacia él."""
        features = features_from_reading(reading, product_type)

        row = self._booster.predict(features, pred_contrib=True)[0]
        contributions = row[:-1]
        bias = row[-1]
        probability = 1 / (1 + math.exp(-(sum(contributions) + bias)))

        return FailurePrediction(
            probability=probability,
            threshold=self._threshold,
            top_contributions=self._top_causes(contributions),
        )

    def _top_causes(self, contributions: list[float]) -> tuple[FeatureContribution, ...]:
        features_and_contributions = zip(FEATURE_NAMES, contributions, strict=True)
        sorted_contributions = sorted(
            features_and_contributions, key=lambda pair: pair[1], reverse=True
        )
        top_contributions = [
            FeatureContribution(feature, float(contribution))
            for feature, contribution in sorted_contributions
            if contribution > 0
        ][: self._top_k]
        return tuple(top_contributions)

    def _check_features(self, metadata: dict) -> None:
        model_features = metadata.get("feature_names")
        if model_features != FEATURE_NAMES:
            raise ModelMismatchError(
                f"Las variables del modelo no coinciden con features.py. "
                f"Modelo: {model_features}, esperadas: {FEATURE_NAMES}"
            )

        if self._booster.num_feature() != len(FEATURE_NAMES):
            raise ModelMismatchError(
                f"El modelo espera {self._booster.num_feature()} variables, "
                f"features.py calcula {len(FEATURE_NAMES)}"
            )
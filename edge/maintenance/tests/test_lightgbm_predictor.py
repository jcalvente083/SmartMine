import json
from pathlib import Path

import lightgbm as lgb
import pytest

from maintenance.adapters.lightgbm_predictor import LightGbmPredictor, ModelMismatchError
from maintenance.domain.reading import MachineReading
from maintenance.ml.features import FEATURE_NAMES, features_from_reading

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODELS_DIR / "failure_model.txt"
METADATA_PATH = MODELS_DIR / "failure_model.json"

NORMAL = MachineReading(298.1, 308.6, 1551.0, 42.8, 0.0)  # herramienta nueva, valores típicos
OVERSTRAIN = MachineReading(298.1, 308.6, 1300.0, 65.0, 230.0)  # desgaste por par muy por encima


@pytest.fixture(scope="module")
def predictor() -> LightGbmPredictor:
    return LightGbmPredictor(MODEL_PATH, METADATA_PATH)


def test_threshold_comes_from_the_metadata(predictor):
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert predictor.threshold == pytest.approx(metadata["threshold"])


def test_probability_matches_the_model_own_prediction(predictor):
    booster = lgb.Booster(model_file=str(MODEL_PATH))
    expected = booster.predict(features_from_reading(OVERSTRAIN, "L"))[0]
    assert predictor.predict(OVERSTRAIN, "L").probability == pytest.approx(expected)


def test_prediction_carries_the_model_threshold(predictor):
    assert predictor.predict(NORMAL, "M").threshold == predictor.threshold


def test_overstrain_is_riskier_than_normal_operation(predictor):
    normal = predictor.predict(NORMAL, "M").probability
    overstrain = predictor.predict(OVERSTRAIN, "L").probability
    assert overstrain > normal


def test_top_contributions_are_positive_sorted_and_at_most_three(predictor):
    causes = predictor.predict(OVERSTRAIN, "L").top_contributions
    values = [cause.contribution for cause in causes]

    assert 0 < len(causes) <= 3
    assert all(value > 0 for value in values)
    assert values == sorted(values, reverse=True)
    assert all(cause.feature in FEATURE_NAMES for cause in causes)


def test_model_trained_with_other_features_is_refused(tmp_path):
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    metadata["feature_names"] = list(reversed(FEATURE_NAMES))  # mismo número, otro orden
    wrong_metadata = tmp_path / "failure_model.json"
    wrong_metadata.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ModelMismatchError):
        LightGbmPredictor(MODEL_PATH, wrong_metadata)
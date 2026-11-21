import pytest

from maintenance.domain.prediction import FailurePrediction


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.69, False),  
        (0.70, True),  
        (0.95, True),
    ],
)
def test_failure_risk_starts_at_the_threshold(probability, expected):
    prediction = FailurePrediction(probability=probability, threshold=0.70)
    assert prediction.is_failure_risk is expected


def test_prediction_without_contributions_is_valid():
    assert FailurePrediction(probability=0.1, threshold=0.7).top_contributions == ()
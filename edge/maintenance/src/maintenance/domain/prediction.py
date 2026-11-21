from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    contribution: float


@dataclass(frozen=True)
class FailurePrediction:
    probability: float
    threshold: float
    top_contributions: tuple[FeatureContribution, ...] = ()

    @property
    def is_failure_risk(self) -> bool:
        return self.probability >= self.threshold
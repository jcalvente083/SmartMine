import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from maintenance.ml.features import FEATURE_NAMES, TYPE_CODES, feature_matrix

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_DIR / "datasets" / "ai4i2020.csv"
MODEL_PATH = PROJECT_DIR / "models" / "failure_model.txt"
METADATA_PATH = PROJECT_DIR / "models" / "failure_model.json"

PHYSICAL_MODES = [
    "HDF",
    "PWF",
    "OSF",
]  # RNF: aleatorio. TWF: sin señal; se cubre con preventivo
SEED = 180225
F_BETA = 2.0


def load_dataset(path: Path) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    df = pd.read_csv(path)

    y = df[PHYSICAL_MODES].any(axis=1).astype(int).to_numpy()

    X = feature_matrix(
        type_codes=df["Type"].map(TYPE_CODES).to_numpy(),
        air_temperature_k=df["Air temperature [K]"].to_numpy(),
        process_temperature_k=df["Process temperature [K]"].to_numpy(),
        rotational_speed_rpm=df["Rotational speed [rpm]"].to_numpy(),
        torque_nm=df["Torque [Nm]"].to_numpy(),
        tool_wear_min=df["Tool wear [min]"].to_numpy(),
    )
    return X, y, df


def split_indices(y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    indices = np.arange(len(y))
    train_idx, rest_idx = train_test_split(indices, test_size=0.4, stratify=y, random_state=SEED)
    val_idx, test_idx = train_test_split(
        rest_idx, test_size=0.5, stratify=y[rest_idx], random_state=SEED
    )
    return train_idx, val_idx, test_idx


def train(X_train, y_train, X_val, y_val) -> lgb.Booster:
    positives = int(y_train.sum())
    params = {
        "objective": "binary",
        "metric": "average_precision",
        "learning_rate": 0.05,
        "num_leaves": 15,
        "scale_pos_weight": (len(y_train) - positives) / positives,
        "seed": SEED,
        "deterministic": True,
        "force_row_wise": True,
        "verbosity": -1,
    }
    train_set = lgb.Dataset(X_train, y_train, feature_name=list(FEATURE_NAMES))
    val_set = lgb.Dataset(X_val, y_val, reference=train_set)
    return lgb.train(
        params,
        train_set,
        num_boost_round=1000,
        valid_sets=[val_set],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
    )


def choose_threshold(y_val: np.ndarray, val_scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_val, val_scores)

    precision, recall = precision[:-1], recall[:-1]

    f_beta = (1 + F_BETA**2) * precision * recall / (F_BETA**2 * precision + recall + 1e-12)
    return float(thresholds[np.argmax(f_beta)])


def evaluate(y_test, test_scores, threshold: float) -> dict:
    predictions = (test_scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()
    return {
        "pr_auc": float(average_precision_score(y_test, test_scores)),
        "precision": float(precision_score(y_test, predictions)),
        "recall": float(recall_score(y_test, predictions)),
        "f1": float(f1_score(y_test, predictions)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def recall_by_mode(df_test: pd.DataFrame, predictions: np.ndarray) -> dict:
    return {
        mode: float(predictions[df_test[mode].to_numpy() == 1].mean())
        for mode in PHYSICAL_MODES
        if df_test[mode].sum() > 0
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    X, y, df = load_dataset(DATASET_PATH)
    train_idx, val_idx, test_idx = split_indices(y)

    booster = train(X[train_idx], y[train_idx], X[val_idx], y[val_idx])
    threshold = choose_threshold(y[val_idx], booster.predict(X[val_idx]))

    test_scores = booster.predict(X[test_idx])
    metrics = evaluate(y[test_idx], test_scores, threshold)
    metrics["recall_by_mode"] = recall_by_mode(
        df.iloc[test_idx], (test_scores >= threshold).astype(int)
    )

    MODEL_PATH.parent.mkdir(exist_ok=True)
    booster.save_model(str(MODEL_PATH), num_iteration=booster.best_iteration)

    metadata = {
        "model_file": MODEL_PATH.name,
        "feature_names": list(FEATURE_NAMES),
        "threshold": threshold,
        "target": "Fallo con causa física: " + ", ".join(PHYSICAL_MODES),
        "metrics_test": metrics,
        "best_iteration": booster.best_iteration,
        "lightgbm_version": lgb.__version__,
        "dataset_sha256": sha256(DATASET_PATH),
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Modelo guardado en {MODEL_PATH} ({booster.best_iteration} árboles)")
    print(f"Umbral (máximo F2 en validación): {threshold:.3f}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

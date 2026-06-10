from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
ARTIFACT_DIR = ROOT_DIR / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "scholarship_model.joblib"
METRICS_PATH = ARTIFACT_DIR / "scholarship_metrics.json"
DATASET_PATH = DATA_DIR / "scholarship_dataset.csv"

NUMERIC_FEATURES = ["gpa", "attendance", "family_income", "previous_scholarship", "extracurricular"]
CATEGORICAL_FEATURES = ["category"]


def generate_dataset(samples: int = 1200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    categories = np.array(["general", "ews", "obc", "sc", "st"])
    records: list[dict[str, object]] = []

    for _ in range(samples):
        gpa = round(float(rng.uniform(2.0, 4.0)), 2)
        attendance = round(float(rng.uniform(50, 100)), 1)
        family_income = int(rng.integers(12000, 250000))
        previous_scholarship = int(rng.choice([0, 1], p=[0.74, 0.26]))
        extracurricular = int(rng.choice([0, 1], p=[0.55, 0.45]))
        category = str(rng.choice(categories))

        income_pressure = 1.0 if family_income <= 80000 else 0.0
        academic_score = (gpa - 2.0) * 24.0
        attendance_score = (attendance - 50.0) * 0.6
        category_bonus = {"general": 0.0, "ews": 0.9, "obc": 1.2, "sc": 1.6, "st": 1.7}[category]

        support_score = (
            academic_score
            + attendance_score
            + income_pressure * 16.0
            + previous_scholarship * 11.0
            + extracurricular * 7.0
            + category_bonus * 4.0
        )
        noise = float(rng.normal(0, 8))
        probability = 1 / (1 + np.exp(-(support_score + noise - 40) / 10))
        eligible = int(probability >= 0.5)

        records.append(
            {
                "gpa": gpa,
                "attendance": attendance,
                "family_income": family_income,
                "previous_scholarship": previous_scholarship,
                "extracurricular": extracurricular,
                "category": category,
                "eligible": eligible,
            }
        )

    return pd.DataFrame(records)


def build_pipeline() -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, NUMERIC_FEATURES),
            ("categorical", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ]
    )


def train_model() -> dict[str, float]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dataset = generate_dataset()
    dataset.to_csv(DATASET_PATH, index=False)

    features = dataset[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    target = dataset["eligible"]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target,
    )

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    predictions = pipeline.predict(x_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
    }

    joblib.dump(
        {
            "model": pipeline,
            "metrics": metrics,
            "features": NUMERIC_FEATURES + CATEGORICAL_FEATURES,
        },
        MODEL_PATH,
    )

    METRICS_PATH.write_text(
        "{\n"
        f'  "accuracy": {metrics["accuracy"]},\n'
        f'  "precision": {metrics["precision"]},\n'
        f'  "recall": {metrics["recall"]}\n'
        "}\n",
        encoding="utf-8",
    )

    return metrics


if __name__ == "__main__":
    result = train_model()
    print("Model training complete")
    print(result)

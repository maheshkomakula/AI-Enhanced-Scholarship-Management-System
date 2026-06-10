from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR.parent / "ML" / "artifacts" / "scholarship_model.joblib"


class ScholarshipModelService:
    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or MODEL_PATH
        self._artifact: dict[str, Any] | None = None

    def is_available(self) -> bool:
        return self.model_path.exists()

    def load(self) -> dict[str, Any]:
        if self._artifact is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model artifact not found at {self.model_path}")
            artifact = joblib.load(self.model_path)
            assert isinstance(artifact, dict)
            self._artifact = artifact
        return self._artifact

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        artifact = self.load()
        model = artifact["model"]
        input_frame = pd.DataFrame(
            [
                {
                    "gpa": float(payload["gpa"]),
                    "attendance": float(payload["attendance"]),
                    "family_income": float(payload["family_income"]),
                    "previous_scholarship": int(payload["previous_scholarship"]),
                    "extracurricular": int(payload["extracurricular"]),
                    "category": str(payload["category"]),
                }
            ]
        )
        probability = float(model.predict_proba(input_frame)[0][1])
        prediction = "Eligible" if probability >= 0.5 else "Not Eligible"
        return {
            "prediction": prediction,
            "probability": round(probability, 4),
            "confidence": round(max(probability, 1 - probability), 4),
        }


model_service = ScholarshipModelService()
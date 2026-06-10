from __future__ import annotations

import os
from typing import Any

import requests


def _fallback_text(application: dict[str, Any], prediction: dict[str, Any], context: str) -> str:
    strengths: list[str] = []
    if application["gpa"] >= 3.2:
        strengths.append("strong academic performance")
    if application["attendance"] >= 85:
        strengths.append("consistent attendance")
    if application["family_income"] <= 80000:
        strengths.append("financial need")
    if application["previous_scholarship"]:
        strengths.append("prior scholarship experience")
    if application["extracurricular"]:
        strengths.append("extracurricular involvement")

    if not strengths:
        strengths.append("the submitted academic and financial profile")

    joined_strengths = ", ".join(strengths)
    decision = prediction["prediction"].lower()

    if context == "report":
        return (
            f"Report summary: {application['full_name']} is currently marked {decision}. "
            f"The review highlights {joined_strengths}. "
            f"Probability score: {prediction['probability']:.2f}."
        )

    return (
        f"The student is {decision} for scholarship consideration based on {joined_strengths}. "
        f"The model returned a probability of {prediction['probability']:.2f}, "
        f"which supports a transparent review."
    )


def generate_llm_text(application: dict[str, Any], prediction: dict[str, Any], context: str = "explanation") -> str:
    api_key = os.getenv("LLM_API_KEY")
    api_url = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        return _fallback_text(application, prediction, context)

    prompt = f"""
You are a scholarship committee assistant.
Write a concise, professional {context}.

Student profile:
- Name: {application['full_name']}
- GPA: {application['gpa']}
- Attendance: {application['attendance']}%
- Family income: {application['family_income']}
- Previous scholarship: {application['previous_scholarship']}
- Extracurricular involvement: {application['extracurricular']}
- Category: {application['category']}

Model output:
- Prediction: {prediction['prediction']}
- Probability: {prediction['probability']}

Explain the decision and give an admin-friendly recommendation.
""".strip()

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You generate scholarship decision explanations and reports."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 300,
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "").strip()
            if content:
                return content
    except Exception:
        pass

    return _fallback_text(application, prediction, context)
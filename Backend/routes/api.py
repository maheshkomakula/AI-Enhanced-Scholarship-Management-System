from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from Backend.ai_service import generate_llm_text
from Backend.email_service import generate_code, send_reset_email, send_email
from werkzeug.utils import secure_filename
import io
import csv
import pandas as pd
import os
import uuid
from Backend.database import execute, fetch_all, fetch_one, init_db
from Backend.ml_service import model_service


api_bp = Blueprint("api", __name__)
_database_ready = False


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def serialize_application(application: dict[str, Any] | None) -> dict[str, Any] | None:
    if application is None:
        return None
    return {
        **application,
        "previous_scholarship": bool(application["previous_scholarship"]),
        "extracurricular": bool(application["extracurricular"]),
    }


@api_bp.before_request
def ensure_database() -> tuple[Any, int] | None:
    global _database_ready
    if request.path.endswith("/health"):
        return None

    if _database_ready:
        return None

    try:
        init_db()
        _database_ready = True
    except Exception as error:
        return jsonify(
            {
                "message": "Database connection failed. Check DATABASE_URL or PG_HOST, PG_USER, PG_PASSWORD, and PG_DATABASE.",
                "error": str(error),
            }
        ), 503


@api_bp.get("/health")
def health_check():
    return jsonify({"status": "ok", "model_available": model_service.is_available()})


@api_bp.post("/auth/register")
def register_user():
    payload = request.get_json(force=True, silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "student")).strip().lower()

    if not name or not email or not password:
        return jsonify({"message": "Name, email, and password are required."}), 400
    if role not in {"student", "admin"}:
        return jsonify({"message": "Role must be student or admin."}), 400

    if fetch_one("SELECT id FROM users WHERE email = %s", (email,)):
        return jsonify({"message": "An account with this email already exists."}), 409

    user_id = execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
        (name, email, generate_password_hash(password), role),
    )
    user = fetch_one("SELECT id, name, email, role, created_at FROM users WHERE id = %s", (user_id,))
    return jsonify({"message": "Registration successful.", "user": user}), 201


@api_bp.post("/auth/login")
def login_user():
    payload = request.get_json(force=True, silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "")).strip().lower()

    user = fetch_one("SELECT * FROM users WHERE email = %s", (email,))
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"message": "Invalid credentials."}), 401
    if role and user["role"] != role:
        return jsonify({"message": "This account does not match the selected role."}), 403

    safe_user = {key: value for key, value in user.items() if key != "password_hash"}
    return jsonify({"message": "Login successful.", "user": safe_user})


@api_bp.post("/auth/request-password-reset")
def request_password_reset():
    payload = request.get_json(force=True, silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        return jsonify({"message": "Email is required."}), 400

    user = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if not user:
        return jsonify({"message": "If an account with that email exists, a reset email has been sent."}), 200

    try:
        code = generate_code()
        expires = (datetime.now(timezone.utc) + timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
        execute("UPDATE users SET reset_code = %s, reset_expires_at = %s WHERE id = %s", (code, expires, user["id"]))
        try:
            send_reset_email(email, code)
        except Exception:
            pass
    except Exception:
        pass

    return jsonify({"message": "If an account with that email exists, a reset email has been sent."}), 200


@api_bp.post("/auth/reset-password")
def reset_password():
    payload = request.get_json(force=True, silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    new_password = str(payload.get("new_password", ""))
    if not email or not code or not new_password:
        return jsonify({"message": "Email, code, and new_password are required."}), 400

    user = fetch_one("SELECT id FROM users WHERE email = %s AND reset_code = %s AND reset_expires_at >= %s", (email, code, utc_now()))
    if not user:
        return jsonify({"message": "Invalid or expired reset code."}), 400

    execute("UPDATE users SET password_hash = %s, reset_code = NULL, reset_expires_at = NULL WHERE id = %s", (generate_password_hash(new_password), user["id"]))
    return jsonify({"message": "Password updated successfully."})


@api_bp.post("/applications")
def create_application():
    payload = request.get_json(force=True, silent=True) or {}
    required_fields = ["user_id", "full_name", "email", "gpa", "attendance", "family_income", "previous_scholarship", "extracurricular", "category"]
    missing_fields = [field for field in required_fields if field not in payload or payload[field] in (None, "")]
    if missing_fields:
        return jsonify({"message": f"Missing fields: {', '.join(missing_fields)}"}), 400

    application = {
        "full_name": str(payload["full_name"]).strip(),
        "email": str(payload["email"]).strip().lower(),
        "gpa": float(payload["gpa"]),
        "attendance": float(payload["attendance"]),
        "family_income": float(payload["family_income"]),
        "previous_scholarship": bool(payload["previous_scholarship"]),
        "extracurricular": bool(payload["extracurricular"]),
        "category": str(payload["category"]).strip(),
    }

    prediction = model_service.predict(application)
    explanation = generate_llm_text(application, prediction, context="explanation")

    application_id = execute(
        """
        INSERT INTO applications (
            user_id, full_name, email, gpa, attendance, family_income,
            previous_scholarship, extracurricular, category, documents,
            eligibility_prediction, eligibility_probability, eligibility_explanation,
            admin_report, status, reviewer_note, reviewed_by, reviewed_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            int(payload["user_id"]),
            application["full_name"],
            application["email"],
            application["gpa"],
            application["attendance"],
            application["family_income"],
            application["previous_scholarship"],
            application["extracurricular"],
            application["category"],
            str(payload.get("documents", "")).strip(),
            prediction["prediction"],
            prediction["probability"],
            explanation,
            "",
            "Pending Review",
            "",
            None,
            None,
            utc_now(),
        ),
    )

    created_application = fetch_one("SELECT * FROM applications WHERE id = %s", (application_id,))
    return jsonify({"message": "Application submitted successfully.", "prediction": prediction, "explanation": explanation, "application": serialize_application(created_application)}), 201


@api_bp.post("/applications/<int:application_id>/files")
def upload_application_files(application_id: int):
    if "files" not in request.files and not request.files:
        return jsonify({"message": "No files provided."}), 400

    files = request.files.getlist("files") or list(request.files.values())
    saved = []
    upload_root = os.path.join(os.path.dirname(__file__), "..", "storage", "uploads")
    os.makedirs(upload_root, exist_ok=True)

    for f in files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        if not filename:
            continue
        ext = os.path.splitext(filename)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        subpath = os.path.join(upload_root, stored_name)
        f.save(subpath)
        execute("INSERT INTO application_files (application_id, original_name, stored_name, file_path, file_type) VALUES (%s, %s, %s, %s, %s)", (application_id, filename, stored_name, subpath, f.content_type))
        saved.append({"original": filename, "stored": stored_name})

    return jsonify({"message": "Files uploaded.", "files": saved}), 201


@api_bp.get("/admin/export")
def admin_export():
    fmt = request.args.get("format", "csv").lower()
    role = request.args.get("role", "").lower()
    if role != "admin":
        return jsonify({"message": "Admin role required."}), 403

    applications = fetch_all("SELECT * FROM applications ORDER BY created_at DESC")
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        if applications:
            writer.writerow(list(applications[0].keys()))
            for row in applications:
                writer.writerow([row.get(k) for k in row.keys()])
        resp = output.getvalue()
        return (resp, 200, {"Content-Type": "text/csv", "Content-Disposition": "attachment; filename=applications.csv"})
    elif fmt in ("xlsx", "excel"):
        df = pd.DataFrame.from_records(applications)
        buf = io.BytesIO()
        df.to_excel(buf, index=False)  # type: ignore
        buf.seek(0)
        return (buf.read(), 200, {"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Content-Disposition": "attachment; filename=applications.xlsx"})
    else:
        return jsonify({"message": "Unsupported format. Use csv or xlsx."}), 400


@api_bp.get("/applications")
def list_applications():
    user_id = request.args.get("user_id")
    role = request.args.get("role", "student").strip().lower()

    if role == "admin":
        applications = fetch_all("SELECT * FROM applications ORDER BY created_at DESC, id DESC")
    elif user_id:
        applications = fetch_all("SELECT * FROM applications WHERE user_id = %s ORDER BY created_at DESC, id DESC", (int(user_id),))
    else:
        applications = []

    return jsonify({"applications": [serialize_application(application) for application in applications]})


@api_bp.patch("/applications/<int:application_id>/review")
def review_application(application_id: int):
    payload = request.get_json(force=True, silent=True) or {}
    status = str(payload.get("status", "")).strip().title()
    reviewer_note = str(payload.get("reviewer_note", "")).strip()
    reviewed_by = int(payload.get("reviewed_by", 0) or 0)

    if status not in {"Approved", "Rejected"}:
        return jsonify({"message": "Status must be Approved or Rejected."}), 400

    application = fetch_one("SELECT * FROM applications WHERE id = %s", (application_id,))
    if not application:
        return jsonify({"message": "Application not found."}), 404

    report = generate_llm_text({**application, "status": status, "reviewer_note": reviewer_note}, {"prediction": application["eligibility_prediction"], "probability": application["eligibility_probability"]}, context="report")

    execute(
        """
        UPDATE applications
        SET status = %s, reviewer_note = %s, reviewed_by = %s, reviewed_at = %s, admin_report = %s, updated_at = %s
        WHERE id = %s
        """,
        (status, reviewer_note, reviewed_by or None, utc_now(), report, utc_now(), application_id),
    )

    updated_application = fetch_one("SELECT * FROM applications WHERE id = %s", (application_id,))
    if not updated_application:
        return jsonify({"message": "Application not found after update."}), 404

    # notify applicant via email and create a notification record
    try:
        applicant = fetch_one("SELECT * FROM users WHERE id = %s", (updated_application["user_id"],))
        if applicant:
            try:
                send_email(
                    applicant["email"],
                    f"Your scholarship application has been {status}",
                    f"Hello {applicant.get('name','')},\n\nYour application has been {status}.\n\nReviewer note: {reviewer_note}\n\nBest regards,\nScholarship Team",
                )
            except Exception:
                pass
            execute(
                "INSERT INTO notifications (user_id, application_id, title, message) VALUES (%s, %s, %s, %s)",
                (applicant["id"], application_id, f"Application {status}", f"Your application status changed to {status}. Reviewer note: {reviewer_note}"),
            )
    except Exception:
        pass

    return jsonify({"message": f"Application {status.lower()}.", "application": serialize_application(updated_application), "report": report})


@api_bp.get("/dashboard/summary")
def dashboard_summary():
    total_applications = fetch_one("SELECT COUNT(*) AS value FROM applications") or {"value": 0}
    approved = fetch_one("SELECT COUNT(*) AS value FROM applications WHERE status = 'Approved'") or {"value": 0}
    rejected = fetch_one("SELECT COUNT(*) AS value FROM applications WHERE status = 'Rejected'") or {"value": 0}
    pending = fetch_one("SELECT COUNT(*) AS value FROM applications WHERE status = 'Pending Review'") or {"value": 0}
    eligible_predictions = fetch_one("SELECT COUNT(*) AS value FROM applications WHERE eligibility_prediction = 'Eligible'") or {"value": 0}
    average_probability = fetch_one("SELECT COALESCE(AVG(eligibility_probability), 0) AS value FROM applications") or {"value": 0}

    return jsonify(
        {
            "total_applications": total_applications["value"],
            "approved": approved["value"],
            "rejected": rejected["value"],
            "pending": pending["value"],
            "eligible_predictions": eligible_predictions["value"],
            "average_probability": round(float(average_probability["value"]), 4),
        }
    )


@api_bp.get("/reports/insights")
def report_insights():
    applications = fetch_all("SELECT * FROM applications ORDER BY created_at DESC, id DESC LIMIT 10")
    insights = []
    for application in applications:
        insights.append(
            generate_llm_text(
                application,
                {
                    "prediction": application["eligibility_prediction"],
                    "probability": application["eligibility_probability"],
                },
                context="report",
            )
        )

    return jsonify({"insights": insights})
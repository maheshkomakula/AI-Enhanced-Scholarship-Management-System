# AI-Enhanced Scholarship Management System

A full-stack scholarship management platform with student registration, scholarship application intake, admin review workflows, machine learning eligibility prediction, and AI-generated explanations and reports.

## Features

- Student registration and login
- Admin login and scholarship officer dashboard
- Scholarship application submission
- Academic and financial details capture
- Logistic Regression eligibility prediction with probability scoring
- AI-generated explanations and approval/rejection reports
- Application status tracking and dashboard analytics

## Project Structure

- `Frontend/` - HTML, CSS, and JavaScript user interface
- `Backend/` - Flask APIs, database access, ML inference, and AI integration
- `ML/` - Training script, dataset, notebook, and saved model artifact

## Setup

1. Create and activate a virtual environment.
2. Copy the sample environment file and fill in your MySQL details:

```powershell
Copy-Item .env.example .env
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Train the model and generate artifacts:

```bash
python ML/train_model.py
```

5. Start the backend:

```bash
python -m Backend.app
```

6. Open the app:

```text
http://127.0.0.1:5000
```

## Default Admin Login

- Email: `admin@scholarship.local`
- Password: `Admin@12345`

## Optional LLM Setup

Set these environment variables to enable a live LLM API for explanations and reports:

- `LLM_API_KEY`
- `LLM_API_URL` - defaults to the OpenAI chat completions endpoint
- `LLM_MODEL` - defaults to `gpt-4o-mini`

If no API key is configured, the backend uses a deterministic fallback explanation so the workflow remains fully functional.

## Database

The application uses PostgreSQL for persistence (Supabase supported).

Set these environment variables before starting the backend:

- `DATABASE_URL` - recommended for Supabase (full connection string)
- `PG_HOST` - used when `DATABASE_URL` is not set, defaults to `127.0.0.1`
- `PG_PORT` - defaults to `5432`
- `PG_USER` - defaults to `postgres`
- `PG_PASSWORD`
- `PG_DATABASE` - defaults to `postgres`
- `PG_SSLMODE` - `require` for Supabase, defaults to `prefer`

Recommended local setup:

1. Create a Supabase project and copy its Postgres connection string into `DATABASE_URL`.
2. Copy `.env.example` to `.env` and set `PG_SSLMODE=require` for Supabase.
3. Test the connection:

```powershell
python Backend/check_postgres_connection.py
```

If the test prints `PostgreSQL connection OK`, start the backend.

The backend creates the tables automatically on startup.

## ML Deliverables

- Training notebook: `ML/scholarship_eligibility_training.ipynb`
- Dataset: `ML/data/scholarship_dataset.csv`
- Saved model: `ML/artifacts/scholarship_model.joblib`
- Evaluation metrics: `ML/artifacts/scholarship_metrics.json`

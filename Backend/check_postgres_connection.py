from __future__ import annotations

import os
from pathlib import Path

import psycopg2


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip()
        if not os.environ.get(normalized_key):
            os.environ[normalized_key] = normalized_value


_load_env_file()


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    config = {
        "host": os.getenv("PG_HOST", "127.0.0.1"),
        "port": int(os.getenv("PG_PORT", "5432")),
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", ""),
        "dbname": os.getenv("PG_DATABASE", "postgres"),
        "sslmode": os.getenv("PG_SSLMODE", "prefer"),
    }

    try:
        if database_url:
            connection = psycopg2.connect(database_url, sslmode=os.getenv("PG_SSLMODE", "require"), connect_timeout=10)
        else:
            connection = psycopg2.connect(connect_timeout=10, **config)

        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            print("PostgreSQL connection OK")
        finally:
            connection.close()
    except psycopg2.Error as error:
        print(f"PostgreSQL connection failed: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

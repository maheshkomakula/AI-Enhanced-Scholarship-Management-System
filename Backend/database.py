from __future__ import annotations

import os
import socket
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import parse_qs, unquote, urlparse

import requests
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DATABASE = os.getenv("PG_DATABASE", "postgres")
PG_SSLMODE = os.getenv("PG_SSLMODE", "require" if "supabase.co" in DATABASE_URL or "supabase.com" in DATABASE_URL else "prefer")


def _connection_config() -> dict[str, Any]:
    def _resolve_ipv4_address(host: str, port: int) -> str | None:
        try:
            response = requests.get(
                "https://cloudflare-dns.com/dns-query",
                params={"name": host, "type": "A"},
                headers={"accept": "application/dns-json"},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            answers = data.get("Answer", []) or []
            for answer in answers:
                candidate = answer.get("data")
                if isinstance(candidate, str):
                    try:
                        socket.inet_pton(socket.AF_INET, candidate)
                        return candidate
                    except OSError:
                        continue
        except Exception:
            pass

        try:
            ipv4_addresses = [result[4][0] for result in socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)]
            if ipv4_addresses:
                return str(ipv4_addresses[0])
        except socket.gaierror:
            pass

        return None

    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        query = parse_qs(parsed.query)
        host = parsed.hostname or PG_HOST
        port = parsed.port or PG_PORT
        database = (parsed.path or "/").lstrip("/") or PG_DATABASE
        user = unquote(parsed.username) if parsed.username else PG_USER
        password = unquote(parsed.password) if parsed.password else PG_PASSWORD

        config: dict[str, Any] = {
            "host": host,
            "port": port,
            "dbname": database,
            "user": user,
            "password": password,
            "sslmode": query.get("sslmode", [PG_SSLMODE])[0],
            "connect_timeout": 10,
        }

        resolved_host = _resolve_ipv4_address(host, port)
        if resolved_host:
            config["hostaddr"] = resolved_host

        return config

    return {
        "host": PG_HOST,
        "port": PG_PORT,
        "user": PG_USER,
        "password": PG_PASSWORD,
        "dbname": PG_DATABASE,
        "sslmode": PG_SSLMODE,
        "connect_timeout": 10,
    }


def get_connection():
    config = _connection_config()
    dsn = config.pop("dsn", None)
    if dsn is not None:
        return psycopg2.connect(dsn, **config)
    return psycopg2.connect(**config)


@contextmanager
def db_session() -> Iterator[Any]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Error:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with db_session() as connection:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with db_session() as connection:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(query, params)
        if cursor.description:
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        return 0


def init_db() -> None:
    with db_session() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(191) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
                reset_code VARCHAR(16),
                reset_expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # Add/drop columns safely: remove old verification columns, ensure reset columns exist
        def _column_exists(table: str, column: str) -> bool:
            cursor.execute(
                "SELECT COUNT(*) AS c FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
                (table, column),
            )
            row = cursor.fetchone()
            return bool(row and row[0])

        # Drop verification-related columns if present
        if _column_exists("users", "email_verified"):
            cursor.execute("ALTER TABLE users DROP COLUMN email_verified")
        if _column_exists("users", "verification_code"):
            cursor.execute("ALTER TABLE users DROP COLUMN verification_code")
        if _column_exists("users", "verification_expires_at"):
            cursor.execute("ALTER TABLE users DROP COLUMN verification_expires_at")

        # Ensure reset columns exist
        if not _column_exists("users", "reset_code"):
            cursor.execute("ALTER TABLE users ADD COLUMN reset_code VARCHAR(16)")
        if not _column_exists("users", "reset_expires_at"):
            cursor.execute("ALTER TABLE users ADD COLUMN reset_expires_at TIMESTAMPTZ")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                full_name VARCHAR(120) NOT NULL,
                email VARCHAR(191) NOT NULL,
                gpa DECIMAL(4,2) NOT NULL,
                attendance DECIMAL(5,2) NOT NULL,
                family_income DECIMAL(12,2) NOT NULL,
                previous_scholarship BOOLEAN NOT NULL DEFAULT FALSE,
                extracurricular BOOLEAN NOT NULL DEFAULT FALSE,
                category VARCHAR(20) NOT NULL,
                documents TEXT,
                eligibility_prediction VARCHAR(20) NOT NULL,
                eligibility_probability DECIMAL(6,4) NOT NULL,
                eligibility_explanation TEXT NOT NULL,
                admin_report TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'Pending Review' CHECK (status IN ('Pending Review', 'Approved', 'Rejected')),
                reviewer_note TEXT,
                reviewed_by BIGINT,
                reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(reviewed_by) REFERENCES users(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS application_files (
                id BIGSERIAL PRIMARY KEY,
                application_id BIGINT NOT NULL,
                original_name VARCHAR(255) NOT NULL,
                stored_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(512) NOT NULL,
                file_type VARCHAR(120),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                application_id BIGINT,
                title VARCHAR(191) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            "SELECT id FROM users WHERE role = %s LIMIT 1",
            ("admin",),
        )
        existing_admin = cursor.fetchone()

        if existing_admin is None:
            from werkzeug.security import generate_password_hash

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    "Scholarship Officer",
                    "admin@scholarship.local",
                    generate_password_hash("Admin@12345"),
                    "admin",
                ),
            )
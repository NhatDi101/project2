"""Local-only Flask API backed by PostgreSQL."""

import logging
import os
import sys

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from psycopg.rows import dict_row

# For local development this loads .env. Existing environment variables (such
# as systemd's EnvironmentFile) always take precedence.
load_dotenv()


def configure_logger() -> logging.Logger:
    """Write application logs to stdout so systemd can send them to journald."""
    api_logger = logging.getLogger("users-api")
    api_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    api_logger.propagate = False

    if not api_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        api_logger.addHandler(handler)

    return api_logger


logger = configure_logger()


def read_database_config() -> dict[str, object]:
    """Load every database connection value from environment variables only."""
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    try:
        port = int(os.environ["DB_PORT"])
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be a valid integer") from exc

    return {
        "host": os.environ["DB_HOST"],
        "port": port,
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "connect_timeout": 5,
    }


database_config = read_database_config()
app = Flask(__name__)


def connect_to_database():
    """Create a short-lived PostgreSQL connection for one request."""
    return psycopg.connect(**database_config, row_factory=dict_row)


def initialize_database() -> None:
    """Create the table on first start; no user data is kept in application RAM."""
    with connect_to_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    name VARCHAR(255) NOT NULL CHECK (char_length(trim(name)) > 0),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    logger.info(
        "PostgreSQL connection verified (host=%s port=%s database=%s user=%s)",
        database_config["host"],
        database_config["port"],
        database_config["dbname"],
        database_config["user"],
    )


@app.before_request
def log_request() -> None:
    logger.info("%s %s", request.method, request.path)


@app.get("/")
def index():
    """Return a small response for browsers and reverse-proxy checks."""
    return jsonify(
        message="Users API is running",
        endpoints={"GET /api/users": "List users", "POST /api/users": "Create a user"},
    )


@app.get("/health")
def health_check():
    """Return healthy only when the PostgreSQL connection works."""
    try:
        with connect_to_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        return jsonify(status="ok"), 200
    except psycopg.Error:
        logger.exception("Health check could not connect to PostgreSQL")
        return jsonify(status="unavailable"), 503


@app.get("/api/users")
def list_users():
    """Read users from PostgreSQL."""
    try:
        with connect_to_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name, created_at FROM users ORDER BY id")
                users = cursor.fetchall()
        return jsonify(users), 200
    except psycopg.Error:
        logger.exception("Could not read users from PostgreSQL")
        return jsonify(error="database temporarily unavailable"), 503


@app.post("/api/users")
def create_user():
    """Create a user in PostgreSQL from {\"name\": \"Lan\"}."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
        return jsonify(error="JSON body must include a string field: name"), 400

    name = payload["name"].strip()
    if not name:
        return jsonify(error="name must not be empty"), 400
    if len(name) > 255:
        return jsonify(error="name must contain at most 255 characters"), 400

    try:
        with connect_to_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (name) VALUES (%s) RETURNING id, name, created_at",
                    (name,),
                )
                user = cursor.fetchone()
        logger.info("Created user id=%s", user["id"])
        return jsonify(user), 201
    except psycopg.Error:
        logger.exception("Could not create user in PostgreSQL")
        return jsonify(error="database temporarily unavailable"), 503


# A database failure during startup makes the process exit. systemd's
# Restart=on-failure will then retry instead of running a broken service.
initialize_database()


if __name__ == "__main__":
    try:
        app_port = int(os.getenv("APP_PORT", "8000"))
    except ValueError as exc:
        raise RuntimeError("APP_PORT must be a valid integer") from exc

    logger.info("Starting development server at http://127.0.0.1:%s", app_port)
    # Deliberately bind only loopback. Nginx/Apache should proxy to this port.
    app.run(host="127.0.0.1", port=app_port, debug=False)

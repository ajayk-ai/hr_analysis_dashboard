"""Creates the target Postgres database if it doesn't exist yet.

Run before `alembic upgrade head` on a fresh machine: alembic connects
straight to DB_NAME and fails outright if that database was never created,
even when the Postgres *server* itself is up. Safe to run every time --
a no-op once the database exists.
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

load_dotenv()

DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]


def main() -> None:
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres",
        )
    except psycopg2.OperationalError as exc:
        print(f"[ensure_db] Could not reach Postgres server at {DB_HOST}:{DB_PORT} - {exc}")
        sys.exit(1)

    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            if cur.fetchone():
                print(f"[ensure_db] Database '{DB_NAME}' already exists.")
                return
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"[ensure_db] Created database '{DB_NAME}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

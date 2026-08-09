"""
Lakebase (Databricks-managed Postgres) connection helper and DAL.

Connects using a single LAKEBASE_URL (a standard Postgres connection URL,
e.g. postgresql://role:password@host:5432/databricks_postgres?sslmode=require)
pointing at a native Postgres role with a static, non-expiring password.
"""

import os
from contextlib import contextmanager

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from databricks.sdk import WorkspaceClient
import os
import base64
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

load_dotenv()

def _lakebase_url() -> str:
    """Return the connection URL from environment variable or Databricks secrets, safely cleaned."""
    url = os.getenv("LAKEBASE_URL")
    
    if not url:
        try:
            w = WorkspaceClient()
            scope = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
            key = os.environ.get("LAKEBASE_SECRET_KEY", "lakebase-url")
            secret = w.secrets.get_secret(scope=scope, key=key)
            if secret and secret.value:
                url = secret.value
        except Exception as e:
            pass

    if not url:
        raise ValueError("LAKEBASE_URL environment variable is not set and could not be fetched from Databricks secrets.")

    # Clean up any trailing/leading whitespaces, quotes, or accidental base64 artifacts
    url = url.strip().strip('"').strip("'")
    
    # Optional safety check: if it looks like it was base64 encoded by mistake, try decoding it safely
    # (Remove this block if your secret is stored as plain text)
    try:
        # Check if it decodes cleanly and starts with postgres
        decoded = base64.b64decode(url).decode("utf-8")
        if decoded.startswith("postgres://") or decoded.startswith("postgresql://"):
            url = decoded
    except Exception:
        pass  # It was already a plain text URL, ignore decode error

    return url

@contextmanager
def get_connection():
    """Yield a raw psycopg2 connection with a RealDictCursor factory."""
    conn = psycopg2.connect(_lakebase_url(), cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def get_engine():
    """Return a SQLAlchemy engine for Lakebase."""
    return create_engine(_lakebase_url())


def run_query(sql: str, params: tuple | dict | None = None) -> list[dict]:
    """Run a read query against Lakebase and return rows as list[dict]."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def run_write(sql: str, params: tuple | dict | None = None) -> int:
    """Run an INSERT/UPDATE/DELETE against Lakebase, return affected row count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


# -----------------------------------------------------------------------------
# Application Data Access Methods
# -----------------------------------------------------------------------------

def fetch_tickets(status_filter: str = "All") -> pd.DataFrame:
    """Fetch tickets filtered by status."""
    sql = "SELECT ticket_id, title, status, created_by, created_at FROM support_system.tickets"
    params = []

    if status_filter and status_filter != "All":
        sql += " WHERE status = %s"
        params.append(status_filter)

    sql += " ORDER BY created_at DESC;"

    rows = run_query(sql, tuple(params) if params else None)
    return pd.DataFrame(rows)


def fetch_messages(ticket_id: str) -> pd.DataFrame:
    """Fetch all messages for a given ticket ID."""
    sql = """
        SELECT message_id, ticket_id, message_text, author, created_at 
        FROM support_system.ticket_messages 
        WHERE ticket_id = %s 
        ORDER BY created_at ASC;
    """
    rows = run_query(sql, (ticket_id,))
    return pd.DataFrame(rows)


def create_ticket(ticket_id: str, title: str, status: str, created_by: str) -> int:
    """Insert a new support ticket."""
    sql = """
        INSERT INTO support_system.tickets (ticket_id, title, status, created_by, created_at)
        VALUES (%s, %s, %s, %s, NOW());
    """
    return run_write(sql, (ticket_id, title, status, created_by))


def add_message(message_id: str, ticket_id: str, message_text: str, author: str) -> int:
    """Add a message reply to an existing ticket."""
    sql = """
        INSERT INTO support_system.ticket_messages (message_id, ticket_id, message_text, author, created_at)
        VALUES (%s, %s, %s, %s, NOW());
    """
    return run_write(sql, (message_id, ticket_id, message_text, author))


def update_ticket_status(ticket_id: str, new_status: str) -> int:
    """Update status of a ticket."""
    sql = "UPDATE support_system.tickets SET status = %s WHERE ticket_id = %s;"
    return run_write(sql, (new_status, ticket_id))
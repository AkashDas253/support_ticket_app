"""
Lakebase (Databricks-managed Postgres) connection helper and DAL.

Connects using a single LAKEBASE_URL (a standard Postgres connection URL,
stored as a Base64 encoded secret in Databricks).
"""

import base64
import os
from contextlib import contextmanager

import pandas as pd
import psycopg2
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine

load_dotenv()

_w = WorkspaceClient()


def _lakebase_url() -> str:
    """Return the connection URL from environment variable or Databricks secret (handling both plain text & Base64)."""
    url = os.getenv("LAKEBASE_URL")
    
    if not url:
        try:
            scope = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
            key = os.environ.get("LAKEBASE_SECRET_KEY", "lakebase-url")
            
            secret = _w.secrets.get_secret(scope=scope, key=key)
            if secret and secret.value:
                raw_val = secret.value.strip().strip('"').strip("'")
                
                # Check if it's already a plain-text Postgres URL
                if raw_val.startswith("postgresql://") or raw_val.startswith("postgres://"):
                    url = raw_val
                else:
                    # Otherwise, try decoding it as Base64
                    try:
                        decoded = base64.b64decode(raw_val).decode("utf-8")
                        url = decoded.strip().strip('"').strip("'")
                    except Exception:
                        # Fallback to raw value if base64 decode fails
                        url = raw_val
        except Exception:
            pass

    if not url:
        raise ValueError("LAKEBASE_URL environment variable is not set and could not be fetched/decoded from Databricks secrets.")

    url = url.strip().strip('"').strip("'")
    
    # Final validation check
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        raise ValueError(f"Invalid connection string format. Must start with postgresql://. Got: {url[:10]}...")

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
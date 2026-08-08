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

load_dotenv()


def _lakebase_url() -> str:
    """Return the connection URL directly from the LAKEBASE_URL environment variable."""
    url = os.getenv("LAKEBASE_URL")
    if not url:
        raise ValueError("LAKEBASE_URL environment variable is not set.")
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
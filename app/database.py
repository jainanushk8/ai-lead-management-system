"""
app/database.py
Async SQLite database connection and schema management.

HOW IT WORKS:
- Uses aiosqlite for non-blocking database operations inside FastAPI's async
  event loop. This means the server can accept new HTTP requests while a
  database query is running, rather than blocking the entire process.
- On application startup, init_db() is called to create tables if they do not
  already exist (IF NOT EXISTS). This makes the app idempotent on restart.
- get_db_connection() is an async context manager that provides a connection
  with row_factory set to sqlite3.Row, so query results behave like
  dictionaries (accessed by column name, not index).

SCHEMA DESIGN:
- leads.email has a UNIQUE constraint. This is the PRIMARY mechanism for
  duplicate detection. INSERT will raise IntegrityError if a duplicate email
  is submitted.
- leads.phone is indexed but not unique (multiple contacts at the same company
  may share a phone number).
- lead_analysis.lead_id is a FOREIGN KEY referencing leads.id, ensuring
  referential integrity.
- agent_logs records every tool call the Hermes agent makes, providing a full
  audit trail for debugging and the technical discussion.

INTERVIEW NOTES:
- Why SQLite over PostgreSQL? On a 16GB RAM machine running an LLM (2-3GB),
  Docker/n8n, and Windows itself, PostgreSQL's idle daemon would consume
  200-500MB of additional RAM. SQLite runs in-process with zero idle overhead.
- Why aiosqlite? Standard sqlite3 is synchronous and would block the FastAPI
  event loop during I/O, degrading throughput under concurrent requests.
"""

import sqlite3
from contextlib import asynccontextmanager

import aiosqlite

from app.config import settings

# SQL statements to create the database schema.
# Each uses IF NOT EXISTS so init_db() is safe to call on every startup.

CREATE_LEADS_TABLE = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    company TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LEAD_ANALYSIS_TABLE = """
CREATE TABLE IF NOT EXISTS lead_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL UNIQUE,
    temperature TEXT NOT NULL DEFAULT 'warm',
    requirements TEXT DEFAULT '[]',
    ai_response TEXT DEFAULT '',
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);
"""

CREATE_AGENT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,
    tool_name TEXT NOT NULL,
    tool_input TEXT DEFAULT '{}',
    tool_output TEXT DEFAULT '{}',
    success INTEGER NOT NULL DEFAULT 1,
    error_message TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL
);
"""

# Indexes for fast lookups on frequently queried columns.
CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_lead_analysis_lead_id ON lead_analysis(lead_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_lead_id ON agent_logs(lead_id);
"""


async def init_db() -> None:
    """
    Create all tables and indexes if they do not already exist.
    Called once during FastAPI application startup via the lifespan event.
    """
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # Enable WAL mode for better concurrent read performance.
        await db.execute("PRAGMA journal_mode=WAL;")
        # Enable foreign key enforcement (off by default in SQLite).
        await db.execute("PRAGMA foreign_keys=ON;")

        await db.execute(CREATE_LEADS_TABLE)
        await db.execute(CREATE_LEAD_ANALYSIS_TABLE)
        await db.execute(CREATE_AGENT_LOGS_TABLE)
        await db.executescript(CREATE_INDEXES)
        await db.commit()


@asynccontextmanager
async def get_db_connection():
    """
    Async context manager that yields an aiosqlite connection.

    Usage:
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM leads")
            rows = await cursor.fetchall()

    The connection automatically:
    - Sets row_factory to sqlite3.Row (dict-like access by column name).
    - Enables foreign key enforcement.
    - Closes cleanly when the context manager exits.
    """
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    db.row_factory = sqlite3.Row
    await db.execute("PRAGMA foreign_keys=ON;")
    try:
        yield db
    finally:
        await db.close()

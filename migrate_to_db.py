"""
migrate_to_db.py
Migrates patterns.json to SQLite database.
Run once from ~/projects/content-engine/
"""

import json
import sqlite3
import os
from datetime import datetime

DB_PATH = "content_engine.db"
JSON_PATH = "patterns.json"


def create_tables(conn):
    """Create all tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS patterns (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS stories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            date_added  TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS identity (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS story_patterns (
            story_id    INTEGER REFERENCES stories(id),
            pattern_id  INTEGER REFERENCES patterns(id),
            PRIMARY KEY (story_id, pattern_id)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            title               TEXT,
            published_date      TEXT,
            platform            TEXT DEFAULT 'linkedin',
            performance_notes   TEXT,
            impressions         INTEGER,
            comments            INTEGER,
            reposts             INTEGER
        );
    """)
    print("✓ Tables created")


def migrate_patterns(conn, data):
    for p in data.get("patterns", []):
        conn.execute(
            "INSERT OR IGNORE INTO patterns (name, description) VALUES (?, ?)",
            (p["name"], p.get("description", ""))
        )
    count = len(data.get("patterns", []))
    print(f"✓ Migrated {count} patterns")


def migrate_stories(conn, data):
    for s in data.get("stories", []):
        conn.execute(
            "INSERT OR IGNORE INTO stories (name, description, date_added) VALUES (?, ?, ?)",
            (s["name"], s.get("description", ""), datetime.today().strftime("%Y-%m-%d"))
        )
    count = len(data.get("stories", []))
    print(f"✓ Migrated {count} stories")


def migrate_identity(conn, data):
    for i in data.get("identity", []):
        conn.execute(
            "INSERT OR IGNORE INTO identity (name, description) VALUES (?, ?)",
            (i["name"], i.get("description", ""))
        )
    count = len(data.get("identity", []))
    print(f"✓ Migrated {count} identity dimensions")


def main():
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: {JSON_PATH} not found. Run from ~/projects/content-engine/")
        return

    with open(JSON_PATH) as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    create_tables(conn)
    migrate_patterns(conn, data)
    migrate_stories(conn, data)
    migrate_identity(conn, data)

    conn.commit()
    conn.close()

    print(f"\n✓ Done. Database created at {DB_PATH}")
    print("Next step: run verify_db.py to confirm everything landed correctly")


if __name__ == "__main__":
    main()

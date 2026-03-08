"""
verify_db.py
Confirms migration landed correctly. Run after migrate_to_db.py
"""

import sqlite3

DB_PATH = "content_engine.db"


def verify():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name

    tables = ["patterns", "stories", "identity", "story_patterns", "posts"]

    print("=== DATABASE VERIFICATION ===\n")

    for table in tables:
        rows = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
        print(f"{table:20} {rows['count']} rows")

    print("\n=== SAMPLE: PATTERNS ===")
    for row in conn.execute("SELECT id, name FROM patterns LIMIT 5"):
        print(f"  [{row['id']}] {row['name']}")

    print("\n=== SAMPLE: STORIES ===")
    for row in conn.execute("SELECT id, name FROM stories LIMIT 5"):
        print(f"  [{row['id']}] {row['name']}")

    print("\n=== SAMPLE: IDENTITY ===")
    for row in conn.execute("SELECT id, name FROM identity"):
        print(f"  [{row['id']}] {row['name']}")

    conn.close()
    print("\n✓ Verification complete")


if __name__ == "__main__":
    verify()

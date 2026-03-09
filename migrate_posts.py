# migrate_posts.py — add hook/reactions columns and seed post history
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "content_engine.db"

POSTS = [
    {
        "hook": "Every year, pharma companies lose something that never shows up on a balance sheet",
        "title": "Bob / Knowledge Loss",
        "published_date": "2026-02-18",
        "platform": "linkedin",
        "impressions": 2103,
        "comments": 0,
        "reposts": 2,
        "reactions": 28,
        "performance_notes": "Introduced Bob character. Named protagonist. Strong senior audience reach.",
    },
    {
        "hook": "Everyone's buying AI tools for pharma right now",
        "title": "Six Sigma Parallel",
        "published_date": "2026-02-20",
        "platform": "linkedin",
        "impressions": 8946,
        "comments": 6,
        "reposts": 0,
        "reactions": 21,
        "performance_notes": "Historical parallel worked. Chef's knives metaphor. First major engagement.",
    },
    {
        "hook": "I told a customer I'll take that back to the team",
        "title": "RAG Floppy Disk",
        "published_date": "2026-02-23",
        "platform": "linkedin",
        "impressions": 901,
        "comments": 4,
        "reposts": 0,
        "reactions": 5,
        "performance_notes": "Specific archaeology story. Lower reach. Abstract concept without named protagonist.",
    },
    {
        "hook": "The FDA deployed an AI assistant called Elsa in June 2025",
        "title": "Elsa FDA",
        "published_date": "2026-02-25",
        "platform": "linkedin",
        "impressions": 56121,
        "comments": 26,
        "reposts": 4,
        "reactions": 116,
        "performance_notes": "Best performer by far. Named protagonist. Irony with stakes. Regulator doing what industry won't.",
    },
    {
        "hook": "AI compressed drug discovery. Nobody told the rest of the pipeline",
        "title": "Pipeline Infrastructure",
        "published_date": "2026-03-03",
        "platform": "linkedin",
        "impressions": 8188,
        "comments": 7,
        "reposts": 2,
        "reactions": 31,
        "performance_notes": "Strong. Visual graphic helped. CAR-T pushback in comments -- good engagement.",
    },
    {
        "hook": "I used to know a dozen phone numbers by heart. Now I know three",
        "title": "Human Faculty Atrophy",
        "published_date": "2026-03-03",
        "platform": "linkedin",
        "impressions": 786,
        "comments": 2,
        "reposts": 0,
        "reactions": 4,
        "performance_notes": "Abstract concept. No named protagonist. Same day as Pipeline post -- may have cannibalized.",
    },
    {
        "hook": "An MIT model just learned to speak yeast",
        "title": "Yeast Language Model",
        "published_date": "2026-03-04",
        "platform": "linkedin",
        "impressions": 205,
        "comments": 0,
        "reposts": 0,
        "reactions": 3,
        "performance_notes": "Too abstract. No pharma practitioner hook. Lowest performer.",
    },
]

conn = sqlite3.connect(DB_PATH)

# Add missing columns if they don't already exist
existing = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
if "hook" not in existing:
    conn.execute("ALTER TABLE posts ADD COLUMN hook TEXT")
    print("added column: hook")
if "reactions" not in existing:
    conn.execute("ALTER TABLE posts ADD COLUMN reactions INTEGER")
    print("added column: reactions")

# Insert posts
conn.executemany(
    """
    INSERT INTO posts (hook, title, published_date, platform,
                       impressions, comments, reposts, reactions, performance_notes)
    VALUES (:hook, :title, :published_date, :platform,
            :impressions, :comments, :reposts, :reactions, :performance_notes)
    """,
    POSTS,
)
conn.commit()

rows = conn.execute("SELECT id, published_date, title, impressions FROM posts ORDER BY published_date").fetchall()
print(f"\nInserted {len(POSTS)} posts. All posts in table:")
for r in rows:
    print(f"  [{r[0]}] {r[1]}  {r[2]:<30}  {r[3]:>6} impressions")

conn.close()

# app.py
import json
import os
import sqlite3
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "content-engine-local"

DB_PATH = Path(__file__).parent / "content_engine.db"
TYPE_TABLES = {"pattern": "patterns", "story": "stories", "identity": "identity"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._parts.append(text)


def _extract_text(html):
    parser = _TextExtractor()
    parser.feed(html)
    return " ".join(parser._parts)


@app.route("/")
def index():
    conn = get_db()
    patterns = conn.execute("SELECT * FROM patterns ORDER BY id").fetchall()
    stories = conn.execute("SELECT * FROM stories ORDER BY id").fetchall()
    identity = conn.execute("SELECT * FROM identity ORDER BY id").fetchall()
    conn.close()
    library = {"patterns": patterns, "stories": stories, "identity": identity, "log": []}
    return render_template("index.html", library=library, recent_log=[])


@app.route("/edit/<entry_type>/<int:idx>", methods=["GET", "POST"])
def edit(entry_type, idx):
    if entry_type not in TYPE_TABLES:
        flash("Invalid type.", "error")
        return redirect(url_for("index"))

    table = TYPE_TABLES[entry_type]
    conn = get_db()
    entry = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (idx,)).fetchone()

    if entry is None:
        conn.close()
        flash("Entry not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            conn.close()
            flash("Name is required.", "error")
            return redirect(url_for("edit", entry_type=entry_type, idx=idx))

        conn.execute(
            f"UPDATE {table} SET name = ?, description = ? WHERE id = ?",
            (name, description, idx),
        )
        conn.commit()
        conn.close()

        flash(f'Updated {entry_type}: "{name}"', "success")
        return redirect(url_for("index"))

    conn.close()
    return render_template("edit.html", entry=entry, entry_type=entry_type, idx=idx)


@app.route("/delete/<entry_type>/<int:idx>", methods=["POST"])
def delete(entry_type, idx):
    if entry_type not in TYPE_TABLES:
        flash("Invalid type.", "error")
        return redirect(url_for("index"))

    table = TYPE_TABLES[entry_type]
    conn = get_db()
    entry = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (idx,)).fetchone()

    if entry is None:
        conn.close()
        flash("Entry not found.", "error")
        return redirect(url_for("index"))

    name = entry["name"]
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (idx,))
    conn.commit()
    conn.close()

    flash(f'Deleted {entry_type}: "{name}"', "success")
    return redirect(url_for("index"))


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        entry_type = request.form.get("type", "").strip().lower()
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if entry_type not in TYPE_TABLES:
            flash("Invalid type.", "error")
            return redirect(url_for("add"))
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("add"))
        if not description:
            flash("Description is required.", "error")
            return redirect(url_for("add"))

        table = TYPE_TABLES[entry_type]
        conn = get_db()
        conn.execute(
            f"INSERT INTO {table} (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        conn.close()

        flash(f'Added {entry_type}: "{name}"', "success")
        return redirect(url_for("index"))

    return render_template("add.html")


CAPTURE_SOURCES = ["other", "x", "linkedin", "newsletter", "book", "conversation", "web", "claude"]


@app.route("/capture", methods=["GET", "POST"])
def capture():
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        source = request.form.get("source", "other").strip()
        category = request.form.get("category", "content").strip()

        if not content:
            flash("Content is required.", "error")
            return redirect(url_for("capture"))
        if source not in CAPTURE_SOURCES:
            source = "other"
        if category not in ("content", "strategy", "learning", "signal"):
            category = "content"

        conn = get_db()
        conn.execute(
            "INSERT INTO captures (content, source, category) VALUES (?, ?, ?)",
            (content, source, category),
        )
        conn.commit()
        conn.close()

        flash("Captured.", "success")
        return redirect(url_for("capture"))

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM captures ORDER BY processed ASC, created_at DESC"
    ).fetchall()
    conn.close()

    inbox = []
    for row in rows:
        item = dict(row)
        if item.get("enrichment"):
            try:
                item["enrichment_data"] = json.loads(item["enrichment"])
            except json.JSONDecodeError:
                item["enrichment_data"] = None
        else:
            item["enrichment_data"] = None
        inbox.append(item)

    unread_count = sum(1 for item in inbox if not item["processed"])
    return render_template("capture.html", inbox=inbox, sources=CAPTURE_SOURCES, unread_count=unread_count)


@app.route("/capture/draft/<int:idx>", methods=["GET", "POST"])
def capture_draft(idx):
    conn = get_db()
    capture = conn.execute("SELECT * FROM captures WHERE id = ?", (idx,)).fetchone()

    if capture is None:
        conn.close()
        flash("Capture not found.", "error")
        return redirect(url_for("capture"))

    if request.method == "POST":
        draft_data = {
            "angle":              request.form.get("angle", "").strip(),
            "hook":               request.form.get("hook", "").strip(),
            "pattern_connection": request.form.get("pattern_connection", "").strip(),
            "notes":              request.form.get("notes", "").strip(),
            "full_draft":         request.form.get("full_draft", "").strip(),
        }
        post_id = request.form.get("post_id", "").strip()

        conn.execute(
            "UPDATE captures SET draft = ? WHERE id = ?",
            (json.dumps(draft_data), idx)
        )

        if post_id:
            exists = conn.execute(
                "SELECT 1 FROM post_captures WHERE post_id = ? AND capture_id = ?",
                (int(post_id), idx)
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO post_captures (post_id, capture_id) VALUES (?, ?)",
                    (int(post_id), idx)
                )

        conn.commit()
        conn.close()
        flash("Draft saved.", "success")
        return redirect(url_for("capture_draft", idx=idx))

    item = dict(capture)
    if item.get("enrichment"):
        try:
            item["enrichment_data"] = json.loads(item["enrichment"])
        except json.JSONDecodeError:
            item["enrichment_data"] = None
    else:
        item["enrichment_data"] = None

    draft = None
    if item.get("draft"):
        try:
            draft = json.loads(item["draft"])
        except json.JSONDecodeError:
            draft = None

    patterns = conn.execute("SELECT name FROM patterns ORDER BY id").fetchall()
    posts = conn.execute(
        "SELECT id, title, published_date FROM posts ORDER BY published_date DESC"
    ).fetchall()
    linked_post_ids = {r["post_id"] for r in conn.execute(
        "SELECT post_id FROM post_captures WHERE capture_id = ?", (idx,)
    ).fetchall()}

    conn.close()
    return render_template(
        "capture_draft.html",
        capture=item,
        draft=draft,
        patterns=patterns,
        posts=posts,
        linked_post_ids=linked_post_ids,
    )


@app.route("/capture/promote/<int:idx>", methods=["GET", "POST"])
def capture_promote(idx):
    conn = get_db()
    capture = conn.execute("SELECT * FROM captures WHERE id = ?", (idx,)).fetchone()

    if capture is None:
        conn.close()
        flash("Capture not found.", "error")
        return redirect(url_for("capture"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        entry_type = request.form.get("type", "").strip().lower()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("capture_promote", idx=idx))
        if entry_type not in TYPE_TABLES:
            flash("Invalid type.", "error")
            return redirect(url_for("capture_promote", idx=idx))

        table = TYPE_TABLES[entry_type]
        conn.execute(
            f"INSERT INTO {table} (name, description) VALUES (?, ?)",
            (name, description)
        )
        conn.commit()
        conn.close()

        flash(f'Added {entry_type}: "{name}" to library.', "success")
        return redirect(url_for("capture"))

    prefill_name = ""
    prefill_description = ""
    if capture["enrichment"]:
        try:
            enrichment = json.loads(capture["enrichment"])
            suggestion = enrichment.get("promote_suggestion") or {}
            prefill_name = suggestion.get("name", "")
            prefill_description = suggestion.get("description", "") or enrichment.get("key_insight", "")
        except json.JSONDecodeError:
            pass

    conn.close()
    return render_template("capture_promote.html", capture=capture,
                           prefill_name=prefill_name,
                           prefill_description=prefill_description)


@app.route("/capture/toggle/<int:idx>", methods=["POST"])
def capture_toggle(idx):
    conn = get_db()
    capture = conn.execute("SELECT processed FROM captures WHERE id = ?", (idx,)).fetchone()
    if capture is None:
        conn.close()
        flash("Capture not found.", "error")
        return redirect(url_for("capture"))
    new_state = 0 if capture["processed"] else 1
    conn.execute("UPDATE captures SET processed = ? WHERE id = ?", (new_state, idx))
    conn.commit()
    conn.close()
    return redirect(url_for("capture"))


@app.route("/capture/dismiss/<int:idx>", methods=["POST"])
def capture_dismiss(idx):
    conn = get_db()
    conn.execute("UPDATE captures SET processed = 1 WHERE id = ?", (idx,))
    conn.commit()
    conn.close()
    flash("Dismissed.", "success")
    return redirect(url_for("capture"))


@app.route("/capture/edit/<int:idx>", methods=["GET", "POST"])
def capture_edit(idx):
    conn = get_db()
    capture = conn.execute("SELECT * FROM captures WHERE id = ?", (idx,)).fetchone()

    if capture is None:
        conn.close()
        flash("Capture not found.", "error")
        return redirect(url_for("capture"))

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "content").strip()

        if not content:
            conn.close()
            flash("Content is required.", "error")
            return redirect(url_for("capture_edit", idx=idx))
        if category not in ("content", "strategy", "learning", "signal"):
            category = "content"

        conn.execute(
            "UPDATE captures SET content = ?, category = ? WHERE id = ?",
            (content, category, idx),
        )
        conn.commit()
        conn.close()
        flash("Capture updated.", "success")
        return redirect(url_for("capture"))

    conn.close()
    return render_template("capture_edit.html", capture=capture)


@app.route("/capture/enrich/<int:idx>", methods=["POST"])
def capture_enrich(idx):
    conn = get_db()
    capture = conn.execute("SELECT * FROM captures WHERE id = ?", (idx,)).fetchone()

    if capture is None:
        conn.close()
        flash("Capture not found.", "error")
        return redirect(url_for("capture"))

    content = capture["content"].strip()
    url = content.split("\n")[0].strip()

    if url.startswith("http"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            page_text = _extract_text(html)[:4000]
        except urllib.error.URLError as e:
            conn.close()
            flash(f"Could not fetch URL: {e.reason}", "error")
            return redirect(url_for("capture"))
    else:
        page_text = content[:4000]

    category = capture["category"] or "content"

    lens_instructions = {
        "content": (
            "Apply the pharma practitioner lens. Emphasize regulatory patterns, compliance gaps, "
            "and manufacturing reality. What does someone with 20 years on the floor see here "
            "that an outsider would miss?"
        ),
        "signal": (
            "Apply the early signal detector + systems thinker lens. Look for cross-domain patterns "
            "and what this rhymes with in other industries. Separate what is actually new from what "
            "is hype. What does this signal about where things are heading?"
        ),
        "strategy": (
            "Apply the empire builder lens. Focus on business model implications and build vs buy vs "
            "ignore decisions. How does this affect a bootstrapped consulting and content business "
            "at the intersection of pharma ops and AI?"
        ),
        "learning": (
            "Apply the curious generalist lens. What mental model does this build or refine? "
            "What changes about how to think after absorbing this? Focus on transferable insight."
        ),
    }
    lens = lens_instructions.get(category, lens_instructions["content"])

    patterns = conn.execute("SELECT name, description FROM patterns ORDER BY id").fetchall()
    patterns_list = "\n".join(f"- {r['name']}: {r['description']}" for r in patterns)

    prompt = f"""{"URL: " + url if url.startswith("http") else "Capture:"}

Content:
{page_text}

Lens: {lens}

Pattern library:
{patterns_list}

Return a JSON object with exactly these fields:
- summary: 2-3 sentence summary of the content
- suggested_category: one of content, strategy, learning, signal
- matched_patterns: identify the ONE or TWO most strongly matched patterns and explain specifically why each one fits. Be selective — only include a pattern if the fit is strong and specific, not just loosely related. Format as a list of strings: ["Pattern Name: reason it fits", ...]. Can be empty list if nothing fits well.
- key_insight: one sentence capturing the most useful insight
- promote_suggestion: an object with these fields:
    - action: either "match" (fits an existing pattern) or "new" (suggest a new one)
    - name: the matching pattern name if action is "match", or a proposed new pattern name if action is "new"
    - description: if action is "match", one sentence on why this capture fits that pattern; if action is "new", a full description of the proposed pattern written in a direct, practitioner voice — specific, not generic

Return only valid JSON, no other text."""

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    enrichment_raw = message.content[0].text.strip().strip("`").removeprefix("json").strip()

    try:
        json.loads(enrichment_raw)
    except json.JSONDecodeError:
        conn.close()
        flash("Enrichment failed — Claude returned unexpected output.", "error")
        return redirect(url_for("capture"))

    conn.execute("UPDATE captures SET enrichment = ? WHERE id = ?", (enrichment_raw, idx))
    conn.commit()
    conn.close()

    flash("Enriched.", "success")
    return redirect(url_for("capture"))


@app.route("/api/capture", methods=["POST"])
def api_capture():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    source = (data.get("source") or "other").strip()

    if not content:
        return jsonify({"error": "content is required"}), 400
    if source not in CAPTURE_SOURCES:
        source = "other"

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO captures (content, source) VALUES (?, ?)",
        (content, source),
    )
    capture_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id": capture_id, "content": content, "source": source}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

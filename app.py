# app.py
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = "content-engine-local"

DB_PATH = Path(__file__).parent / "content_engine.db"
TYPE_TABLES = {"pattern": "patterns", "story": "stories", "identity": "identity"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    inbox = conn.execute(
        "SELECT * FROM captures WHERE processed = 0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("capture.html", inbox=inbox, sources=CAPTURE_SOURCES)


@app.route("/capture/dismiss/<int:idx>", methods=["POST"])
def capture_dismiss(idx):
    conn = get_db()
    conn.execute("UPDATE captures SET processed = 1 WHERE id = ?", (idx,))
    conn.commit()
    conn.close()
    flash("Dismissed.", "success")
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
    app.run(host="127.0.0.1", port=5000, debug=True)

"""
db.py — SQLite database layer for the AI Resume Analyzer.

Handles schema creation and all CRUD operations for users (auth) and
applicants (parsed resume + scores + predictions + recommendations),
keeping app.py focused on routing.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "resume.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            email TEXT,
            phone TEXT,
            linkedin TEXT,
            github TEXT,
            resume_filename TEXT,
            resume_path TEXT,
            education TEXT,
            experience_years REAL,
            skills_json TEXT,
            resume_score REAL,
            ats_score REAL,
            formatting_score REAL,
            readability_score REAL,
            experience_score REAL,
            education_score REAL,
            skill_score REAL,
            overall_rating TEXT,
            predictions_json TEXT,
            recommendations_json TEXT,
            upload_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )

    # Lightweight migration: add user_id to pre-existing DBs that predate auth.
    cur.execute("PRAGMA table_info(applicants)")
    cols = [row["name"] for row in cur.fetchall()]
    if "user_id" not in cols:
        cur.execute("ALTER TABLE applicants ADD COLUMN user_id INTEGER")

    conn.commit()

    # Seed a default admin account if none exists, so /admin is usable out of the box.
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE is_admin = 1")
    if cur.fetchone()["c"] == 0:
        from werkzeug.security import generate_password_hash
        cur.execute(
            "INSERT INTO users (name, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, 1, ?)",
            ("Admin", "admin@resumeai.com", generate_password_hash("admin123"), datetime.utcnow().isoformat()),
        )
        conn.commit()

    conn.close()


# ---------------------------------------------------------------- Users

def create_user(name: str, email: str, password_hash: str, is_admin: bool = False) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, email.lower().strip(), password_hash, int(is_admin), datetime.utcnow().isoformat()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_user_by_email(email: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------- Applicants

def insert_applicant(record: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO applicants (
            user_id, name, email, phone, linkedin, github, resume_filename, resume_path,
            education, experience_years, skills_json, resume_score, ats_score,
            formatting_score, readability_score, experience_score, education_score,
            skill_score, overall_rating, predictions_json, recommendations_json, upload_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.get("user_id"), record["name"], record["email"], record["phone"],
            record["linkedin"], record["github"],
            record["resume_filename"], record["resume_path"], record["education"],
            record["experience_years"], json.dumps(record["skills"]),
            record["resume_score"], record["ats_score"], record["formatting_score"],
            record["readability_score"], record["experience_score"], record["education_score"],
            record["skill_score"], record["overall_rating"],
            json.dumps(record["predictions"]), json.dumps(record["recommendations"]),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_applicant(applicant_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applicants WHERE id = ?", (applicant_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_all_applicants(search: str = "", role_filter: str = "") -> list:
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM applicants WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR email LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    query += " ORDER BY upload_date DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    results = [_row_to_dict(r) for r in rows]

    if role_filter:
        results = [
            r for r in results
            if r["predictions"] and r["predictions"][0]["role"] == role_filter
        ]
    return results


def get_history_for_user(user_id: int) -> list:
    """Per-user resume analysis history (used by the applicant dashboard)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applicants WHERE user_id = ? ORDER BY upload_date DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def delete_applicant(applicant_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM applicants WHERE id = ?", (applicant_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["skills"] = json.loads(d.pop("skills_json") or "{}")
    d["predictions"] = json.loads(d.pop("predictions_json") or "[]")
    d["recommendations"] = json.loads(d.pop("recommendations_json") or "{}")
    return d

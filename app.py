"""
app.py — AI Resume Analyzer (Flask backend).

Routes:
  GET  /                      Landing page
  GET/POST /register          User registration
  GET/POST /login             User login
  GET  /logout                Clear session and log out
  GET  /dashboard             Applicant dashboard (login required)
  GET  /admin                 Admin dashboard (admin login required)
  POST /api/upload            Upload + analyze a resume (PDF) (login required)
  GET  /api/applicant/<id>    Get one applicant's full analysis
  GET  /api/history           Get the logged-in user's upload history
  GET  /api/admin/applicants  List all applicants (search/filter)
  DELETE /api/admin/applicant/<id>  Delete an applicant
  GET  /api/admin/export-csv  Export all applicants as CSV
  GET  /api/admin/analytics   Aggregated stats for Plotly charts
  GET  /api/report/<id>       Download a plaintext analysis report
"""

import os
import io
import csv
import uuid
import re
import sys
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, send_file, Response,
    session, redirect, url_for
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# ── Create the Flask app FIRST so `app` is always defined, even if a
#    utility import fails below (prevents NameError: name 'app' is not defined).
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"]        = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"]   = 8 * 1024 * 1024   # 8 MB
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Utility imports — kept AFTER app creation so any ImportError surfaces as
#    a clear message instead of "NameError: name 'app' is not defined".
try:
    from utils import db
    from utils.parser import parse_resume
    from utils.analyzer import compute_all_scores
    from utils.predictor import predict_job_roles
    from utils.recommender import generate_full_recommendations
except ImportError as _e:
    print(
        f"\n❌  Import error: {_e}"
        "\n    Make sure you have installed all dependencies:"
        "\n    pip install -r requirements.txt\n",
        file=sys.stderr,
    )
    sys.exit(1)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view):
    """Redirect to /login (for pages) or 401 JSON (for /api/*) if not authenticated."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login", next=request.path))
        if not session.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin access required."}), 403
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    return {
        "id": session["user_id"], "name": session.get("user_name"),
        "email": session.get("user_email"), "is_admin": session.get("is_admin", False),
    }


# ---------------------------------------------------------------- Auth pages

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.", name=name, email=email)
    if not EMAIL_RE.match(email):
        return render_template("register.html", error="Enter a valid email address.", name=name, email=email)
    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.", name=name, email=email)
    if password != confirm:
        return render_template("register.html", error="Passwords do not match.", name=name, email=email)
    if db.get_user_by_email(email):
        return render_template("register.html", error="An account with this email already exists.", name=name, email=email)

    user_id = db.create_user(name, email, generate_password_hash(password))

    session["user_id"] = user_id
    session["user_name"] = name
    session["user_email"] = email
    session["is_admin"] = False

    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", next=request.args.get("next", ""))

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    next_url = request.form.get("next", "")

    user = db.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email, next=next_url)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    session["is_admin"] = bool(user["is_admin"])

    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("admin") if user["is_admin"] else url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/me", methods=["GET"])
def api_me():
    return jsonify({"user": current_user()}), 200


# ---------------------------------------------------------------- Pages

@app.route("/")
def index():
    return render_template("index.html", user=current_user())


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user())


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", user=current_user())


# ---------------------------------------------------------------- API: Upload & Analyze

@app.route("/api/upload", methods=["POST"])
@login_required
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF resumes are supported."}), 400

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(save_path)

    try:
        parsed = parse_resume(save_path)
        scores = compute_all_scores(parsed)
        predictions = predict_job_roles(parsed)
        recommendations = generate_full_recommendations(parsed, scores, predictions)
    except Exception as e:
        return jsonify({"error": f"Failed to analyze resume: {e}"}), 422

    record = {
        "user_id": session["user_id"],
        "name": parsed["name"],
        "email": parsed["email"],
        "phone": parsed["phone"],
        "linkedin": parsed["linkedin"],
        "github": parsed["github"],
        "resume_filename": safe_name,
        "resume_path": unique_name,
        "education": parsed["education"],
        "experience_years": parsed["experience_years"],
        "skills": parsed["skills"],
        "resume_score": scores["resume_score"],
        "ats_score": scores["ats_score"],
        "formatting_score": scores["formatting_score"],
        "readability_score": scores["readability_score"],
        "experience_score": scores["experience_score"],
        "education_score": scores["education_score"],
        "skill_score": scores["skill_score"],
        "overall_rating": scores["overall_rating"],
        "predictions": predictions,
        "recommendations": recommendations,
    }

    applicant_id = db.insert_applicant(record)
    record["id"] = applicant_id

    return jsonify({
        "id": applicant_id,
        "parsed": {
            "name": parsed["name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "linkedin": parsed["linkedin"],
            "github": parsed["github"],
            "education": parsed["education"],
            "experience_section": parsed["experience_section"],
            "projects": parsed["projects"],
            "certifications": parsed["certifications"],
            "languages": parsed["languages"],
            "experience_years": parsed["experience_years"],
            "skills": parsed["skills"],
        },
        "scores": scores,
        "predictions": predictions,
        "recommendations": recommendations,
    }), 200


@app.route("/api/applicant/<int:applicant_id>", methods=["GET"])
@login_required
def get_applicant(applicant_id):
    applicant = db.get_applicant(applicant_id)
    if not applicant:
        return jsonify({"error": "Applicant not found."}), 404
    if not session.get("is_admin") and applicant.get("user_id") != session["user_id"]:
        return jsonify({"error": "You don't have access to this record."}), 403
    return jsonify(applicant), 200


@app.route("/api/history", methods=["GET"])
@login_required
def history():
    records = db.get_history_for_user(session["user_id"])
    return jsonify({"history": records}), 200


# ---------------------------------------------------------------- API: Admin

@app.route("/api/admin/applicants", methods=["GET"])
@admin_required
def admin_applicants():
    search = request.args.get("search", "").strip()
    role = request.args.get("role", "").strip()
    applicants = db.get_all_applicants(search=search, role_filter=role)
    return jsonify({"applicants": applicants}), 200


@app.route("/api/admin/applicant/<int:applicant_id>", methods=["DELETE"])
@admin_required
def admin_delete_applicant(applicant_id):
    success = db.delete_applicant(applicant_id)
    if not success:
        return jsonify({"error": "Applicant not found."}), 404
    return jsonify({"message": "Deleted successfully."}), 200


@app.route("/api/admin/export-csv", methods=["GET"])
@admin_required
def export_csv():
    applicants = db.get_all_applicants()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Name", "Email", "Phone", "Resume Score", "ATS Score",
        "Top Predicted Role", "Experience Years", "Upload Date"
    ])
    for a in applicants:
        top_role = a["predictions"][0]["role"] if a["predictions"] else ""
        writer.writerow([
            a["id"], a["name"], a["email"], a["phone"], a["resume_score"],
            a["ats_score"], top_role, a["experience_years"], a["upload_date"]
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=applicants_export.csv"},
    )


@app.route("/api/admin/analytics", methods=["GET"])
@admin_required
def admin_analytics():
    applicants = db.get_all_applicants()

    skill_counter = {}
    role_counter = {}
    score_buckets = {"0-50": 0, "50-70": 0, "70-85": 0, "85-100": 0}
    monthly_users = {}
    education_levels = {}
    experience_buckets = {"0-1 yrs": 0, "1-3 yrs": 0, "3-6 yrs": 0, "6+ yrs": 0}

    for a in applicants:
        for skill in a["skills"].get("all_technical", []):
            skill_counter[skill] = skill_counter.get(skill, 0) + 1

        if a["predictions"]:
            top_role = a["predictions"][0]["role"]
            role_counter[top_role] = role_counter.get(top_role, 0) + 1

        score = a["resume_score"] or 0
        if score < 50:
            score_buckets["0-50"] += 1
        elif score < 70:
            score_buckets["50-70"] += 1
        elif score < 85:
            score_buckets["70-85"] += 1
        else:
            score_buckets["85-100"] += 1

        month = (a["upload_date"] or "")[:7]
        if month:
            monthly_users[month] = monthly_users.get(month, 0) + 1

        edu = (a["education"] or "").lower()
        if "phd" in edu:
            level = "PhD"
        elif "master" in edu or "m.tech" in edu or "msc" in edu or "mca" in edu:
            level = "Master's"
        elif "bachelor" in edu or "b.tech" in edu or "bsc" in edu or "bca" in edu:
            level = "Bachelor's"
        else:
            level = "Other/Unspecified"
        education_levels[level] = education_levels.get(level, 0) + 1

        years = a["experience_years"] or 0
        if years < 1:
            experience_buckets["0-1 yrs"] += 1
        elif years < 3:
            experience_buckets["1-3 yrs"] += 1
        elif years < 6:
            experience_buckets["3-6 yrs"] += 1
        else:
            experience_buckets["6+ yrs"] += 1

    top_skills = sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    return jsonify({
        "total_applicants": len(applicants),
        "top_skills": top_skills,
        "job_role_distribution": role_counter,
        "resume_score_distribution": score_buckets,
        "monthly_users": dict(sorted(monthly_users.items())),
        "education_distribution": education_levels,
        "experience_distribution": experience_buckets,
    }), 200


# ---------------------------------------------------------------- API: Report

@app.route("/api/report/<int:applicant_id>", methods=["GET"])
@login_required
def download_report(applicant_id):
    a = db.get_applicant(applicant_id)
    if not a:
        return jsonify({"error": "Applicant not found."}), 404
    if not session.get("is_admin") and a.get("user_id") != session["user_id"]:
        return jsonify({"error": "You don't have access to this record."}), 403

    lines = [
        "=" * 60,
        "AI RESUME ANALYZER — ANALYSIS REPORT",
        "=" * 60,
        f"Name: {a['name']}",
        f"Email: {a['email']}",
        f"Phone: {a['phone']}",
        f"LinkedIn: {a['linkedin']}",
        f"GitHub: {a['github']}",
        f"Upload Date: {a['upload_date']}",
        "-" * 60,
        "SCORES",
        f"  Overall Resume Score : {a['resume_score']} ({a['overall_rating']})",
        f"  ATS Compatibility    : {a['ats_score']}",
        f"  Formatting           : {a['formatting_score']}",
        f"  Readability          : {a['readability_score']}",
        f"  Experience           : {a['experience_score']}",
        f"  Education            : {a['education_score']}",
        f"  Skills               : {a['skill_score']}",
        "-" * 60,
        "TOP PREDICTED ROLES",
    ]
    for p in a["predictions"]:
        lines.append(f"  {p['role']}: {p['confidence']}%")

    lines += ["-" * 60, "TECHNICAL SKILLS DETECTED"]
    for category, items in a["skills"].items():
        if items and category != "all_technical":
            lines.append(f"  {category.replace('_', ' ').title()}: {', '.join(items)}")

    rec = a["recommendations"]
    lines += ["-" * 60, "MISSING SKILLS FOR TOP ROLE"]
    lines.append("  " + (", ".join(rec.get("missing_skills", [])) or "None — great coverage!"))

    lines += ["-" * 60, "RESUME IMPROVEMENT TIPS"]
    for tip in rec.get("resume_tips", []):
        lines.append(f"  - {tip}")

    lines += ["-" * 60, "RECOMMENDED COURSES"]
    for c in rec.get("recommended_courses", []):
        lines.append(f"  - {c['name']} ({c['difficulty']}, {c['duration']})")

    lines += ["=" * 60, "Generated by AI Resume Analyzer"]

    report_text = "\n".join(lines)
    buffer = io.BytesIO(report_text.encode("utf-8"))
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"resume_report_{applicant_id}.txt",
    )


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)

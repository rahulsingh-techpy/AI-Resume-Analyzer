# AI Resume Analyzer

A premium, dark-themed AI Resume Analyzer SaaS-style web app: upload a PDF resume, get an instant ATS score, full resume breakdown, predicted job roles, missing-skill analysis, personalized recommendations, an interview-prep kit, and an admin analytics dashboard.

**Stack:** HTML5 + CSS3 + JavaScript + Bootstrap 5 (frontend) · Python Flask (backend) · SQLite (database) · pdfminer.six, scikit-learn, pandas, NumPy

## Folder Structure

```
ResumeAnalyzer/
├── app.py                  # Flask app & all routes
├── requirements.txt
├── templates/
│   ├── index.html           # Landing page (hero, features, upload)
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── dashboard.html        # Applicant dashboard (per-user history)
│   └── admin.html            # Admin dashboard (Plotly analytics)
├── static/
│   ├── css/style.css         # Dark glassmorphism theme
│   ├── js/
│   │   ├── main.js           # Shared: toasts, scroll reveal, progress rings
│   │   ├── upload.js         # Drag-and-drop upload + analysis trigger
│   │   ├── dashboard.js       # Renders analysis results
│   │   └── admin.js           # Applicant table + Plotly charts
│   ├── images/
│   └── uploads/              # Uploaded resumes are stored here
├── database/
│   └── resume.db             # Auto-created SQLite DB on first run
├── models/                   # Reserved for future trained ML models
├── utils/
│   ├── data.py                # Skill taxonomy, job-role profiles, course catalog, interview Qs
│   ├── parser.py               # PDF text extraction + structured field parsing
│   ├── analyzer.py             # ATS / formatting / readability / experience / education / skill scoring
│   ├── predictor.py            # TF-IDF + cosine-similarity job role prediction
│   ├── recommender.py          # Tips, courses, roadmap, salary estimate, interview prep
│   └── db.py                   # SQLite data access layer
└── README.md
```

## 1. Setup

```bash
cd ResumeAnalyzer
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Visit **http://localhost:5000**. The SQLite database and uploads folder are created automatically on first run.

## 2. Authentication

The app now has full user accounts:

- **Register** (`/register`) — creates an account with a hashed password (Werkzeug's `generate_password_hash`).
- **Login** (`/login`) — verifies credentials and starts a signed Flask session (`app.secret_key`, override via `SECRET_KEY` env var in production).
- **Logout** (`/logout`) — clears the session.
- **Session-scoped data** — `/dashboard`, resume uploads, and `/api/history` all require login and are automatically scoped to `session["user_id"]`; one user can never see another user's analyses, even by guessing an applicant ID (enforced server-side, not just hidden in the UI).
- **Admin accounts** — a seeded admin (`admin@resumeai.com` / `admin123`) is created automatically on first run so `/admin` is usable out of the box. Admin-only routes are protected by an `is_admin` flag in both the session and an `admin_required` decorator.

⚠️ Change the seeded admin password and `SECRET_KEY` before any real deployment — these are dev-only defaults.

## 3. How it works

1. **Upload** — drag-and-drop or browse a PDF resume on the landing page (`/`).
2. **Parse** (`utils/parser.py`) — `pdfminer.six` extracts raw text; regex + section-heading heuristics pull out name, email, phone, LinkedIn, GitHub, education, experience, projects, certifications, and languages. Skills are matched against a 100+ term taxonomy (`utils/data.py`) across programming languages, frameworks, databases, cloud tools, dev tools, data/ML tools, and soft skills.
3. **Score** (`utils/analyzer.py`) — six sub-scores (ATS compatibility, formatting, readability, experience, education, skills) are computed with transparent rule-based heuristics and combined into a weighted overall Resume Score + rating label.
4. **Predict** (`utils/predictor.py`) — TF-IDF vectorizes the resume's detected skills against 10 job-role skill profiles and ranks roles by cosine similarity, producing a confidence percentage per role.
5. **Recommend** (`utils/recommender.py`) — generates resume tips, a missing-skills list, matched courses, certifications, project ideas, a learning roadmap, LinkedIn/GitHub/portfolio tips, an illustrative salary range, a career path, and interview questions (technical/coding/HR/behavioral).
6. **Store** (`utils/db.py`) — every analysis is saved to SQLite for the applicant dashboard's history view and the admin dashboard.
7. **Dashboards** — `/dashboard` shows the latest analysis with animated circular score rings, skill pills, and tabs; `/admin` lists all applicants (search/filter/delete/export-CSV) plus interactive Plotly charts (score distribution, role distribution, top skills, education/experience distribution, monthly uploads).

## 4. API Reference

| Method | Endpoint                          | Description                                  |
|--------|------------------------------------|-----------------------------------------------|
| GET/POST | `/register`                      | User registration page / submit              |
| GET/POST | `/login`                         | Login page / submit                           |
| GET    | `/logout`                          | Clear session                                 |
| GET    | `/api/me`                          | Current logged-in user (or null)              |
| POST   | `/api/upload`                      | Upload + analyze a PDF resume (login required) |
| GET    | `/api/applicant/<id>`              | Full stored analysis (owner or admin only)    |
| GET    | `/api/history`                     | Logged-in user's own past uploads             |
| GET    | `/api/admin/applicants?search=&role=` | List/search/filter all applicants (admin) |
| DELETE | `/api/admin/applicant/<id>`        | Delete an applicant record (admin)            |
| GET    | `/api/admin/export-csv`            | Download all applicants as CSV (admin)        |
| GET    | `/api/admin/analytics`             | Aggregated stats for the Plotly charts (admin) |
| GET    | `/api/report/<id>`                 | Download a plaintext analysis report (owner or admin) |

## 5. Design choices & honest limitations

This was built fully offline (no internet access in the build environment), so a few items from a "dream" spec are implemented as solid, transparent approximations rather than trained ML models:

- **Parsing** uses regex + heading-based section splitting instead of spaCy NER / PyResparser, since downloading spaCy's language models requires internet access. It's dependency-light and reliable for standard resume layouts; swap in spaCy NER inside `extract_name()` for production-grade name detection if you have model access.
- **Job role prediction** uses TF-IDF + cosine similarity against curated role/skill profiles (`utils/data.py`) rather than a classifier trained on a labeled resume dataset (no such dataset was available offline). It's explainable and tunable — extend `JOB_ROLE_SKILLS` to add more roles, or swap in a trained scikit-learn classifier once you have labeled data.
- **Salary estimates** are simplified, illustrative bands (not live market data) — labeled as such in the UI.
- **AI Resume Rewrite / AI Cover Letter Generator** are natural follow-on features best powered by an LLM API call (e.g. the Anthropic API) — not included here since that requires your own API key, but `utils/recommender.py` is structured so you can add a `generate_rewrite()` function that calls out to an LLM using the parsed resume + target job role.
- **Dark mode toggle** is present in the UI; the app ships dark-only by design per the brief (toggle currently shows a confirmation toast — wire it to a CSS custom-property swap if you want a real light theme).

## 6. Extending

- Add `.docx` support: integrate `python-docx` and a new branch in `parser.py`.
- Add authentication: wrap `/admin/*` routes with a login-required decorator and add an admin login page.
- Swap SQLite for PostgreSQL/MySQL: only `utils/db.py` needs to change (it isolates all SQL).
- Add a trained ML classifier for job-role prediction once you have a labeled resume dataset — `utils/predictor.py` is the only file to touch.

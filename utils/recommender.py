"""
recommender.py — Personalized recommendation engine.

Generates resume improvement tips, missing-skill-based course
recommendations, certification suggestions, project ideas, a learning
roadmap, LinkedIn/GitHub/portfolio tips, and interview preparation
content, all driven by the parsed resume + computed scores + predicted
job role.
"""

from utils.data import COURSE_CATALOG, INTERVIEW_QUESTIONS, JOB_ROLE_SKILLS
from utils.analyzer import detect_action_verb_usage, has_quantifiable_achievements
from utils.predictor import skill_gap_for_role


def recommend_courses(missing_skills: list, limit: int = 6) -> list:
    missing_lower = set(s.lower() for s in missing_skills)
    scored = []
    for course in COURSE_CATALOG:
        overlap = len(set(s.lower() for s in course["skills"]) & missing_lower)
        if overlap > 0:
            scored.append((overlap, course))
    scored.sort(key=lambda x: x[0], reverse=True)
    recommended = [c for _, c in scored[:limit]]

    if len(recommended) < limit:
        extra = [c for c in COURSE_CATALOG if c not in recommended]
        recommended += extra[: limit - len(recommended)]

    return recommended


def resume_improvement_tips(parsed: dict, scores: dict) -> list:
    tips = []
    verbs = detect_action_verb_usage(parsed["raw_text"])

    if scores["ats_score"] < 80:
        tips.append("Avoid tables, columns, and graphics — they can break ATS parsing. Stick to a clean single-column layout.")
    if scores["formatting_score"] < 80:
        tips.append("Use consistent bullet points for each role/project instead of long paragraphs.")
    if scores["readability_score"] < 80:
        tips.append("Shorten long sentences and avoid overly complex words to improve readability.")
    if not has_quantifiable_achievements(parsed["raw_text"]):
        tips.append("Add measurable results to your bullet points (e.g. 'reduced load time by 30%', 'managed a team of 6').")
    if verbs["weak_phrases_used"]:
        tips.append(f"Replace weak phrases like \"{verbs['weak_phrases_used'][0]}\" with strong action verbs (e.g. 'led', 'built', 'optimized').")
    if parsed["linkedin"] == "Not Found":
        tips.append("Add a LinkedIn profile link near your contact details.")
    if parsed["github"] == "Not Found" and parsed["skills"]["all_technical"]:
        tips.append("Add a GitHub link to showcase your code and projects.")
    if parsed["experience_years"] == 0 and parsed["experience_section"] == "Not clearly detected":
        tips.append("Add an Experience section, even for internships, freelance work, or significant academic projects.")

    if not tips:
        tips.append("Your resume looks solid! Consider tailoring keywords per job application for even better ATS matching.")

    return tips


def linkedin_tips(parsed: dict) -> list:
    tips = [
        "Use a professional headshot and a headline that states your target role clearly.",
        "Write a concise 'About' summary highlighting your top 3 skills and career goals.",
        "List all relevant projects and skills, and request endorsements/recommendations from peers.",
    ]
    if parsed["linkedin"] == "Not Found":
        tips.insert(0, "Create and link a LinkedIn profile — most recruiters check it before responding.")
    return tips


def github_tips(parsed: dict) -> list:
    tips = [
        "Pin your 4-6 best repositories with clear, descriptive README files.",
        "Include setup instructions, screenshots/GIFs, and live demo links where possible.",
        "Keep a consistent commit history to show ongoing activity.",
    ]
    if parsed["github"] == "Not Found":
        tips.insert(0, "Create a GitHub profile and upload your project source code — it's one of the first things technical recruiters check.")
    return tips


def portfolio_suggestions(parsed: dict) -> list:
    return [
        "Build a personal portfolio website showcasing 3-5 of your best projects with live links.",
        "Include a short case-study writeup per project: problem, your approach, tech used, and outcome.",
        "Add a downloadable PDF version of your resume on the portfolio site.",
    ]


def project_suggestions(top_role: str) -> list:
    suggestions_by_role = {
        "Software Engineer": ["Build a URL shortener with rate limiting", "Implement a simple in-memory key-value store"],
        "Frontend Developer": ["Build a responsive e-commerce UI clone", "Create a real-time chat UI with WebSockets"],
        "Backend Developer": ["Build a REST API with authentication and role-based access", "Design a scalable notification service"],
        "Full Stack Developer": ["Build a full-stack task management app (CRUD + auth)", "Create a blogging platform with comments and likes"],
        "Java Developer": ["Build a Spring Boot microservice with JPA + REST", "Implement a library management system"],
        "Python Developer": ["Build a Flask/Django REST API with JWT auth", "Create a web scraper + data pipeline with Pandas"],
        "Cloud Engineer": ["Deploy a containerized app on AWS ECS/Kubernetes", "Set up a CI/CD pipeline with Terraform + GitHub Actions"],
        "Data Analyst": ["Build an interactive sales dashboard with Plotly/Power BI", "Analyze a public dataset and publish insights"],
        "Machine Learning Engineer": ["Train and deploy an image classifier as a web API", "Build an end-to-end ML pipeline with MLflow tracking"],
        "Cyber Security Analyst": ["Set up a home lab SIEM with log analysis", "Perform a vulnerability assessment on a sandbox app"],
    }
    return suggestions_by_role.get(top_role, ["Build a project that demonstrates your top 3 technical skills end-to-end."])


def learning_roadmap(missing_skills: list) -> list:
    roadmap = []
    for i, skill in enumerate(missing_skills[:5], start=1):
        roadmap.append(f"Step {i}: Learn {skill.title()} fundamentals, then build one small project applying it.")
    if not roadmap:
        roadmap.append("You already cover the core skills for your target role — focus on depth and real-world projects.")
    return roadmap


def estimate_salary_range(top_role: str, experience_years: float) -> str:
    """Rough illustrative salary band (USD/year) based on role + experience.
    NOTE: These are simplified placeholder estimates, not live market data."""
    base_ranges = {
        "Software Engineer": (65000, 130000),
        "Frontend Developer": (60000, 120000),
        "Backend Developer": (65000, 125000),
        "Full Stack Developer": (70000, 135000),
        "Java Developer": (65000, 120000),
        "Python Developer": (65000, 125000),
        "Cloud Engineer": (75000, 145000),
        "Data Analyst": (55000, 105000),
        "Machine Learning Engineer": (85000, 160000),
        "Cyber Security Analyst": (75000, 140000),
    }
    lo, hi = base_ranges.get(top_role, (55000, 110000))
    growth = min(experience_years, 10) * 0.06
    lo = int(lo * (1 + growth))
    hi = int(hi * (1 + growth))
    return f"${lo:,} - ${hi:,} / year (estimated, varies by location & company)"


def career_path_suggestions(top_role: str) -> list:
    paths = {
        "Software Engineer": ["Software Engineer", "Senior Software Engineer", "Staff Engineer", "Engineering Manager"],
        "Frontend Developer": ["Frontend Developer", "Senior Frontend Developer", "Frontend Architect", "UI Engineering Lead"],
        "Backend Developer": ["Backend Developer", "Senior Backend Developer", "Backend Architect", "Engineering Manager"],
        "Full Stack Developer": ["Full Stack Developer", "Senior Full Stack Engineer", "Tech Lead", "CTO/Founding Engineer"],
        "Java Developer": ["Java Developer", "Senior Java Developer", "Java Architect", "Engineering Manager"],
        "Python Developer": ["Python Developer", "Senior Python Developer", "Backend Architect", "Engineering Manager"],
        "Cloud Engineer": ["Cloud Engineer", "Senior Cloud Engineer", "Cloud Architect", "DevOps/Platform Lead"],
        "Data Analyst": ["Data Analyst", "Senior Data Analyst", "Analytics Manager", "Head of Analytics"],
        "Machine Learning Engineer": ["ML Engineer", "Senior ML Engineer", "ML Architect", "Head of AI/ML"],
        "Cyber Security Analyst": ["Security Analyst", "Senior Security Analyst", "Security Architect", "CISO"],
    }
    return paths.get(top_role, [top_role, f"Senior {top_role}", f"Lead {top_role}", f"Head of {top_role}"])


def generate_full_recommendations(parsed: dict, scores: dict, predictions: list) -> dict:
    top_role = predictions[0]["role"] if predictions else "Software Engineer"
    gap = skill_gap_for_role(parsed, top_role)

    return {
        "top_predicted_role": top_role,
        "missing_skills": gap["missing_skills"],
        "matched_skills": gap["matched_skills"],
        "resume_tips": resume_improvement_tips(parsed, scores),
        "recommended_courses": recommend_courses(gap["missing_skills"]),
        "recommended_certifications": [c["name"] for c in recommend_courses(gap["missing_skills"], limit=3)],
        "project_suggestions": project_suggestions(top_role),
        "learning_roadmap": learning_roadmap(gap["missing_skills"]),
        "linkedin_tips": linkedin_tips(parsed),
        "github_tips": github_tips(parsed),
        "portfolio_suggestions": portfolio_suggestions(parsed),
        "interview_prep": INTERVIEW_QUESTIONS,
        "salary_estimate": estimate_salary_range(top_role, parsed["experience_years"]),
        "career_path": career_path_suggestions(top_role),
    }

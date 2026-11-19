"""
predictor.py — Job role prediction.

Uses TF-IDF + cosine similarity (scikit-learn) between the resume's
extracted skill set and each job role's representative skill profile,
producing a ranked list of roles with confidence percentages.

This is a content-based similarity model rather than a trained
classifier (no labeled resume dataset is available offline), but it
gives sensible, explainable rankings and is easy to swap for a trained
scikit-learn classifier (e.g. SVM/LogisticRegression on a labeled
resume corpus) later — see README for upgrade notes.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.data import JOB_ROLE_SKILLS


def predict_job_roles(parsed: dict, top_n: int = 5) -> list:
    resume_skills = parsed["skills"]["all_technical"]
    resume_doc = " ".join(resume_skills) if resume_skills else parsed["raw_text"][:2000]

    role_names = list(JOB_ROLE_SKILLS.keys())
    role_docs = [" ".join(skills) for skills in JOB_ROLE_SKILLS.values()]

    corpus = [resume_doc] + role_docs
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Empty vocabulary (e.g. resume has no recognizable skills)
        return [{"role": r, "confidence": 0.0} for r in role_names[:top_n]]

    resume_vec = tfidf_matrix[0:1]
    role_vecs = tfidf_matrix[1:]

    similarities = cosine_similarity(resume_vec, role_vecs)[0]

    results = list(zip(role_names, similarities))
    results.sort(key=lambda x: x[1], reverse=True)

    total = sum(s for _, s in results) or 1.0
    predictions = []
    for role, sim in results[:top_n]:
        confidence = round(float(sim / total) * 100, 1) if total > 0 else 0.0
        predictions.append({"role": role, "confidence": confidence})

    return predictions


def skill_gap_for_role(parsed: dict, role: str) -> dict:
    """Compare resume skills against a specific role's required skill profile."""
    required = set(s.lower() for s in JOB_ROLE_SKILLS.get(role, []))
    have = set(s.lower() for s in parsed["skills"]["all_technical"])

    matched = sorted(required & have)
    missing = sorted(required - have)

    return {"role": role, "matched_skills": matched, "missing_skills": missing}

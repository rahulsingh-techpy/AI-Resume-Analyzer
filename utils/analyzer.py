"""
analyzer.py — Resume scoring engine.

Computes Resume Score, ATS Compatibility, Formatting, Readability,
Experience, Education, and Skill scores (0-100 each), plus an overall
rating. Also runs grammar/action-verb checks for the recommendation
engine.

All scoring here is rule-based and transparent (no external API calls),
so the app works fully offline and the scoring logic is easy to audit
and tune.
"""

import re
from utils.data import STRONG_ACTION_VERBS, WEAK_VERBS_TO_AVOID


def _clamp(value, lo=0, hi=100):
    return max(lo, min(hi, value))


def score_ats_compatibility(parsed: dict) -> float:
    """Checks resume against common ATS-friendliness heuristics."""
    score = 100.0
    text = parsed["raw_text"]

    if parsed["email"] == "Not Found":
        score -= 15
    if parsed["phone"] == "Not Found":
        score -= 10
    if not parsed["skills"]["all_technical"]:
        score -= 20
    if parsed["word_count"] < 150:
        score -= 15
    if len(re.findall(r"[^\x00-\x7F]", text)) > 50:
        score -= 10  # heavy use of special/unicode glyphs can confuse ATS parsers
    if "education" not in [s.lower() for s in parsed.keys()] and parsed["education"] == "Not clearly detected":
        score -= 10

    return _clamp(score)


def score_formatting(parsed: dict) -> float:
    """Approximates formatting quality using structural signals."""
    score = 100.0
    text = parsed["raw_text"]
    lines = [l for l in text.splitlines() if l.strip()]

    if len(lines) < 10:
        score -= 25
    avg_line_len = sum(len(l) for l in lines) / max(len(lines), 1)
    if avg_line_len > 150:
        score -= 15  # likely missing line breaks / poor structure
    bullet_markers = len(re.findall(r"^[\s]*[•\-\*]\s+", text, re.MULTILINE))
    if bullet_markers < 3:
        score -= 15  # resumes should use bullet points for readability
    if parsed["education"] == "Not clearly detected":
        score -= 10
    if parsed["experience_section"] == "Not clearly detected":
        score -= 10

    return _clamp(score)


def score_readability(parsed: dict) -> float:
    """Simplified Flesch-style readability proxy using sentence/word length."""
    text = parsed["raw_text"]
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    words = re.findall(r"\b\w+\b", text)

    if not sentences or not words:
        return 50.0

    avg_words_per_sentence = len(words) / len(sentences)
    long_word_ratio = sum(1 for w in words if len(w) > 8) / len(words)

    score = 100.0
    if avg_words_per_sentence > 28:
        score -= 20
    elif avg_words_per_sentence > 20:
        score -= 10
    score -= long_word_ratio * 40

    return _clamp(score)


def score_experience(parsed: dict) -> float:
    years = parsed["experience_years"]
    has_section = parsed["experience_section"] != "Not clearly detected"

    score = 0.0
    if has_section:
        score += 40
    score += min(years, 8) * 7.5  # up to 60 more points for 8+ years

    return _clamp(score)


def score_education(parsed: dict) -> float:
    edu_text = parsed["education"].lower()
    if edu_text == "not clearly detected":
        return 30.0

    score = 60.0
    degree_keywords = ["bachelor", "b.tech", "b.e", "m.tech", "master", "phd", "bsc", "msc", "b.sc", "m.sc", "mca", "bca"]
    if any(k in edu_text for k in degree_keywords):
        score += 25
    if re.search(r"\b(19|20)\d{2}\b", edu_text):
        score += 15  # graduation year present

    return _clamp(score)


def score_skills(parsed: dict) -> float:
    technical_count = len(parsed["skills"]["all_technical"])
    soft_count = len(parsed["skills"]["soft_skills"])

    score = min(technical_count, 15) * 5.5  # up to 82.5
    score += min(soft_count, 5) * 3.5       # up to 17.5

    return _clamp(score)


def detect_action_verb_usage(text: str) -> dict:
    lowered = text.lower()
    strong_found = [v for v in STRONG_ACTION_VERBS if v in lowered]
    weak_found = [v for v in WEAK_VERBS_TO_AVOID if v in lowered]
    return {"strong_verbs_used": strong_found, "weak_phrases_used": weak_found}


def has_quantifiable_achievements(text: str) -> bool:
    return bool(re.search(r"\b\d+%|\$\d+[kKmM]?|\b\d{2,}\+?\b", text))


def compute_all_scores(parsed: dict) -> dict:
    ats = score_ats_compatibility(parsed)
    formatting = score_formatting(parsed)
    readability = score_readability(parsed)
    experience = score_experience(parsed)
    education = score_education(parsed)
    skill = score_skills(parsed)

    overall = round(
        ats * 0.25 + formatting * 0.15 + readability * 0.10 +
        experience * 0.20 + education * 0.15 + skill * 0.15,
        1
    )

    return {
        "resume_score": overall,
        "ats_score": round(ats, 1),
        "formatting_score": round(formatting, 1),
        "readability_score": round(readability, 1),
        "experience_score": round(experience, 1),
        "education_score": round(education, 1),
        "skill_score": round(skill, 1),
        "overall_rating": _rating_label(overall),
    }


def _rating_label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Average"
    return "Needs Improvement"

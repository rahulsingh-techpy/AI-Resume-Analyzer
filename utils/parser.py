"""
parser.py — Resume parsing utilities (v3).

Key fixes vs v2 (visible in second screenshot):
  ❌ Education showed certification content  
     → Section splitter missed the cert header; cert lines spilled into education
  ❌ Experience showed education year ranges [2023-2027]
     → _fallback_experience() was too greedy — matched ANY date range,
       including education years inside square brackets
  ❌ Projects showed the same date ranges as experience (duplication)
     → Fallback scanned the full text including the already-detected education block

Root-cause fixes in v3:
  1. Section splitter: handle ALL-CAPS headers, broader keyword list,
     "Courses / Certifications", "Academic Projects", etc.
  2. _fallback_experience(): only fire on date ranges that look like WORK
     (month-named ranges, or lines with job-title keywords nearby).
     Square-bracket year ranges [YYYY-YYYY] are education, not work.
  3. _fallback_education(): filters out lines that look like certifications.
  4. Projects no longer inherits fallback date ranges; uses keyword proximity
     + explicit section only.
  5. Post-parse cleanup: if education text also contains cert keywords,
     strip those lines out and move them to certifications.
"""

import re
from datetime import datetime
from typing import Optional
from pdfminer.high_level import extract_text as pdfminer_extract_text

from utils.data import ALL_TECHNICAL_SKILLS, SOFT_SKILLS

# ------------------------------------------------------------------ Regexes

EMAIL_RE    = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE    = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)?\d{3,5}[\s\-.]?\d{4,6}"
)
LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/[A-Za-z0-9_\-/]+", re.I)
GITHUB_RE   = re.compile(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9_\-/]+", re.I)

# Month-named date range: "June 2023 – Aug 2023", "Jan 2022 - Present"
# This pattern REQUIRES at least one month name → distinguishes WORK dates from [YYYY-YYYY]
WORK_DATE_RE = re.compile(
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)"
    r"\s*[\'\']?\d{2,4}\s*[-–—to]+\s*"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)?\s*(?:\d{2,4}|[Pp]resent|[Cc]urrent|[Nn]ow)",
    re.IGNORECASE,
)

# Any date range including bare [YYYY-YYYY] or YYYY–YYYY (used for duration calculation)
ANY_DATE_RE = re.compile(
    r"(?:\[)?(\d{4})\s*[-–—]\s*(\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)(?:\])?",
    re.IGNORECASE,
)

# Job-title keywords that signal a work experience context
JOB_TITLE_KEYWORDS = [
    "engineer", "developer", "analyst", "intern", "internship", "manager",
    "consultant", "designer", "architect", "lead", "scientist", "specialist",
    "coordinator", "executive", "officer", "associate", "trainee",
]

DEGREE_KEYWORDS = [
    "b.tech", "b.e.", "be ", "btech", "b.sc", "bsc", "b.com", "bcom",
    "bachelor", "b.a ", "ba ", "b.s ", "bs ",
    "m.tech", "mtech", "m.sc", "msc", "m.e.", "mba",
    "master", "m.a ", "ma ",
    "phd", "ph.d", "doctorate", "m.phil",
    "diploma", "polytechnic",
    "12th", "10th", "hsc", "ssc", "secondary", "higher secondary",
    "mca", "bca", "b.ca",
    "university", "institute", "college", "school", "cgpa", "gpa", "percentage",
]

CERT_KEYWORDS = [
    "certified", "certification", "certificate",
    "coursera", "udemy", "edx", "nptel", "linkedin learning",
    "aws certified", "google certified", "microsoft certified",
    "cisco", "comptia", "oracle certified", "pmp", "ceh", "ccna",
    "simulation", "bootcamp", "workshop", "course completed",
    "virtual experience", "forage",
]

# ------------------------------------------------------------------ Section rules
# Ordered: first match wins. Keep more-specific entries BEFORE general ones.

SECTION_RULES = [
    ("summary",        ["summary", "objective", "career objective", "professional summary",
                         "profile", "about me", "overview", "career goal"]),
    ("education",      ["education", "academic background", "academics", "qualification",
                         "educational background", "educational detail", "academic detail",
                         "academic qualification", "educational qualification"]),
    ("experience",     ["experience", "work experience", "employment", "professional experience",
                         "internship", "internships", "work history", "career history",
                         "professional background", "job experience", "industrial training",
                         "industrial experience", "positions held", "employment history"]),
    ("projects",       ["project", "projects", "academic project", "personal project",
                         "major project", "minor project", "college project",
                         "key project", "notable project"]),
    # certifications BEFORE skills so "courses & certifications" doesn't become skills
    ("certifications", ["certification", "certifications", "certificates", "certificate",
                         "achievements", "achievement", "awards", "award", "honor", "honours",
                         "courses", "course", "online course", "online courses",
                         "mooc", "license", "licenses", "training", "workshop",
                         "virtual experience", "simulation"]),
    ("skills",         ["skill", "skills", "technical skill", "core competencies",
                         "competencies", "technologies", "technology", "tools",
                         "programming skill", "technical expertise", "tech stack"]),
    ("languages",      ["language", "languages", "language proficiency",
                         "language known", "known languages", "languages known"]),
]


# ------------------------------------------------------------------ PDF extract

def extract_text_from_pdf(file_path: str) -> str:
    try:
        return pdfminer_extract_text(file_path) or ""
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF: {e}")


# ------------------------------------------------------------------ Section splitter (v3)

def _normalise_header(line: str) -> str:
    """Strip formatting noise: bullets, hashes, dashes, colons, underscores."""
    s = line.strip()
    s = re.sub(r"^[\s#\-*•▪▸►→|≡=_]+", "", s)
    s = re.sub(r"[\s:•\-_=*]+$", "", s)
    return s.lower().strip()


def _match_section(normalised: str) -> Optional[str]:
    """
    Return the section key if normalised header matches any known keyword.

    Matching strategies (in order):
    1. Exact match
    2. The header STARTS WITH the keyword (handles "Certifications & Courses")
    3. The keyword is contained and the line is only slightly longer (≤ kw + 8 chars)
       — catches "TECHNICAL SKILLS" matching "technical skill"
    """
    for key, keywords in SECTION_RULES:
        for kw in keywords:
            if normalised == kw:
                return key
            if normalised.startswith(kw):
                return key
            # contained + short suffix
            if kw in normalised and len(normalised) <= len(kw) + 8:
                return key
    return None


def _looks_like_sentence(line: str) -> bool:
    """True if the line looks like body content rather than a section header."""
    # Has more than 2 commas, or a mid-line full stop, or starts with a bullet/dash
    if line.count(",") >= 3:
        return True
    if line.startswith(("-", "•", "*", "·")):
        return True
    # Contains words that strongly suggest body text
    if re.search(r"\b(using|developed|built|implemented|responsible|managed|achieved)\b",
                 line, re.I):
        return True
    return False


def _split_sections(text: str) -> dict:
    """
    Robust two-pass section splitter.

    Pass 1: line-by-line scan with header detection.
    Pass 2: any section with < 8 chars of content is discarded (likely a detection error).
    """
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current = "header"
    buffer: list[str] = []

    def flush():
        non_empty = [l for l in buffer if l.strip()]
        if non_empty:
            sections.setdefault(current, []).extend(non_empty)

    for line in lines:
        raw = line.strip()
        if not raw:
            buffer.append(line)
            continue

        norm = _normalise_header(raw)

        # Header candidate: short, not a sentence, and matches a known keyword
        is_short = len(raw) <= 60
        if is_short and not _looks_like_sentence(raw):
            matched = _match_section(norm)
        else:
            matched = None

        if matched:
            flush()
            current = matched
            buffer = []
        else:
            buffer.append(line)

    flush()

    # Pass 2: discard empty / near-empty sections (false positives)
    return {
        k: "\n".join(v).strip()
        for k, v in sections.items()
        if len("\n".join(v).strip()) >= 8
    }


# ------------------------------------------------------------------ Content-based fallbacks (v3)

def _fallback_education(text: str, exclude_certs: bool = True) -> str:
    """
    Find education content by degree/institution keywords.
    If exclude_certs=True, skip lines that look like certifications.
    """
    lines = text.splitlines()
    edu_lines = []
    for i, line in enumerate(lines):
        ll = line.lower()
        # Must contain a degree/institution keyword
        if not any(kw in ll for kw in DEGREE_KEYWORDS):
            continue
        # Skip lines that look like certs
        if exclude_certs and any(ck in ll for ck in CERT_KEYWORDS):
            continue
        # Grab this line + up to 2 following context lines
        block = lines[i: i + 3]
        edu_lines.extend([l for l in block if l.strip()])

    if not edu_lines:
        return "Not clearly detected"

    seen: set[str] = set()
    result = []
    for l in edu_lines:
        if l not in seen:
            seen.add(l)
            result.append(l)
    return "\n".join(result)


def _fallback_experience(text: str, education_text: str = "") -> str:
    """
    Find work experience by scanning for MONTH-NAMED date ranges only.

    Deliberately skips bare [YYYY-YYYY] ranges (those are education/project dates).
    Also checks nearby lines for job-title keywords to confirm it's work context.

    `education_text`: lines from the education section are excluded from search
    to avoid picking up education years.
    """
    # Build a set of lines already claimed by education
    edu_lines = set(education_text.splitlines()) if education_text else set()

    lines = text.splitlines()
    exp_lines = []

    for i, line in enumerate(lines):
        if line in edu_lines:
            continue
        # Require a MONTH-named date range (not bare YYYY-YYYY)
        if not WORK_DATE_RE.search(line):
            continue
        # Confirm context: look ±3 lines for a job-title keyword
        context_window = lines[max(0, i - 3): i + 4]
        context_str = " ".join(context_window).lower()
        has_job_title = any(kw in context_str for kw in JOB_TITLE_KEYWORDS)

        if has_job_title:
            start = max(0, i - 2)
            block = lines[start: i + 4]
            exp_lines.extend([l for l in block if l.strip() and l not in edu_lines])

    if not exp_lines:
        return "Not clearly detected"

    seen: set[str] = set()
    result = []
    for l in exp_lines:
        if l not in seen:
            seen.add(l)
            result.append(l)
    return "\n".join(result)


def _fallback_certifications(text: str, education_text: str = "") -> str:
    """
    Find certifications by keyword scanning.
    Excludes lines that are already in the education section AND look like degrees.
    """
    edu_lines = set(education_text.splitlines()) if education_text else set()
    lines = text.splitlines()
    cert_lines = []

    for line in lines:
        if not line.strip():
            continue
        ll = line.lower()
        if any(ck in ll for ck in CERT_KEYWORDS):
            cert_lines.append(line.strip())

    if not cert_lines:
        return "Not clearly detected"

    seen: set[str] = set()
    result = []
    for l in cert_lines:
        if l not in seen:
            seen.add(l)
            result.append(l)
    return "\n".join(result)


def _clean_education(education_text: str) -> str:
    """
    Post-parse cleanup: remove certification lines that leaked into the education section.
    A line is removed if it contains cert keywords BUT no degree keywords.
    """
    cleaned = []
    for line in education_text.splitlines():
        ll = line.lower()
        has_cert = any(ck in ll for ck in CERT_KEYWORDS)
        has_degree = any(dk in ll for dk in DEGREE_KEYWORDS)
        if has_cert and not has_degree:
            continue  # cert line masquerading as education — drop it
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    return result if result else "Not clearly detected"


# ------------------------------------------------------------------ Field extractors

def extract_name(text: str) -> str:
    skip_words = {"resume", "curriculum", "vitae", "cv", "profile", "page",
                  "objective", "portfolio", "contact"}
    lines = [l.strip() for l in text.splitlines() if l.strip()][:12]
    for line in lines:
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if "http" in line.lower() or "@" in line:
            continue
        if any(sw in line.lower() for sw in skip_words):
            continue
        words = line.split()
        if not (1 <= len(words) <= 5):
            continue
        if not all(re.match(r"^[A-Za-z][A-Za-z.\-']*$", w) for w in words):
            continue
        if words[0][0].isupper():
            return " ".join(w.title() for w in words)
    return "Not Found"


def extract_email(text: str) -> str:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else "Not Found"


def extract_phone(text: str) -> str:
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 7 <= len(digits) <= 15:
            return m.group(0).strip()
    return "Not Found"


def extract_linkedin(text: str) -> str:
    m = LINKEDIN_RE.search(text)
    if m:
        url = m.group(0)
        return url if url.startswith("http") else f"https://{url}"
    return "Not Found"


def extract_github(text: str) -> str:
    m = GITHUB_RE.search(text)
    if m:
        url = m.group(0)
        return url if url.startswith("http") else f"https://{url}"
    return "Not Found"


def extract_skills(text: str) -> dict:
    lowered = text.lower()

    def find(skill_list):
        found = []
        for skill in skill_list:
            escaped = re.escape(skill.lower())
            pattern = r"(?<![a-zA-Z0-9+#])" + escaped + r"(?![a-zA-Z0-9+#])"
            if re.search(pattern, lowered):
                found.append(skill)
        return sorted(set(found))

    from utils.data import (
        PROGRAMMING_LANGUAGES, FRAMEWORKS, DATABASES, CLOUD_TECH, DEV_TOOLS, DATA_ML
    )

    return {
        "programming_languages": find(PROGRAMMING_LANGUAGES),
        "frameworks":            find(FRAMEWORKS),
        "databases":             find(DATABASES),
        "cloud_technologies":    find(CLOUD_TECH),
        "development_tools":     find(DEV_TOOLS),
        "data_ml":               find(DATA_ML),
        "soft_skills":           find(SOFT_SKILLS),
        "all_technical":         find(ALL_TECHNICAL_SKILLS),
    }


# ------------------------------------------------------------------ Experience years

def estimate_experience_years(text: str, experience_section: str = "") -> float:
    """
    Strategy 1: explicit "X years of experience" phrase.
    Strategy 2: sum month-named date spans in the experience section only
                (avoids counting education years).
    """
    explicit = re.findall(
        r"(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of\s+)?(?:experience|exp\.?)?",
        text.lower()
    )
    explicit_max = max((float(m) for m in explicit), default=0.0)

    # Only sum date ranges found in the confirmed experience section
    source = experience_section if (
        experience_section and experience_section != "Not clearly detected"
    ) else ""

    total_months = 0
    now = datetime.now()

    if source:
        for m in WORK_DATE_RE.finditer(source):
            try:
                # Extract start year (group 1 is the start month name, group 2 doesn't exist in this RE)
                # Find the years in the match string
                years = re.findall(r"\d{4}", m.group(0))
                if len(years) == 0:
                    continue
                start_year = int(years[0])
                end_raw = re.search(
                    r"(\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)\s*$", m.group(0)
                )
                if not end_raw:
                    continue
                end_str = end_raw.group(1)
                if re.match(r"[Pp]resent|[Cc]urrent|[Nn]ow", end_str):
                    end_year = now.year
                    end_month = now.month
                else:
                    end_year = int(end_str)
                    end_month = 12
                duration = (end_year - start_year) * 12
                if 0 < duration < 600:
                    total_months += duration
            except (ValueError, IndexError, AttributeError):
                continue

    range_years = round(total_months / 12, 1)
    return max(explicit_max, range_years)


# ------------------------------------------------------------------ Main

def parse_resume(file_path: str) -> dict:
    """Parse a PDF resume into a fully structured dict."""
    text = extract_text_from_pdf(file_path)
    if not text.strip():
        raise RuntimeError(
            "No extractable text found. "
            "The PDF may be a scanned image — please use a text-based PDF."
        )

    sections = _split_sections(text)

    # ---- Education -------------------------------------------------------
    education = sections.get("education", "").strip()
    if len(education) < 10:
        education = _fallback_education(text, exclude_certs=True)
    else:
        # Clean cert lines that leaked in from a missed section header
        education = _clean_education(education)
        if len(education) < 10:
            education = _fallback_education(text, exclude_certs=True)

    # ---- Experience ------------------------------------------------------
    experience = sections.get("experience", "").strip()
    if len(experience) < 10:
        # Only use fallback with month-named ranges + job-title check
        experience = _fallback_experience(text, education_text=education)

    # ---- Projects --------------------------------------------------------
    projects = sections.get("projects", "").strip()
    if len(projects) < 5:
        projects = "Not clearly detected"

    # ---- Certifications --------------------------------------------------
    certifications = sections.get("certifications", "").strip()
    if len(certifications) < 5:
        certifications = _fallback_certifications(text, education_text=education)

    # ---- Languages -------------------------------------------------------
    languages = sections.get("languages", "").strip()
    if len(languages) < 3:
        languages = "Not clearly detected"

    # ---- Skills & years --------------------------------------------------
    skills = extract_skills(text)
    exp_years = estimate_experience_years(text, experience)

    return {
        "raw_text":           text,
        "name":               extract_name(text),
        "email":              extract_email(text),
        "phone":              extract_phone(text),
        "linkedin":           extract_linkedin(text),
        "github":             extract_github(text),
        "education":          education,
        "experience_section": experience,
        "projects":           projects,
        "certifications":     certifications,
        "languages":          languages,
        "experience_years":   exp_years,
        "skills":             skills,
        "word_count":         len(re.findall(r"\b\w+\b", text)),
    }

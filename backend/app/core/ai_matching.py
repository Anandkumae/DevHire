import io
import re
from typing import Dict, List, Optional, Tuple, Any
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all readable text from a PDF byte stream."""
    if not pdf_bytes:
        return ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text).strip()
    except Exception:
        return ""


def normalize_text(text: str) -> str:
    """Lowercase and clean excessive whitespace."""
    if not text:
        return ""
    # Collapse multiple whitespaces/newlines into single space
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned.strip()


def build_skill_pattern(skill: str) -> re.Pattern:
    """Build a case-insensitive regex pattern that safely matches skills with symbols (e.g. C++, .NET, Node.js)."""
    escaped = re.escape(skill.strip())
    # If the skill starts and ends with alphanumeric characters, use standard word boundaries
    if re.match(r"^\w", skill) and re.match(r"\w$", skill):
        pattern_str = rf"\b{escaped}\b"
    elif re.match(r"^\w", skill):
        pattern_str = rf"\b{escaped}(?!\w)"
    elif re.match(r"\w$", skill):
        pattern_str = rf"(?<!\w){escaped}\b"
    else:
        pattern_str = rf"(?<!\w){escaped}(?!\w)"
    return re.compile(pattern_str, re.IGNORECASE)


def match_skills(text: str, target_skills: List[str]) -> Tuple[List[str], List[str], float]:
    """
    Identify matching and missing skills from target_skills within text.
    Returns: (matching_skills, missing_skills, skills_score)
    """
    if not target_skills:
        return [], [], 100.0

    matching = []
    missing = []

    for skill in target_skills:
        clean_skill = skill.strip()
        if not clean_skill:
            continue
        pattern = build_skill_pattern(clean_skill)
        if pattern.search(text):
            matching.append(clean_skill)
        else:
            missing.append(clean_skill)

    total_target = len(matching) + len(missing)
    if total_target == 0:
        score = 100.0
    else:
        score = round((len(matching) / total_target) * 100.0, 1)

    return matching, missing, score


def compute_semantic_similarity(
    resume_text: str,
    job_title: str,
    job_description: str,
    job_skills: Optional[List[str]] = None
) -> float:
    """
    Compute TF-IDF cosine similarity between resume text and job profile.
    Returns a calibrated similarity score from 0.0 to 100.0.
    """
    norm_resume = normalize_text(resume_text)
    skills_part = " ".join(job_skills) if job_skills else ""
    norm_job = normalize_text(f"{job_title} {job_description} {skills_part}")

    # Guard: if either document has too few words, return a conservative neutral score
    if len(norm_resume.split()) < 5 or len(norm_job.split()) < 5:
        return 50.0

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform([norm_resume, norm_job])
        raw_sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        # Calibrate: raw cosine similarity for natural texts typically peaks around 0.35 - 0.70
        calibrated = min(100.0, max(0.0, round(raw_sim * 150.0, 1)))
        return calibrated
    except Exception:
        return 50.0


def evaluate_experience_level(resume_text: str, required_level: str) -> Tuple[float, List[str]]:
    """
    Heuristic rule matching for experience level.
    Returns: (experience_score, remarks)
    """
    text_lower = resume_text.lower()
    req_lower = (required_level or "mid_level").lower().replace("-", "_").replace(" ", "_")
    remarks = []

    # Detect years of experience mentioned in resume
    years_matches = [int(y) for y in re.findall(r"\b(\d{1,2})\+?\s*(?:years?|yrs?)\b", text_lower)]
    max_years = max(years_matches) if years_matches else None

    # Detect seniority signals
    has_executive = bool(re.search(r"\b(cto|vp|director|head of engineering|chief)\b", text_lower))
    has_lead = bool(re.search(r"\b(lead|principal|staff|architect)\b", text_lower)) or (max_years is not None and max_years >= 7)
    has_senior = bool(re.search(r"\b(senior|sr\.?|5\+? years)\b", text_lower)) or (max_years is not None and max_years >= 5)
    has_mid = bool(re.search(r"\b(mid|intermediate|2\+? years|3\+? years)\b", text_lower)) or (max_years is not None and max_years >= 2)
    has_entry = bool(re.search(r"\b(junior|jr\.?|entry|graduate|fresher|intern)\b", text_lower))

    if req_lower in ["executive"]:
        if has_executive:
            score = 100.0
            remarks.append("Demonstrates executive-level engineering leadership background.")
        elif has_lead:
            score = 80.0
            remarks.append("Possesses staff/lead experience with strong potential for executive scope.")
        else:
            score = 50.0
            remarks.append("Executive role requested; profile indicates less senior leadership scope.")

    elif req_lower in ["lead"]:
        if has_lead or has_executive:
            score = 100.0
            remarks.append("Demonstrates technical leadership, architecture, or lead developer background.")
        elif has_senior:
            score = 85.0
            remarks.append("Strong senior experience suitable for step-up to technical lead.")
        else:
            score = 55.0
            remarks.append("Lead role requested; candidate demonstrates mid/early-career tenure.")

    elif req_lower in ["senior"]:
        if has_senior or has_lead or has_executive:
            score = 100.0
            remarks.append("Exceeds or fully satisfies senior-level engineering experience requirements.")
        elif has_mid:
            score = 75.0
            remarks.append("Mid-level engineer showing growth towards senior position.")
        else:
            score = 50.0
            remarks.append("Senior experience requested; candidate demonstrates early-career signals.")

    elif req_lower in ["mid_level", "mid"]:
        if has_mid or has_senior or has_lead:
            score = 100.0
            remarks.append("Fully satisfies mid-level experience expectations.")
        else:
            score = 70.0
            remarks.append("Entry-level/fresher profile evaluated against mid-level criteria.")

    elif req_lower in ["entry_level", "intern"]:
        score = 100.0
        remarks.append("Candidate background aligns well with entry-level/intern position.")

    else:
        score = 80.0
        remarks.append(f"Standard evaluation applied for experience level '{required_level}'.")

    if max_years is not None:
        remarks.append(f"Detected up to {max_years} years of relevant professional experience.")

    return score, remarks


def analyze_resume_for_job(
    resume_text: str,
    job_title: str,
    job_description: str,
    job_skills: List[str],
    experience_level: str
) -> Dict[str, Any]:
    """
    Perform comprehensive AI resume-job match analysis:
    - Skill matching (50% weight)
    - Semantic TF-IDF similarity (35% weight)
    - Experience level heuristic (15% weight)
    Returns complete breakdown with explainable insights.
    """
    matching_skills, missing_skills, skills_score = match_skills(resume_text, job_skills)
    semantic_score = compute_semantic_similarity(resume_text, job_title, job_description, job_skills)
    experience_score, exp_remarks = evaluate_experience_level(resume_text, experience_level)

    # Weighted overall score (0 - 100)
    overall_score = round(
        (0.50 * skills_score) + (0.35 * semantic_score) + (0.15 * experience_score),
        1
    )
    overall_score = max(0.0, min(100.0, overall_score))

    # Construct explainable strengths and gap analysis
    strengths: List[str] = []
    gap_analysis: List[str] = []

    if matching_skills:
        strengths.append(f"Matched {len(matching_skills)} of {len(job_skills)} required skills: {', '.join(matching_skills)}.")
    if semantic_score >= 70.0:
        strengths.append("High semantic relevance between candidate profile and job requirements.")
    elif semantic_score >= 50.0:
        strengths.append("Moderate contextual alignment with job description domain.")
    strengths.extend(exp_remarks)

    if missing_skills:
        gap_analysis.append(f"Missing {len(missing_skills)} required skill(s): {', '.join(missing_skills)}.")
    if semantic_score < 45.0:
        gap_analysis.append("Low overall terminology overlap with job description.")
    if experience_score < 70.0:
        gap_analysis.append(f"Candidate signals may not fully meet the '{experience_level}' requirement.")

    # Rating summary
    if overall_score >= 80.0:
        rating = "Strong Match"
        rec = "Candidate demonstrates exceptional alignment with technical stack and experience expectations. Highly recommended for interview."
    elif overall_score >= 65.0:
        rating = "Good Match"
        rec = "Candidate meets the core technical requirements with minor skill or experience gaps. Recommended for recruiter review."
    elif overall_score >= 50.0:
        rating = "Moderate Match"
        rec = "Candidate has partial skill overlap. Technical assessment recommended before proceeding."
    else:
        rating = "Weak Match"
        rec = "Candidate has significant gaps against key required skills and experience level."

    summary = f"{rating} ({overall_score}%) — {rec}"

    return {
        "overall_score": overall_score,
        "skills_score": skills_score,
        "semantic_score": semantic_score,
        "experience_score": experience_score,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "gap_analysis": gap_analysis,
        "summary": summary
    }


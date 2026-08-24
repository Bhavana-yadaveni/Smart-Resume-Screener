import re
from pathlib import Path

from pypdf import PdfReader

SKILL_VOCABULARY = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue", "node.js",
    "fastapi", "django", "flask", "spring", "sql", "postgresql", "mysql", "mongodb",
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "rest", "graphql", "linux",
    "machine learning", "deep learning", "data analysis", "pandas", "numpy", "spark",
    "tableau", "power bi", "figma", "agile", "scrum", "ci/cd", "terraform",
]


def extract_pdf_text(path: Path) -> str:
    try:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    except Exception as error:
        raise ValueError("This PDF could not be read. Upload a text-based PDF or paste the resume text.") from error
    if not text.strip():
        raise ValueError("No selectable text was found in the PDF. Paste the resume text instead.")
    return text


def extract_candidate(resume_text: str) -> dict:
    clean_text = re.sub(r"\r\n?", "\n", resume_text).strip()
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", clean_text, re.I)
    phone_match = re.search(r"(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]?)?\d{3,5}[ .-]\d{4}", clean_text)
    name = lines[0] if lines else "Unnamed candidate"
    if len(name) > 80 or "@" in name or any(char.isdigit() for char in name):
        name = "Unnamed candidate"
    lower = clean_text.lower()
    skills = [skill for skill in SKILL_VOCABULARY if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", lower)]
    year_matches = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", lower)]
    experience_years = max(year_matches, default=0)
    education_lines = [line for line in lines if re.search(r"\b(bachelor|master|b\.tech|m\.tech|bsc|msc|mba|phd|degree|university|college)\b", line, re.I)]
    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "skills": skills,
        "experience_years": experience_years,
        "education": education_lines[:5],
        "resume_text": clean_text,
    }

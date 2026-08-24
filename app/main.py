import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.database import dump_list, get_connection, init_db, load_list
from app.extraction import extract_candidate, extract_pdf_text
from app.matching import assess

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app = FastAPI(title="Smart Resume Screener")
app.mount("/static", StaticFiles(directory="static"), name="static")


class ResumeTextInput(BaseModel):
    resume_text: str = Field(min_length=20)


class JobInput(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=30)


@app.on_event("startup")
def startup() -> None:
    init_db()


def candidate_response(row):
    result = dict(row)
    result["skills"] = load_list(result["skills"])
    result["education"] = load_list(result["education"])
    result.pop("resume_text", None)
    return result


def create_candidate(resume_text: str):
    data = extract_candidate(resume_text)
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO candidates (name,email,phone,skills,experience_years,education,resume_text) VALUES (?,?,?,?,?,?,?)",
            (data["name"], data["email"], data["phone"], dump_list(data["skills"]), data["experience_years"], dump_list(data["education"]), data["resume_text"]),
        )
        row = connection.execute("SELECT * FROM candidates WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return candidate_response(row)


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse("static/index.html")


@app.post("/api/candidates/text")
def add_text_candidate(payload: ResumeTextInput):
    return create_candidate(payload.resume_text)


@app.post("/api/candidates/upload")
async def upload_candidate(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(400, "Upload a PDF or .txt file.")
    destination = UPLOAD_DIR / f"{Path(file.filename or 'resume').stem}-{file.filename}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        text = extract_pdf_text(destination) if suffix == ".pdf" else destination.read_text(encoding="utf-8", errors="ignore")
        return create_candidate(text)
    finally:
        destination.unlink(missing_ok=True)


@app.get("/api/candidates")
def list_candidates():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()
    return [candidate_response(row) for row in rows]


@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int):
    with get_connection() as connection:
        if connection.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,)).rowcount == 0:
            raise HTTPException(404, "Candidate not found")
    return {"ok": True}


@app.post("/api/jobs")
def create_job(payload: JobInput):
    with get_connection() as connection:
        cursor = connection.execute("INSERT INTO jobs (title, description) VALUES (?, ?)", (payload.title, payload.description))
        job_id = cursor.lastrowid
    return {"id": job_id, **payload.model_dump()}


@app.post("/api/jobs/{job_id}/screen")
def screen_candidates(job_id: int):
    with get_connection() as connection:
        job = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(404, "Job not found")
        candidates = connection.execute("SELECT * FROM candidates").fetchall()
        for candidate in candidates:
            candidate_data = dict(candidate)
            candidate_data["skills"] = load_list(candidate_data["skills"])
            result = assess(candidate_data, dict(job))
            connection.execute(
                """INSERT INTO assessments (job_id,candidate_id,score,matched_skills,missing_skills,strengths,concerns,justification,scoring_method)
                VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id,candidate_id) DO UPDATE SET score=excluded.score, matched_skills=excluded.matched_skills, missing_skills=excluded.missing_skills, strengths=excluded.strengths, concerns=excluded.concerns, justification=excluded.justification, scoring_method=excluded.scoring_method, created_at=CURRENT_TIMESTAMP""",
                (job_id, candidate["id"], result["score"], dump_list(result["matched_skills"]), dump_list(result["missing_skills"]), dump_list(result["strengths"]), dump_list(result["concerns"]), result["justification"], result["scoring_method"]),
            )
    return {"job_id": job_id, "screened_candidates": len(candidates)}


@app.get("/api/jobs/{job_id}/assessments")
def list_assessments(job_id: int):
    with get_connection() as connection:
        rows = connection.execute(
            """SELECT a.*, c.name, c.email, c.phone, c.experience_years, c.skills, c.education
            FROM assessments a JOIN candidates c ON c.id = a.candidate_id WHERE a.job_id = ?
            ORDER BY a.score DESC, a.created_at DESC""", (job_id,)
        ).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        for field in ("matched_skills", "missing_skills", "strengths", "concerns", "skills", "education"):
            item[field] = load_list(item[field])
        results.append(item)
    return results

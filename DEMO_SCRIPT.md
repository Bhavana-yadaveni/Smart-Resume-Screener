# 2–3 Minute Demo Script

1. **0:00–0:20 — Introduce the platform**
   - Open `http://127.0.0.1:8000`.
   - Say: “This is a Smart Resume Screener that parses resumes, extracts candidate data, compares candidates with a job description, and ranks the shortlist.”

2. **0:20–0:55 — Add resumes**
   - Upload a PDF/text resume or paste a sample resume.
   - Point out the extracted candidate name, skills, and years of experience in the candidate list.

3. **0:55–1:25 — Create a job**
   - Enter a job title and requirements such as Python, FastAPI, SQL, Docker, AWS, and 3+ years of experience.
   - Click **Create job and screen candidates**.

4. **1:25–2:10 — Explain results**
   - Show that candidates are ranked by score.
   - Explain the matched skills, highlighted gaps, justification, and scoring method.
   - State that OpenAI semantic scoring is used when an API key is configured; the local fallback makes the platform usable and auditable without one.

5. **2:10–2:35 — Show technical quality**
   - Open `/docs` to show the backend API.
   - Briefly show the SQLite-backed code structure and README architecture diagram.

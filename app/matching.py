import json
import os
import re

from dotenv import load_dotenv

from app.extraction import SKILL_VOCABULARY

load_dotenv()


def _job_skills(description: str) -> list[str]:
    lowered = description.lower()
    return [skill for skill in SKILL_VOCABULARY if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", lowered)]


def local_assessment(candidate: dict, job: dict) -> dict:
    required = _job_skills(job["description"])
    candidate_skills = {skill.lower() for skill in candidate["skills"]}
    matched = [skill for skill in required if skill in candidate_skills]
    missing = [skill for skill in required if skill not in candidate_skills]
    coverage = len(matched) / len(required) if required else 0.5
    experience_bonus = min(float(candidate["experience_years"]) / 8, 1) * 0.15
    score = max(1, min(10, round(1 + coverage * 8 + experience_bonus)))
    strengths = [f"Matches {', '.join(matched[:4])}" if matched else "Resume was stored and parsed successfully"]
    if candidate["experience_years"]:
        strengths.append(f"Reports approximately {candidate['experience_years']:g} years of experience")
    concerns = [f"Evidence for {', '.join(missing[:4])} was not found" ] if missing else ["No obvious skill gaps from the detected requirements"]
    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "strengths": strengths,
        "concerns": concerns,
        "justification": f"Local scoring found {len(matched)} of {len(required)} detected job skills. Review the original resume before making a hiring decision.",
        "scoring_method": "local fallback",
    }


def assess(candidate: dict, job: dict) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return local_assessment(candidate, job)
    try:
        from openai import OpenAI
        prompt = f"""You are an unbiased recruitment assistant. Compare the candidate resume with the job description.
Return JSON only, with keys score (integer 1-10), matched_skills (array), missing_skills (array), strengths (array), concerns (array), and justification (string).
Score evidence in the resume only. Do not infer or discuss age, gender, ethnicity, disability, religion, nationality, or other protected traits.

JOB TITLE: {job['title']}
JOB DESCRIPTION:\n{job['description']}

CANDIDATE RESUME:\n{candidate['resume_text'][:12000]}"""
        result = OpenAI(api_key=api_key).chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        parsed = json.loads(result.choices[0].message.content or "{}")
        parsed["score"] = max(1, min(10, int(parsed.get("score", 1))))
        for key in ("matched_skills", "missing_skills", "strengths", "concerns"):
            parsed[key] = [str(item) for item in parsed.get(key, [])]
        parsed["justification"] = str(parsed.get("justification", "No justification returned."))
        parsed["scoring_method"] = "OpenAI semantic assessment"
        return parsed
    except Exception:
        return local_assessment(candidate, job)

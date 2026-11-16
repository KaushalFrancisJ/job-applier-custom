"""
Bridge to Google Antigravity CLI (`agy`) for complex reasoning,
bespoke screening answers, and nuanced fit evaluations without third-party API keys.
"""
import json
import logging
import subprocess
from typing import Optional

from src.utils import sanitize_unicode

logger = logging.getLogger("agy_bridge")


class AgyBridge:
    def __init__(self, effort: str = "low"):
        self.effort = effort

    def ask(self, prompt: str, timeout_seconds: int = 45) -> Optional[str]:
        """
        Runs non-interactive `agy -p` prompt and captures text output.
        """
        try:
            cmd = ["agy", "-p", prompt, "--effort", self.effort]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_seconds,
            )
            if res.returncode == 0:
                return sanitize_unicode(res.stdout.strip())
            else:
                logger.warning(f"[AgyBridge] agy returned code {res.returncode}: {res.stderr[:200]}")
                return None
        except Exception as e:
            logger.warning(f"[AgyBridge] Failed to invoke agy: {e}")
            return None

    def answer_screening_question(self, question: str, jd: str, candidate_context: str) -> Optional[str]:
        """
        Generates a concise, high-caliber answer for custom recruiter application questions.
        """
        prompt = (
            f"You are Kaushal Francis J, a Senior Associate with 1.5+ years experience specializing in "
            f"Applied Generative AI (RAG with PgVector/Bedrock Titan, 40% accuracy gain, Groq LLM evaluation) "
            f"and Agentic Systems (NVIDIA NIM Desktop Coding Agent with Model Context Protocol - MCP).\n\n"
            f"Job Description Context: {jd[:400]}\n"
            f"Candidate Highlights: {candidate_context}\n\n"
            f"Screening Question: {question}\n\n"
            f"Provide a direct, authentic, professional answer (2-4 sentences max). Be specific with technologies."
        )
        return self.ask(prompt)

    def evaluate_role_fit(
        self,
        title: str,
        description: str,
        candidate_summary: str,
        company: str = "",
        location: str = "",
        timeout_seconds: int = 35,
    ) -> Optional[dict]:
        """
        Uses agy to perform nuanced role evaluation matching the full JD against candidate profile.
        Passes up to 3500 characters of the JD to ensure complete requirements, stack, and YOE context.
        """
        jd_text = sanitize_unicode(description.strip())[:3500]
        prompt = (
            f"You are an expert technical hiring evaluator. Match this job description against the candidate's verified profile.\n\n"
            f"--- CANDIDATE PROFILE ---\n"
            f"{candidate_summary}\n\n"
            f"--- JOB DETAILS ---\n"
            f"Company: {company or 'Undisclosed'}\n"
            f"Title: {title}\n"
            f"Location: {location or 'Not specified'}\n"
            f"Job Description:\n{jd_text}\n\n"
            f"--- EVALUATION INSTRUCTIONS ---\n"
            f"Evaluate if this candidate is genuinely a strong fit for this role:\n"
            f"1. Experience Match: Candidate has 19 months (~1.5 yrs) experience and target is 0-3 YOE. "
            f"   If JD strictly requires 4+ years of experience, REJECT (is_match: false).\n"
            f"2. Tech Stack Match: Candidate specializes in Python, TypeScript, Node.js, Next.js, React, RAG, PgVector, Bedrock, and MCP. "
            f"   If JD mandates foreign backend languages (e.g. Go, Java, C++, C#, Rust, Ruby, PHP) with NO Python/TS/Node alternative, REJECT (is_match: false).\n"
            f"3. Role Relevance: Strong alignment with Applied AI/GenAI, Agentic Systems, Full Stack, or Backend engineering. Reject pure research/PhD math.\n\n"
            f"Reply strictly with a valid JSON object only (no markdown fences, no extra text):\n"
            f'{{"is_match": true, "score": 85, "reason": "concise 1-2 sentence explanation of match or why rejected"}}'
        )
        resp = self.ask(prompt, timeout_seconds=timeout_seconds)
        if not resp:
            return None
        try:
            clean = resp.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            data = json.loads(clean)
            if "is_match" in data and "score" in data:
                return {
                    "is_match": bool(data["is_match"]),
                    "score": float(data["score"]),
                    "reason": str(data.get("reason", "")).strip(),
                }
            return None
        except Exception as e:
            logger.warning(f"[AgyBridge] Failed to parse evaluate_role_fit JSON: {e}")
            return None

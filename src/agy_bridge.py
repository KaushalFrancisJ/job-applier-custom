"""
Bridge to Google Antigravity CLI (`agy`) for complex reasoning,
bespoke screening answers, and nuanced fit evaluations without third-party API keys.
"""
import json
import logging
import subprocess
from typing import Optional

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
                return res.stdout.strip()
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

    def evaluate_role_fit(self, title: str, description: str, candidate_summary: str) -> Optional[dict]:
        """
        Uses agy to perform nuanced role evaluation when regex matching is borderline.
        """
        prompt = (
            f"You are an expert technical recruiter evaluating candidate fit.\n"
            f"Role: {title}\n"
            f"Description: {description[:400]}\n"
            f"Candidate Profile: {candidate_summary}\n\n"
            f"Evaluate if this candidate (Applied GenAI, RAG, MCP, Python, TypeScript, Fullstack) "
            f"should apply. Reply strictly with valid JSON only in format: "
            f'{{"is_match": true, "score": 85, "reason": "short explanation"}}'
        )
        resp = self.ask(prompt)
        if not resp:
            return None
        try:
            clean = resp.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            return json.loads(clean)
        except Exception:
            return None

"""
Job Matching & Tailored Pitch Generation Engine.
Evaluates JDs against candidate background, filters out pure theoretical ML roles,
and generates customized application pitches highlighting relevant GitHub projects.
"""
from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple

from src.agy_bridge import AgyBridge
from src.candidate_profile import CandidateProfile


@dataclass
class MatchResult:
    is_match: bool
    score: float  # 0 to 100
    reason: str
    action_required: bool = False
    action_notes: str = ""
    pitch_note: str = ""


class JobMatcher:
    def __init__(self, profile: CandidateProfile, config: dict):
        self.profile = profile
        self.config = config
        self.prefs = config.get("preferences", {})
        self.exclude_keywords = [
            k.lower() for k in self.prefs.get("exclude_keywords", [])
        ]
        self.target_roles = [
            r.lower() for r in self.prefs.get("target_roles", [])
        ]
        self.primary_locations = [
            loc.lower() for loc in self.prefs.get("locations", {}).get("primary", [])
        ]
        self.allow_any_india = self.prefs.get("locations", {}).get("allow_any_india", True)
        self.allow_remote_india = self.prefs.get("locations", {}).get("allow_remote_india", True)
        self.strict_india_only = self.prefs.get("locations", {}).get("strict_india_only", True)
        self.disallowed_countries = [
            c.lower() for c in self.prefs.get("locations", {}).get("disallowed_countries", [])
        ]
        self.exclude_roles = [
            r.lower() for r in self.prefs.get("exclude_roles", [])
        ]
        self.min_salary_lpa = float(self.prefs.get("expected_ctc_lpa", 10.0))
        self.agy = AgyBridge(effort="low")

    def evaluate_job(
        self,
        title: str,
        description: str,
        location: str,
        salary_str: str = "",
        external_url: Optional[str] = None,
        has_custom_questions: bool = False,
        company: str = "",
        platform: str = "",
    ) -> MatchResult:
        """
        Runs comprehensive checks:
        1. Pure ML exclusion filter
        2. Role and keyword relevance
        3. Location compatibility
        4. Salary threshold (>= 10 LPA)
        5. Action required flags (external ATS, custom assignments)
        6. Pitch note synthesis
        """
        title_lower = title.lower()
        desc_lower = description.lower()
        loc_lower = location.lower()
        combined_text = f"{title_lower} {desc_lower}"

        # 1. Pure ML Check (User explicitly wants to avoid pure ML / research math roles)
        for bad_kw in self.exclude_keywords:
            if bad_kw in combined_text:
                # Check if it's explicitly in the title or heavily emphasized
                if bad_kw in title_lower or desc_lower.count(bad_kw) >= 2:
                    return MatchResult(
                        is_match=False,
                        score=15.0,
                        reason=f"Excluded: Pure ML/Research role keyword found ('{bad_kw}').",
                    )

        # Also check for PhD requirement
        if "phd required" in desc_lower or "ph.d in computer science" in desc_lower:
            return MatchResult(
                is_match=False,
                score=10.0,
                reason="Excluded: Requires PhD / theoretical research background.",
            )

        # 2. Location Check (Strict Indian Role Alignment)
        if self.strict_india_only:
            has_disallowed = any(dc in loc_lower for dc in self.disallowed_countries)
            if has_disallowed and "india" not in loc_lower:
                return MatchResult(
                    is_match=False,
                    score=25.0,
                    reason=f"Location excluded: '{location}' is an overseas/non-Indian role.",
                )

        loc_matched = False
        india_regions = [
            "india", "chennai", "bangalore", "bengaluru", "hyderabad", "pune",
            "gurgaon", "gurugram", "noida", "mumbai", "delhi", "karnataka",
            "tamil nadu", "telangana", "maharashtra", "jaipur", "indore", "navi mumbai"
        ]
        has_india_mention = any(ind in loc_lower for ind in india_regions)

        if has_india_mention:
            loc_matched = True
        elif self.allow_remote_india and any(rem in loc_lower for rem in ["remote", "work from home", "wfh"]) and not has_disallowed:
            loc_matched = True
        elif not self.strict_india_only and any(rem in loc_lower for rem in ["remote", "wfh", "work from home"]):
            loc_matched = True

        if not loc_matched:
            return MatchResult(
                is_match=False,
                score=30.0,
                reason=f"Location mismatch: '{location}' is not an India-based or India-eligible role.",
            )

        # 3. Salary Check
        salary_ok, salary_msg = self._check_salary(salary_str)
        if not salary_ok:
            return MatchResult(
                is_match=False,
                score=35.0,
                reason=f"Salary below target threshold: {salary_msg}",
            )

        # 4. Role & JD Relevance Evaluation (Holistic JD Assessment)
        # Check hard negative keywords that indicate purely non-software or manual infrastructure work
        hard_exclusions = [
            "hardware engineer", "embedded engineer", "firmware developer",
            "soc analyst", "manual qa", "manual tester", "compliance auditor",
            "it support", "sales engineer", "telecom line"
        ]
        for hard_ex in hard_exclusions:
            if hard_ex in combined_text:
                return MatchResult(
                    is_match=False,
                    score=15.0,
                    reason=f"Excluded non-software/hardware role: matched '{hard_ex}'.",
                )

        # Extract core tech stack alignment from JD description
        genai_hits = [k for k in ["rag", "llm", "bedrock", "pgvector", "faiss", "agent", "groq", "langchain", "prompt", "livekit", "stt", "tts", "conversational"] if k in desc_lower]
        fullstack_hits = [k for k in ["python", "node", "typescript", "fastapi", "react", "next.js", "docker", "aws", "redis", "django", "postgres", "sql", "api", "microservice", "asyncio", "streaming", "websocket"] if k in desc_lower]

        has_target_title = any(tr in title_lower for tr in self.target_roles) or any(p in title_lower for p in ["ai", "fullstack", "full stack", "full-stack", "backend", "python", "software engineer", "developer", "sde"])

        is_explicit_ai = any(kw in title_lower for kw in [
            "ai engineer", "generative ai", "genai", "ai full stack", "ai fullstack",
            "ai platform", "founding ai", "llm engineer", "ai developer", "applied ai"
        ])
        is_core_eng = any(kw in title_lower for kw in [
            "founding engineer", "full stack", "fullstack", "backend engineer", "software engineer", "sde"
        ])

        # Scoring based on JD substance
        score = 45.0
        if is_explicit_ai:
            score += 30.0
        elif is_core_eng or has_target_title:
            score += 20.0
        elif any(ai_term in desc_lower for ai_term in ["agent", "llm", "conversational", "generative"]):
            score += 15.0  # Applied AI startup with cross-functional title

        tech_score = len(genai_hits) * 3.5 + len(fullstack_hits) * 2.0
        score += min(tech_score, 30.0)

        # Minimum relevance threshold:
        # If title is explicitly an AI role or Core Engineering role, a score >= 65 is an automatic match even if the card snippet was short
        if score < 65.0 or (not is_explicit_ai and not is_core_eng and len(genai_hits) == 0 and len(fullstack_hits) < 2):
            return MatchResult(
                is_match=False,
                score=score,
                reason=f"Low relevance score ({score:.1f}/100). JD does not sufficiently align with Applied AI/Fullstack/Backend.",
            )

        # 5. Check if manual action is required
        action_required = False
        action_notes = []

        if external_url and not any(plat in external_url for plat in ["wellfound.com", "linkedin.com", "naukri.com"]):
            action_required = True
            action_notes.append(f"External ATS application URL: {external_url}")

        if has_custom_questions or any(q in desc_lower for q in ["take-home assignment", "coding challenge link", "submit a loom video", "github repo with proof of work"]):
            action_required = True
            action_notes.append("JD requests specific assignment/video or complex screening responses.")

        # 6. Generate Tailored Pitch Note
        pitch = self._generate_pitch(title, desc_lower, genai_hits, fullstack_hits, company=company, platform=platform)

        return MatchResult(
            is_match=True,
            score=min(score, 98.0),
            reason=f"High match ({score:.1f}/100). Aligned with {', '.join((genai_hits + fullstack_hits)[:4])}.",
            action_required=action_required,
            action_notes="; ".join(action_notes),
            pitch_note=pitch,
        )

    def _check_salary(self, salary_str: str) -> Tuple[bool, str]:
        """
        Parses salary string for INR LPA or USD ranges.
        If salary is undisclosed or competitive, returns (True, 'Undisclosed/Competitive').
        If maximum salary is strictly below expected_ctc_lpa, returns (False, reason).
        """
        if not salary_str or salary_str.strip() == "":
            return True, "Undisclosed / Market standard"

        s_lower = salary_str.lower()
        if "competitive" in s_lower or "doe" in s_lower or "not disclosed" in s_lower:
            return True, "Competitive / Undisclosed"

        # Search for LPA numbers like '6 - 10 LPA' or '₹8L - ₹11L'
        lpa_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lac|l\b)", s_lower)
        if lpa_matches:
            nums = [float(n) for n in lpa_matches]
            max_num = max(nums)
            if max_num < self.min_salary_lpa:
                return False, f"Maximum offered is {max_num} LPA, below target {self.min_salary_lpa} LPA."
            return True, f"Matches salary expectations ({salary_str})"

        # Check for USD rates (e.g. $40k - $80k or $50/hr for remote)
        usd_matches = re.findall(r"\$(\d+)(?:k)?", s_lower)
        if usd_matches:
            # Any global USD role over $25k exceeds 10 LPA (approx $14k)
            nums = [float(n) for n in usd_matches]
            if max(nums) < 20:  # e.g. < $20k
                return False, f"USD salary {salary_str} below threshold"
            return True, f"USD salary meets threshold ({salary_str})"

        return True, "Salary format unparsed, assuming eligible"

    def _generate_pitch(
        self,
        title: str,
        desc: str,
        genai_hits: List[str],
        fullstack_hits: List[str],
        company: str = "",
        platform: str = "",
    ) -> str:
        """
        Hybrid Pitch Synthesis:
        1. Attempts bespoke synthesis via `agy` CLI connecting Kaushal's verified metrics & MCP/RAG
           repos to the company's specific mission.
        2. Falls back instantly to deterministic vectored templates if agy times out or is offline.
        """
        if company and self.agy:
            try:
                prompt = (
                    f"You are Kaushal Francis J applying to {company} for the role of {title}.\n"
                    f"Candidate Background: Senior Associate at Payday Suite, improved enterprise RAG accuracy by 40% "
                    f"with AWS Bedrock Titan + PgVector, built open-source NVIDIA NIM Desktop Coding Agent with Model Context Protocol (MCP) "
                    f"and async streaming (github.com/KaushalFrancisJ/Coding-agent-nvidia), and built production HabitFlow API (Redis/Docker).\n"
                    f"Job Description Context: {desc[:400]}\n\n"
                    f"Write a punchy, authentic 3-sentence application note to the hiring team. "
                    f"Connect your actual project experience directly to their specific product/mission, cite the +40% metric or MCP repo, "
                    f"and keep it under 65 words. No placeholders."
                )
                bespoke = self.agy.ask(prompt, timeout_seconds=15)
                if bespoke and len(bespoke) > 40 and not bespoke.startswith("Error"):
                    return bespoke
            except Exception as e:
                logger.warning(f"[Matcher] agy pitch synthesis fallback: {e}")

        # Deterministic Vectored Fallback
        if len(genai_hits) >= len(fullstack_hits) and ("rag" in desc or "vector" in desc or "bedrock" in desc):
            return (
                f"Hi team, I saw your opening for {title} and wanted to reach out. "
                f"In my current role as Senior Associate at Payday Suite, I improved RAG response accuracy by 40% "
                f"using AWS Bedrock Titan embeddings, PgVector, and built a custom LLM-as-a-judge evaluation harness via Groq. "
                f"I've also built an open-source Desktop Coding Agent using NVIDIA NIM and MCP (github.com/KaushalFrancisJ/Coding-agent-nvidia). "
                f"I'd love to bring this hands-on GenAI orchestration experience to your team!"
            )
        elif "agent" in desc or "python" in desc:
            return (
                f"Hi team, I'm reaching out regarding the {title} role. "
                f"I specialize in building production agentic systems and scalable backends. "
                f"Recently, I architected an asynchronous desktop coding assistant powered by NVIDIA NIM APIs and the "
                f"Model Context Protocol (MCP) with streaming JSON handling (github.com/KaushalFrancisJ/Coding-agent-nvidia). "
                f"Backed by fullstack engineering in Python/FastAPI, TypeScript, and AWS Lambda/SQS, I am confident I can contribute immediately."
            )
        else:
            return (
                f"Hi team, I'm excited about the {title} opportunity. "
                f"As a Senior Associate at 4i apps, I own fullstack feature delivery across Next.js, Node.js/FastAPI, "
                f"and event-driven AWS infrastructure, alongside production GenAI workflows with PgVector and AWS Bedrock. "
                f"Check out my production habit engine API with Redis caching and Docker at github.com/KaushalFrancisJ/Habit-Formation-Application. "
                f"Looking forward to speaking!"
            )

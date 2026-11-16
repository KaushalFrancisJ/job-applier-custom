"""
Job Matching & Tailored Pitch Generation Engine.
Evaluates JDs against candidate background, filters out pure theoretical ML roles,
and generates customized application pitches highlighting relevant GitHub projects.
"""
from dataclasses import dataclass
import logging
import re
from typing import Dict, List, Optional, Tuple

from src.agy_bridge import AgyBridge
from src.candidate_profile import CandidateProfile
from src.utils import sanitize_unicode

logger = logging.getLogger("matcher")


@dataclass
class MatchResult:
    is_match: bool
    score: float  # 0 to 100
    reason: str
    action_required: bool = False
    action_notes: str = ""
    pitch_note: str = ""
    extracted_external_url: Optional[str] = None


ATS_FORM_REGEX = re.compile(
    r"(https?://(?:forms\.gle|docs\.google\.com/forms|tally\.so/r/|typeform\.com|jobs\.lever\.co|"
    r"boards\.greenhouse\.io|job-boards\.greenhouse\.io|jobs\.ashbyhq\.com|notion\.site/[^\s]+|"
    r"airtable\.com/[^\s]+|applytojob\.com|bamboohr\.com|myworkdayjobs\.com)[^\s\)\"\'>]+)",
    re.IGNORECASE,
)


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
        self.candidate_summary = (
            self.profile.to_matcher_context()
            if hasattr(self.profile, "to_matcher_context")
            else ""
        )

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

        # 0. Incomplete JD Guardrail
        # If JD text is missing or just a synthetic 1-line fallback snippet (e.g. '{title} at {company} on LinkedIn')
        # we cannot reliably verify experience or tech requirements. Exclude to prevent blind approvals of 8+ YOE roles.
        is_synthetic_snippet = (
            len(description.strip()) < 50 or
            (description.strip().endswith("on linkedin.") and len(description.strip()) < 140 and not any(kw in desc_lower for kw in ["requirement", "skill", "experience", "year", "python", "react"]))
        )
        if is_synthetic_snippet:
            return MatchResult(
                is_match=False,
                score=30.0,
                reason="Excluded: Full job description could not be retrieved to verify experience and stack requirements.",
            )

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

        # 1b. Executive / Director / High-Tier Corporate Level Exclusions
        # NOTE: We do NOT blindly exclude 'Senior' titles — candidate has 19 months experience
        # and is a Senior Associate. Many teams hire 2-3 YOE engineers for Senior roles.
        # Filtering is strictly driven by the actual required YOE (upper limit: 3 years).
        high_tier_title_exclusions = [
            "director", "vp", "vice president", "chief", "head of",
            "principal", "staff engineer", "staff software", "staff developer",
            "senior ii", "senior 2", "senior iii", "senior 3", "senior manager"
        ]
        for ht_kw in high_tier_title_exclusions:
            pattern = rf"\b{re.escape(ht_kw)}\b"
            if re.search(pattern, title_lower):
                return MatchResult(
                    is_match=False,
                    score=20.0,
                    reason=f"Excluded high executive/tiered role: matched '{ht_kw}' in title ('{title}').",
                )

        # 1c. Tech Stack Title Exclusions (Candidate stack: Python, TypeScript, Node.js, Next.js, React, SQL, AWS)
        tech_title_exclusions = [
            "java", "spring boot", "springboot", "angular", "c++", ".net", "dotnet", "c#",
            "ruby", "rails", "php", "sap", "cobol", "salesforce", "scala", "spark",
            "golang", "rust", "kotlin", "swift", "elixir"
        ]
        for tt_kw in tech_title_exclusions:
            pattern = rf"\b{re.escape(tt_kw)}\b"
            if re.search(pattern, title_lower):
                return MatchResult(
                    is_match=False,
                    score=20.0,
                    reason=f"Excluded tech stack mismatch in title: matched '{tt_kw}' in '{title}'.",
                )
        # Dedicated word-boundary check for 'go' to prevent false substring matches
        if re.search(r"\bgo\s+(?:developer|engineer|backend|programmer)\b", title_lower) or re.search(r"\b(?:backend|software)\s+engineer\s+-\s+go\b", title_lower):
            return MatchResult(
                is_match=False,
                score=20.0,
                reason=f"Excluded tech stack mismatch in title: matched Go/Golang in '{title}'.",
            )

        # 1d. YOE Filter (Candidate has 19 months experience; upper limit is 2-3 years, with tolerance for 2-4 ranges)
        # Check title first for explicit high YOE (e.g. '5-7 yrs', '8+ yrs', '4+ years')
        title_yoe_ranges = re.findall(r"\b(\d+)\s*(?:to|-|–)\s*(\d+)\+?\s*(?:years?|yrs?)\b", title_lower)
        for lower_y, upper_y in title_yoe_ranges:
            if int(lower_y) >= 4:
                return MatchResult(
                    is_match=False,
                    score=20.0,
                    reason=f"Excluded high YOE in title: '{lower_y}-{upper_y} yrs' exceeds profile range (19 months, upper limit 2-3 YOE).",
                )
        title_single_yoe = re.findall(r"(?<![-–\dto]\s)(?<![-–\d])\b([4-9]|\d{2})\+?\s*(?:years?|yrs?)\b", title_lower)
        if title_single_yoe:
            min_t_exp = min(int(x) for x in title_single_yoe)
            if min_t_exp >= 4:
                return MatchResult(
                    is_match=False,
                    score=20.0,
                    reason=f"Excluded high YOE in title: specifies {min_t_exp}+ years of experience (target: 0-3 YOE).",
                )

        # Check description for ranges with lower bound >= 4 (e.g. '4-7 years', '6-10 years')
        desc_yoe_ranges = re.findall(r"\b(\d+)\s*(?:to|-|–)\s*(\d+)\+?\s*(?:years?|yrs?)\b", desc_lower)
        for lower_y, upper_y in desc_yoe_ranges:
            if int(lower_y) >= 4:
                return MatchResult(
                    is_match=False,
                    score=20.0,
                    reason=f"Excluded high YOE requirement: JD specifies {lower_y}-{upper_y} years of experience (target: 0-3 YOE).",
                )

        # Check description for single minimum numbers >= 4 (e.g. '4+ years', '5+ years', '8+ years of experience', 'minimum 5 years')
        single_yoe_matches = re.findall(r"(?<![-–\dto]\s)(?<![-–\d])\b([4-9]|\d{2})\+?\s*(?:years?|yrs?)\b", desc_lower)
        min_prefix_matches = re.findall(r"\b(?:minimum|min|at least|over)\s+([4-9]|\d{2})\+?\s*(?:years?|yrs?)\b", desc_lower)
        exp_colon_matches = re.findall(r"\bexperience\s*[:\-]\s*([4-9]|\d{2})\+?\s*(?:years?|yrs?)\b", desc_lower)
        all_yoe_single = single_yoe_matches + min_prefix_matches + exp_colon_matches
        if all_yoe_single:
            min_exp_found = min(int(x) for x in all_yoe_single)
            if min_exp_found >= 4:
                return MatchResult(
                    is_match=False,
                    score=20.0,
                    reason=f"Excluded high YOE requirement: JD specifies {min_exp_found}+ years of experience (target: 0-3 YOE).",
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
        genai_hits = [k for k in ["rag", "llm", "bedrock", "pgvector", "faiss", "agent", "groq", "langchain", "prompt", "livekit", "stt", "tts", "conversational", "genai", "generative ai"] if k in desc_lower]
        primary_lang_hits = [k for k in ["python", "node", "nodejs", "node.js", "typescript", "fastapi", "django", "react", "next.js", "nextjs"] if k in desc_lower]
        infra_hits = [k for k in ["docker", "aws", "redis", "postgres", "sql", "api", "microservice", "asyncio", "streaming", "websocket"] if k in desc_lower]
        all_tech_hits = list(set(primary_lang_hits + infra_hits))

        # 4b. Primary Language Gate: Filter out foreign backend languages when candidate's stack is absent
        foreign_lang_patterns = [
            ("Go/Golang", [
                r"\bgolang\b",
                r"\bgo\s+(?:developer|engineer|backend|microservices|programming|code)\b",
                r"\b(?:proficiency|proficient|experience|hands-on|expertise|strong|working)\s+(?:in|with)\s+go\b",
                r"\bbuilt\s+in\s+go\b",
                r"\bcore\s+go\b",
            ]),
            ("Java", [
                r"\bjava\b",
                r"\bspring\s*boot\b",
                r"\bj2ee\b",
                r"\bcore\s+java\b",
            ]),
            ("C++", [
                r"\bc\+\+\b",
                r"\bcpp\b",
            ]),
            ("C#/.NET", [
                r"\bc#\b",
                r"\b\.net\b",
                r"\bdotnet\b",
                r"\basp\.net\b",
            ]),
            ("Rust", [
                r"\brust\s+(?:developer|engineer|backend|programming)\b",
                r"\b(?:proficiency|proficient|experience)\s+(?:in|with)\s+rust\b",
            ]),
            ("PHP", [
                r"\bphp\b",
                r"\blaravel\b",
            ]),
            ("Ruby", [
                r"\bruby\s+on\s+rails\b",
                r"\bruby\b",
            ]),
            ("Scala", [
                r"\bscala\b",
            ]),
        ]

        # If JD mandates a foreign language and does NOT accept Python/TypeScript/Node.js:
        if not primary_lang_hits:
            for lang_name, patterns in foreign_lang_patterns:
                if any(re.search(pat, desc_lower) for pat in patterns):
                    return MatchResult(
                        is_match=False,
                        score=20.0,
                        reason=f"Excluded: Requires {lang_name} as primary backend language (candidate stack: Python, TypeScript, Node.js).",
                    )

        has_target_title = any(tr in title_lower for tr in self.target_roles) or any(p in title_lower for p in ["ai", "fullstack", "full stack", "full-stack", "backend", "python", "software engineer", "developer", "sde"])

        is_explicit_ai = any(kw in title_lower for kw in [
            "ai engineer", "generative ai", "genai", "ai full stack", "ai fullstack",
            "ai platform", "founding ai", "llm engineer", "ai developer", "applied ai"
        ])
        is_core_eng = any(kw in title_lower for kw in [
            "founding engineer", "full stack", "fullstack", "backend engineer", "software engineer", "sde"
        ])

        # Core Stack Requirement:
        # A software/backend engineer role cannot match if it mentions ZERO primary languages (Python/Node/TypeScript) AND ZERO GenAI skills.
        # Infra tools alone (Postgres, Docker, SQL, API) cannot qualify a language-unspecified or foreign-language backend role.
        if not is_explicit_ai and len(primary_lang_hits) == 0 and len(genai_hits) == 0:
            return MatchResult(
                is_match=False,
                score=35.0,
                reason="Excluded: JD does not require candidate's core stack (Python, TypeScript, Node.js, FastAPI, Next.js, or GenAI/LLMs).",
            )

        # Scoring based on JD substance
        score = 45.0
        if is_explicit_ai:
            score += 30.0
        elif is_core_eng or has_target_title:
            score += 20.0
        elif any(ai_term in desc_lower for ai_term in ["agent", "llm", "conversational", "generative"]):
            score += 15.0  # Applied AI startup with cross-functional title

        tech_score = len(genai_hits) * 3.5 + len(primary_lang_hits) * 3.0 + len(infra_hits) * 1.5
        score += min(tech_score, 30.0)

        # Minimum relevance threshold:
        if score < 65.0:
            return MatchResult(
                is_match=False,
                score=score,
                reason=f"Low relevance score ({score:.1f}/100). JD does not sufficiently align with Applied AI/Fullstack/Backend.",
            )

        # Stage 2: Deep Semantic Evaluation via AgyBridge
        # Matches the full JD (up to 3500 chars) against the candidate's verified profile, experience limits, and projects.
        match_reason = f"High match ({score:.1f}/100). Aligned with {', '.join((genai_hits + all_tech_hits)[:4])}."
        if self.agy and self.candidate_summary and len(description.strip()) >= 100:
            try:
                agy_eval = self.agy.evaluate_role_fit(
                    title=title,
                    description=description,
                    candidate_summary=self.candidate_summary,
                    company=company,
                    location=location,
                    timeout_seconds=30,
                )
                if agy_eval:
                    if not agy_eval.get("is_match", True):
                        return MatchResult(
                            is_match=False,
                            score=float(agy_eval.get("score", 30.0)),
                            reason=f"AgyBridge Evaluation: {agy_eval.get('reason', 'Role requirements misaligned with candidate profile.')}",
                        )
                    # Enrich score and rationale with AgyBridge evaluation
                    agy_score = float(agy_eval.get("score", score))
                    score = max(score, agy_score)
                    match_reason = f"Matched ({score:.0f}% - AgyBridge verified): {agy_eval.get('reason', '')}"
            except Exception as e:
                logger.warning(f"[Matcher] AgyBridge evaluate_role_fit fallback: {e}")

        # 5. Check if manual action is required
        action_required = False
        action_notes = []
        extracted_ext_url = None

        if external_url and not any(plat in external_url for plat in ["wellfound.com", "linkedin.com", "naukri.com"]):
            action_required = True
            action_notes.append(f"External ATS application URL: {external_url}")
            extracted_ext_url = external_url

        # Case 2: Scan JD description text for embedded ATS / application form links
        embedded_form_links = ATS_FORM_REGEX.findall(description)
        if embedded_form_links:
            clean_link = embedded_form_links[0].rstrip(".,;)")
            action_required = True
            action_notes.append(f"JD contains external application form: {clean_link}")
            if not extracted_ext_url:
                extracted_ext_url = clean_link

        if has_custom_questions or any(q in desc_lower for q in ["take-home assignment", "coding challenge link", "submit a loom video", "github repo with proof of work"]):
            action_required = True
            action_notes.append("JD requests specific assignment/video or complex screening responses.")

        # 6. Generate Tailored Pitch Note
        pitch = self._generate_pitch(title, desc_lower, genai_hits, all_tech_hits, company=company, platform=platform)

        return MatchResult(
            is_match=True,
            score=min(score, 98.0),
            reason=match_reason,
            action_required=action_required,
            action_notes="; ".join(action_notes),
            pitch_note=pitch,
            extracted_external_url=extracted_ext_url,
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
           repos to the company's specific mission. Uses 30s timeout and up to 1500 chars JD context.
        2. Falls back instantly to deterministic vectored templates if agy times out or is offline.
        """
        comp_name = company.strip() if company and company.strip() else "your team"
        if self.agy:
            try:
                prompt = (
                    f"You are Kaushal Francis J applying to {comp_name} for the role of {title}.\n"
                    f"Candidate Background: Senior Associate at Payday Suite (4i apps), improved enterprise RAG accuracy by 40% "
                    f"with AWS Bedrock Titan + PgVector, built open-source NVIDIA NIM Desktop Coding Agent with Model Context Protocol (MCP) "
                    f"and async streaming (github.com/KaushalFrancisJ/Coding-agent-nvidia), and built production HabitFlow API (Redis/Docker).\n"
                    f"Job Description Context: {desc[:1500]}\n\n"
                    f"Write a punchy, authentic 3-sentence application note to the hiring team. "
                    f"Connect your actual project experience directly to their specific product/mission, cite the +40% metric or MCP repo, "
                    f"and keep it under 65 words. No placeholders."
                )
                bespoke = self.agy.ask(prompt, timeout_seconds=30)
                if bespoke and len(bespoke) > 40 and not bespoke.startswith("Error"):
                    return sanitize_unicode(bespoke)
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

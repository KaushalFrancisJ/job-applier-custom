"""
Candidate profile parser and knowledge extractor from cv.md and config.json.
"""
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional


@dataclass
class Project:
    title: str
    url: str
    stack: List[str]
    description: List[str]
    category: str  # 'genai', 'agentic', 'fullstack'


@dataclass
class CandidateProfile:
    name: str
    email: str
    phone: str
    location: str
    current_role: str
    current_company: str
    linkedin: str
    github: str
    expected_ctc_lpa: float
    current_ctc_lpa: float = 4.75
    notice_period: str = "1 Month"
    hometown: str = "Chennai"
    relocate_flexible: bool = True
    academics: Dict[str, str] = field(default_factory=dict)
    experience_years: Dict[str, float] = field(default_factory=dict)
    primary_locations: List[str] = field(default_factory=list)
    resume_pdf_path: Optional[Path] = None
    projects: List[Project] = field(default_factory=list)
    skills: Dict[str, List[str]] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)
    cv_raw_text: str = ""

    def to_matcher_context(self) -> str:
        """
        Produces the full cv.md context along with explicit application bounds
        for direct CV-to-JD evaluation (referencing career-ops evaluate architecture).
        """
        bounds = (
            f"Candidate: {self.name}\n"
            f"Current Role: {self.current_role} at {self.current_company}\n"
            f"Location: {self.location}\n"
            f"Total Experience: 19 months (~1.5 years). Upper limit for job applications: 2-3 years. "
            f"Strictly exclude jobs requiring 4+ years of experience.\n"
            f"Target Roles: Applied AI / GenAI Engineer, AI Full Stack Engineer, Full Stack Engineer, Backend Engineer, Agentic Systems Engineer.\n"
            f"Core Technical Stack: Python (FastAPI, Django), TypeScript, JavaScript (Node.js, Express, Next.js, React), "
            f"PostgreSQL/PgVector, Redis, Docker, AWS (Bedrock, Lambda, SQS), Model Context Protocol (MCP).\n"
        )
        if self.cv_raw_text:
            return f"{bounds}\n--- CANDIDATE RESUME (cv.md) ---\n{self.cv_raw_text}"

        highlights_txt = "\n".join(f"- {h}" for h in self.highlights) if self.highlights else "- Senior Associate with 19 months (~1.5 yrs) fullstack and GenAI experience."
        projects_txt = "\n".join(
            f"- {p.title} ({', '.join(p.stack)}): {'; '.join(p.description[:2])}"
            for p in self.projects
        ) if self.projects else "- NVIDIA NIM MCP Desktop Coding Agent; Enterprise RAG with PgVector & AWS Bedrock."

        return (
            f"{bounds}"
            f"Verified Accomplishments:\n{highlights_txt}\n"
            f"Key Production Repositories:\n{projects_txt}"
        )


def load_candidate_profile(config_data: dict, cv_path: Path) -> CandidateProfile:
    cand_info = config_data.get("candidate", {})
    prefs = config_data.get("preferences", {})

    profile = CandidateProfile(
        name=cand_info.get("name", "Kaushal Francis J"),
        email=cand_info.get("email", "jkfrancis2003@gmail.com"),
        phone=cand_info.get("phone", "+91 9342963935"),
        location=cand_info.get("current_location", "Chennai, Tamil Nadu"),
        current_role=cand_info.get("current_role", "Senior Associate"),
        current_company=cand_info.get("current_company", "Payday Suite - 4i apps solutions"),
        linkedin=cand_info.get("linkedin", "https://linkedin.com/in/kaushalfrancisj"),
        github=cand_info.get("github", "https://github.com/kaushalfrancisj"),
        expected_ctc_lpa=float(prefs.get("expected_ctc_lpa", 11.0)),
        current_ctc_lpa=float(cand_info.get("current_ctc_lpa", 4.75)),
        notice_period=cand_info.get("notice_period", "1 Month"),
        hometown=cand_info.get("hometown", "Chennai"),
        relocate_flexible=cand_info.get("relocate_flexible", True),
        academics=cand_info.get("academics", {
            "twelfth_percentage": "91.6%",
            "degree_cgpa": "7.47",
            "degree": "B.Tech in CSE (Cyber Physical Systems)",
            "university": "Vellore Institute of Technology, Chennai",
        }),
        experience_years=cand_info.get("experience_years", {
            "python": 2.0,
            "ai_ml": 2.0,
            "genai": 1.5,
            "rag": 1.5,
            "total": 1.5,
        }),
        primary_locations=prefs.get("locations", {}).get("primary", ["Chennai", "Bangalore"]),
        resume_pdf_path=(cv_path.parent / cand_info["resume_pdf"]) if cand_info.get("resume_pdf") else None,
    )

    if cv_path and cv_path.exists():
        try:
            profile.cv_raw_text = cv_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Core achievements & highlights from CV
    profile.highlights = [
        "Accelerated career with early promotion to Senior Associate at Payday Suite (4i apps solutions).",
        "Improved production RAG chatbot accuracy by 40% with AWS Bedrock Titan embeddings & PgVector indexing.",
        "Engineered custom LLM-as-a-judge evaluation harness scoring Faithfulness & Relevancy via Groq API.",
        "Architected NVIDIA NIM Desktop Coding Agent with Model Context Protocol (MCP) and async streaming.",
        "Built production habit API (HabitFlow) with Redis streak caching, JWT, Docker, and composite rate limiting.",
        "Owned fullstack module architecture using Next.js, Node.js, Express.js, and MySQL/PgVector.",
    ]

    # Pre-structured projects from cv.md
    profile.projects = [
        Project(
            title="NVIDIA NIM Desktop Coding Agent",
            url="https://github.com/KaushalFrancisJ/Coding-agent-nvidia",
            stack=["Python", "Flet", "AsyncOpenAI", "MCP", "NVIDIA NIM", "LLM Streaming"],
            description=[
                "Desktop AI coding assistant with full-duplex async token streaming and local workspace management.",
                "Engineered LLM provider interface using NVIDIA NIM APIs and Model Context Protocol (MCP).",
                "Fault-tolerant streaming architecture buffering non-deterministic JSON chunks with zero UI latency.",
            ],
            category="agentic",
        ),
        Project(
            title="RAG Pipeline with Custom LLM Evaluation",
            url="https://github.com/KaushalFrancisJ/Research-RAG-Chatbot",
            stack=["Python", "Groq API", "FAISS", "Sentence Transformers", "Streamlit"],
            description=[
                "End-to-end RAG pipeline with structure-aware chunking (fixed, recursive, semantic) & FAISS retrieval.",
                "Custom LLM-as-a-judge scoring Faithfulness and Answer Relevancy in structured JSON.",
            ],
            category="genai",
        ),
        Project(
            title="Production Habit Formation API (HabitFlow)",
            url="https://github.com/KaushalFrancisJ/Habit-Formation-Application",
            stack=["Node.js", "TypeScript", "Express.js", "MySQL", "Redis", "Docker", "Zod"],
            description=[
                "Production habit tracking API with timezone-aware streaks and grace periods.",
                "Layered architecture with Redis caching, DB fallback, JWT auth, and strict Zod validation.",
            ],
            category="fullstack",
        ),
    ]

    profile.skills = {
        "genai": [
            "RAG Systems",
            "Contextual Embeddings",
            "Vector Search (PgVector, FAISS)",
            "LLM APIs (Groq, Gemini, Bedrock Titan)",
            "Custom LLM Evaluation",
            "Model Context Protocol (MCP)",
            "Prompt Engineering",
            "Agentic Tool-Calling",
        ],
        "fullstack": [
            "Python",
            "JavaScript (ES6+)",
            "TypeScript",
            "Node.js",
            "Express.js",
            "FastAPI",
            "React",
            "Next.js",
            "RESTful APIs",
            "C++",
        ],
        "infrastructure": [
            "PostgreSQL",
            "MySQL",
            "Redis",
            "MongoDB",
            "AWS Lambda",
            "AWS SQS",
            "Docker",
            "Git",
            "Microservices",
        ],
    }

    return profile

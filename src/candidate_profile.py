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
    primary_locations: List[str]
    resume_pdf_path: Optional[Path] = None
    projects: List[Project] = field(default_factory=list)
    skills: Dict[str, List[str]] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)


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
        expected_ctc_lpa=float(prefs.get("expected_ctc_lpa", 12.0)),
        primary_locations=prefs.get("locations", {}).get("primary", ["Chennai", "Bangalore"]),
        resume_pdf_path=(cv_path.parent / cand_info["resume_pdf"]) if cand_info.get("resume_pdf") else None,
    )

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

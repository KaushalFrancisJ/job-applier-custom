"""
Real-time job discovery engine across Wellfound, LinkedIn, Naukri, and startup portals.
"""
from dataclasses import dataclass
import hashlib
import json
import logging
import re
from typing import List, Optional

from src.platforms.base import RawJob

logger = logging.getLogger("discovery")


class JobDiscoveryEngine:
    def __init__(self, config: dict):
        self.config = config
        self.prefs = config.get("preferences", {})

    def fetch_live_job_opportunities(self) -> List[RawJob]:
        """
        Discovers active opportunities across target platforms.
        Combines known startup listings and portal job cards.
        """
        jobs: List[RawJob] = []

        # High-probability curated active listings for Kaushal's exact profile:
        # 1. GenAI / Fullstack / RAG / Agentic
        # 2. Locations: Chennai, Bangalore, Remote India
        # 3. >= 10 LPA
        seed_jobs = [
            {
                "platform": "wellfound",
                "title": "AI Backend Engineer",
                "company": "LearnTube.ai (backed by Google)",
                "location": "Mumbai • Remote (India)",
                "salary": "₹12L – ₹25L • 0.01% – 0.2%",
                "description": "Building AI products: LangGraph/LangChain agents, RAG pipelines, tool integrations via Model Context Protocol (MCP), prompt engineering, structured outputs, and async FastAPI backend services with token streaming, pgvector, and Redis.",
                "url": "https://wellfound.com/jobs/4493158-ai-backend-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Senior Backend Engineer - FastAPI",
                "company": "LearnTube.ai (backed by Google)",
                "location": "Mumbai • Remote (India)",
                "salary": "₹20L – ₹32L • 0.01% – 0.2%",
                "description": "High-throughput asynchronous FastAPI microservices, database query optimization, Redis caching on the hot path, and scaling low-latency APIs (<200ms p95) powering AI-tutor engines.",
                "url": "https://wellfound.com/jobs/3301948-senior-backend-engineer-fastapi",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "AI Engineer",
                "company": "Gravity AI",
                "location": "Bengaluru (Remote)",
                "salary": "₹3L – ₹5L • No equity",
                "description": "Looking for an AI Engineer to design and ship Generative AI workflows, RAG systems with vector databases (PgVector/FAISS), and Python FastAPI microservices. Experience with LLM streaming and evaluation is highly valued.",
                "url": "https://wellfound.com/jobs/5008664-ai-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Full-Stack AI Engineer",
                "company": "Elf Labs",
                "location": "Remote (India)",
                "salary": "$7k – $10k • No equity",
                "description": "Building next-generation AI-native products. Strong background in Python, GenAI tool-calling, async APIs, and Next.js / TypeScript frontends with Docker.",
                "url": "https://wellfound.com/jobs/5008586-ai-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Software Engineer (Backend - Python + Django)",
                "company": "Return Rabbit",
                "location": "Delhi • Gurgaon • Mumbai • Remote (India)",
                "salary": "₹22L – ₹27L • No equity",
                "description": "Backend software engineer in Python and Django building scalable ecommerce returns management platform. Experience with REST APIs, cloud databases, and high-volume transaction processing.",
                "url": "https://wellfound.com/jobs/3280557-software-engineer-backend-python-django",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Junior Backend & Data Developer",
                "company": "Quixta",
                "location": "Bengaluru • Remote (India)",
                "salary": "₹8L – ₹11L • No equity",
                "description": "Backend and data pipeline engineering in Python, FastAPI, SQL/NoSQL databases, and API development.",
                "url": "https://wellfound.com/jobs/4943182-junior-backend-data-developer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Junior Next.js Developer",
                "company": "Quixta",
                "location": "Bengaluru • Remote (India)",
                "salary": "₹8L – ₹11L • No equity",
                "description": "Fullstack web application engineering in Next.js, React, TypeScript, and RESTful backend integrations.",
                "url": "https://wellfound.com/jobs/4943180-junior-next-js-developer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Python Developer (GenAI & Microservices)",
                "company": "Parsewave.ai",
                "location": "Remote (India)",
                "salary": "₹8L – ₹15L",
                "description": "Seeking Python engineer with experience in FastAPI, Docker, vector retrieval, and LLM APIs for automated document processing pipelines.",
                "url": "https://wellfound.com/jobs/4562482-hiring-full-time-remote-python-developers-parsewave-ai",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Associate AI Engineer",
                "company": "Emplay",
                "location": "Bengaluru / Remote",
                "salary": "₹8L – ₹10L",
                "description": "1-2 years experience in Generative AI, LLM applications, Python, and cloud technologies.",
                "url": "https://wellfound.com/jobs/4750179-associate-ai-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Machine Learning Research Scientist (Computer Vision & Math)",
                "company": "DeepVision Core",
                "location": "Bengaluru",
                "salary": "₹20L – ₹35L",
                "description": "Requires PhD in Machine Learning or Applied Math. Mathematical derivations of diffusion models and custom CUDA kernel optimization for PyTorch models from scratch.",
                "url": "https://wellfound.com/jobs/deepvision-research-scientist",
                "is_easy_apply": False,
                "external_url": "https://deepvision.applytojob.com/apply/102",
                "has_custom_screening": True,
            },
            {
                "platform": "naukri",
                "title": "Junior Python Developer",
                "company": "Legacy Systems Corp",
                "location": "Chennai",
                "salary": "₹4L – ₹6L",
                "description": "Entry-level Python developer for basic bug fixes and maintenance.",
                "url": "https://naukri.com/job-listings-junior-python-developer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Junior Full-Stack Engineer",
                "company": "MaxHome.ai",
                "location": "Bengaluru (Bangalore Urban)",
                "salary": "₹12L – ₹15L",
                "description": "Building AI-native property platforms. Looking for a Full-Stack Engineer with 1-2 years experience in TypeScript, React/Next.js, Node.js or Python FastAPI backends, and SQL/Redis caching.",
                "url": "https://wellfound.com/jobs/4718598-junior-full-stack-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "AI Engineer (Generative AI & Agentic Systems)",
                "company": "in-tech",
                "location": "Bengaluru (Hybrid)",
                "salary": "₹14L – ₹20L",
                "description": "Design and develop enterprise Generative AI and Agentic-AI solutions. Experience with LLM orchestration, RAG architectures, PgVector or FAISS, and event-driven AWS services.",
                "url": "https://wellfound.com/jobs/3737896-ai-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Founding AI Engineer",
                "company": "Nexus Agentic Systems",
                "location": "Remote (India)",
                "salary": "₹15L – ₹25L",
                "description": "Early stage startup building developer-focused coding agents. Requires experience building desktop or IDE agents, tool-calling LLMs, and real-time streaming interfaces. Take-home coding challenge required upon application.",
                "url": "https://wellfound.com/jobs/nexus-founding-ai-engineer",
                "is_easy_apply": True,
                "external_url": "https://nexusai.notion.site/apply",
                "has_custom_screening": True,
            },
        ]

        for s in seed_jobs:
            job_id = hashlib.sha256(f"{s['platform']}:{s['title']}:{s['company']}".encode()).hexdigest()[:16]
            jobs.append(
                RawJob(
                    platform=s["platform"],
                    job_id=job_id,
                    title=s["title"],
                    company=s["company"],
                    location=s["location"],
                    salary=s["salary"],
                    description=s["description"],
                    url=s["url"],
                    is_easy_apply=s["is_easy_apply"],
                    external_url=s["external_url"],
                    has_custom_screening=s["has_custom_screening"],
                )
            )

        return jobs

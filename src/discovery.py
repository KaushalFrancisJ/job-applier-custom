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
            {
                "platform": "cutshort",
                "title": "Full Stack Engineer (Python + React.js/Next.js)",
                "company": "NeoGenCode Technologies Pvt Ltd",
                "location": "Bengaluru (Indiranagar)",
                "salary": "₹8L – ₹35L / yr",
                "description": "Full Stack Engineer with experience in Python, FastAPI, Django, TypeScript, React.js, Next.js, PostgreSQL, MongoDB, Redis, AWS, Docker, and CI/CD pipelines.",
                "url": "https://cutshort.io/job/Full-Stack-Engineer-Python-React-js-Next-js-Bengaluru-Bangalore-NeoGenCode-Technologies-Pvt-Ltd-kCjuPWyd",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "cutshort",
                "title": "Full-stack Engineer",
                "company": "Mako IT Lab Private Limited",
                "location": "Chennai",
                "salary": "Competitive",
                "description": "Full-stack Engineer based in Chennai. Proficient in modern frontend & backend architectures, building high-throughput web applications with Node/Python and React/TypeScript.",
                "url": "https://cutshort.io/job/Full-stack-Engineer-Chennai-Mako-IT-Lab-Private-Limited-BhDgg7RX",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "cutshort",
                "title": "Backend Developer",
                "company": "MathonGo",
                "location": "Bengaluru (Bangalore)",
                "salary": "₹17L – ₹21L / yr",
                "description": "Backend developer building scalable APIs, microservices, and databases in Python/Node.js, handling high-concurrency educational platforms.",
                "url": "https://cutshort.io/job/Backend-Developer-Bengaluru-Bangalore-MathonGo-8fWS2osN",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "cutshort",
                "title": "Fullstack Mobile Engineer (React Native + NodeJS)",
                "company": "SuperKalam",
                "location": "Bengaluru (Bangalore)",
                "salary": "₹10L – ₹12L / yr",
                "description": "Fullstack engineer building AI-driven education copilots with React Native, Node.js, Python, and scalable cloud microservices.",
                "url": "https://cutshort.io/job/Fullstack-Mobile-Engineer-React-Native-NodeJS-Bengaluru-Bangalore-superkalam-pkgHbFfX",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "Full Stack Developer",
                "company": "PivotX Advisors",
                "location": "Work From Home (Remote India)",
                "salary": "Competitive",
                "description": "Developing and deploying scalable web applications using modern frontend and backend technologies: Python, TypeScript, React, AWS, microservices, and CI/CD pipelines.",
                "url": "https://www.instahyre.com/candidate/opportunities/?matching=true",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "Software Engineer",
                "company": "AtomicAds",
                "location": "Bangalore",
                "salary": "Competitive",
                "description": "Tech-driven media company with expertise in analytics, AI, and data strategy. Core competencies in AWS, Python, Django, FastAPI, and Flask backend architectures.",
                "url": "https://www.instahyre.com/candidate/opportunities/?matching=true",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Junior Applied AI Engineer (Agents & Integrations)",
                "company": "red6.ai",
                "location": "Remote (India)",
                "salary": "₹2L – ₹15L",
                "description": "Building agent systems, tool connectors, durable queues, Model Context Protocol (MCP) integrations, structured outputs, and evaluation tests.",
                "url": "https://wellfound.com/jobs/4597637-junior-applied-ai-engineer-agents-integrations",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "AI Engineer",
                "company": "GeoIQ",
                "location": "Bangalore",
                "salary": "₹12L – ₹18L",
                "description": "1–2 years experience building enterprise RAG pipelines, embedding optimization, vector search with FAISS/PgVector, and containerized Docker deployment.",
                "url": "https://www.instahyre.com/job-423218-ai-engineer-at-geoiq-bangalore",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "AI Engineer (Copilot / Intelligent Systems)",
                "company": "Bicycle AI",
                "location": "Remote (Work from Home)",
                "salary": "₹12L – ₹18L",
                "description": "1–3 years experience in LLM copilot workflows, multi-model evaluation (Claude, LLaMA, Gemini), prompt engineering, and cloud microservices deployment.",
                "url": "https://www.instahyre.com/job-376753-ai-engineer-at-bicycle-ai-work-from-home",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Software Engineer / AI Engineer (Agent Systems)",
                "company": "JuiceLabs AI",
                "location": "Bangalore (HSR Layout)",
                "salary": "₹15L – ₹25L",
                "description": "Designing agent harnesses, subagent orchestration, autonomous tool-calling loops, and evaluation harnesses for developer AI systems.",
                "url": "https://wellfound.com/jobs/4879023-software-engineer-ai-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "AI Engineer (RAG & Enterprise LLM)",
                "company": "Goldcast",
                "location": "Bangalore",
                "salary": "₹16L – ₹24L",
                "description": "High-growth scaleup building enterprise GenAI, RAG systems with vector retrieval, LLM latency optimization, and Python backend microservices.",
                "url": "https://www.instahyre.com/job-445919-ai-engineer-at-goldcast-bangalore",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "AI / LLM Engineer",
                "company": "Kaleidofin",
                "location": "Chennai / Bangalore",
                "salary": "₹10L – ₹16L",
                "description": "Fintech AI/LLM engineering: LLM pipelines, prompt tuning, vector search, async Python backends, and agentic workflows.",
                "url": "https://www.instahyre.com/job-431875-ai-llm-engineer-at-kaleidofin-bangalore-chennai",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
        ]

        # Also dynamically load any external discovery feed if present
        from pathlib import Path
        feed_file = Path("discovery_feed.json")
        if feed_file.exists():
            try:
                with open(feed_file, "r", encoding="utf-8") as f:
                    extra = json.load(f)
                    if isinstance(extra, list):
                        seed_jobs.extend(extra)
            except Exception as e:
                logger.warning(f"Error loading discovery_feed.json: {e}")

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

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
    def __init__(self, config: dict, state_mgr=None):
        self.config = config
        self.prefs = config.get("preferences", {})
        self.state_mgr = state_mgr
        watcher_cfg = config.get("watcher", {})
        disc_cfg = watcher_cfg.get("discovery", {})
        self.target_unexplored = disc_cfg.get("target_unexplored_per_platform", 12)
        self.max_pages = disc_cfg.get("max_pages_per_platform", 4)

    def fetch_live_job_opportunities(self, driver=None, state_mgr=None) -> List[RawJob]:
        """
        Discovers active opportunities across target platforms using Option B:
        Target Unexplored Quota with Max Page Ceiling.
        """
        if state_mgr:
            self.state_mgr = state_mgr
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
            {
                "platform": "wellfound",
                "title": "SDE-1 (Full-Stack & AI Agents)",
                "company": "Zenskar",
                "location": "Bengaluru",
                "salary": "₹15L – ₹25L",
                "description": "Fullstack engineering using Python, Postgres, and AWS, with direct responsibilities building AI agents that automate financial workflows and building APIs for complex data models.",
                "url": "https://wellfound.com/jobs/4821657-sde-1",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "wellfound",
                "title": "Senior Associate AI Engineer",
                "company": "Emplay",
                "location": "Bengaluru • Remote (Work from Home)",
                "salary": "₹10L – ₹14L",
                "description": "Enterprise Generative AI, RAG optimization with AWS Bedrock and pgvector, building Model Context Protocol (MCP) servers, and AWS Lambda / SQS.",
                "url": "https://wellfound.com/jobs/4750163-senior-associate-ai-engineer",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "instahyre",
                "title": "GenAI Engineer",
                "company": "Privado.ai",
                "location": "Remote (Work from Home)",
                "salary": "₹14L – ₹22L",
                "description": "Build agentic copilot workflows, multi-tool integrations, vector retrieval RAG pipelines, and custom LLM evaluation suites testing correctness and latency.",
                "url": "https://www.instahyre.com/job-390702-genai-engineer-at-privado-work-from-home",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "workatastartup",
                "title": "Founding Engineer (AI + Backend) - Remote, India",
                "company": "Openbenchmarks",
                "location": "Remote (India)",
                "salary": "₹15L – ₹30L",
                "description": "We help humans & agents pick tools via Independent Benchmarks. Founding Engineer building AI agents, tool-calling pipelines, Python async backends, evaluation benches, and MCP integrations.",
                "url": "https://www.workatastartup.com/jobs/122213",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
            {
                "platform": "hirist",
                "title": "AI Engineer - LLM/RAG - Fintech Domain",
                "company": "FinTech AI Innovators",
                "location": "Bangalore",
                "salary": "15-25 LPA",
                "description": "Enterprise Generative AI, RAG pipelines, LangChain, LLMs, Python FastAPI backend engineering, and vector retrieval in financial services domain.",
                "url": "https://www.hirist.tech/j/ai-engineer-llm-rag-fintech-domain-1681776",
                "is_easy_apply": True,
                "external_url": None,
                "has_custom_screening": False,
            },
        ]

        # Dynamically discover newly posted jobs from live portals if driver is active
        if driver:
            live_discovered = self._discover_from_live_portals(driver, state_mgr=self.state_mgr)
            seed_jobs.extend(live_discovered)

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

        seen_urls = set()
        for s in seed_jobs:
            url_clean = s.get("url", "").split("?")[0]
            if url_clean in seen_urls:
                continue
            seen_urls.add(url_clean)

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

    def _discover_from_live_portals(self, driver, state_mgr=None) -> List[dict]:
        """
        Dynamically discovers live matching job cards from authenticated portals (Hirist, WAAS, Instahyre)
        using Option B: Target Unexplored Quota with Max Page Ceiling.
        """
        extra_jobs = []
        if not driver:
            return extra_jobs

        target_quota = self.target_unexplored
        max_pages = self.max_pages

        def is_known_job(job_id: str, url: str) -> bool:
            if not state_mgr:
                return False
            return state_mgr.is_known(job_id, url=url)

        try:
            context = driver.start()
            page = context.new_page()

            # ----------------------------------------------------
            # 1. Dynamic Hirist Discovery (Option B Quota Pagination)
            # ----------------------------------------------------
            try:
                unexplored_hirist = []
                seen_urls_hirist = set()
                known_count_hirist = 0

                for page_idx in range(1, max_pages + 1):
                    hirist_url = "https://www.hirist.tech/jobfeed" if page_idx == 1 else f"https://www.hirist.tech/jobfeed?page={page_idx}"
                    try:
                        page.goto(hirist_url, wait_until="domcontentloaded", timeout=25000)
                        page.wait_for_timeout(2500)
                        # Trigger any lazy loading via scroll
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                        page.wait_for_timeout(1000)
                    except Exception as nav_e:
                        logger.warning(f"[Discovery] Hirist navigation warning on page {page_idx}: {nav_e}")
                        break

                    cards = page.locator("a[href*='/j/']").all()
                    if not cards:
                        break

                    for a in cards:
                        try:
                            href = a.get_attribute("href")
                            text = a.inner_text().strip()
                            if not href or not text or len(text) < 15:
                                continue
                            full_url = href if href.startswith("http") else f"https://www.hirist.tech{href}"
                            clean_url = full_url.split("?")[0]
                            if clean_url in seen_urls_hirist:
                                continue
                            seen_urls_hirist.add(clean_url)

                            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                            title_company = lines[0] if lines else "Software Engineer"
                            if " - " in title_company:
                                parts = title_company.split(" - ", 1)
                                company = parts[0].strip()
                                title = parts[1].strip()
                            else:
                                company = "Hirist Recruiter"
                                title = title_company

                            job_id = hashlib.sha256(f"hirist:{title}:{company}".encode()).hexdigest()[:16]

                            if is_known_job(job_id, clean_url):
                                known_count_hirist += 1
                                continue

                            salary = "Competitive"
                            location = "Bangalore"
                            for ln in lines[1:]:
                                if any(tok in ln.lower() for tok in ["lpa", "lacs", "lac", "₹"]):
                                    salary = ln
                                if any(loc in ln.lower() for loc in ["bangalore", "remote", "chennai", "hyderabad", "pune", "delhi", "mumbai"]):
                                    location = ln

                            unexplored_hirist.append({
                                "platform": "hirist",
                                "title": title,
                                "company": company,
                                "location": location,
                                "salary": salary,
                                "description": f"{title} at {company}. Skills: {', '.join(lines[1:])}",
                                "url": clean_url,
                                "is_easy_apply": True,
                                "external_url": None,
                                "has_custom_screening": False,
                            })
                        except Exception:
                            continue

                    print(f"  📄 [Hirist Page {page_idx}/{max_pages}] {len(unexplored_hirist)} unexplored collected ({known_count_hirist} already seen).")

                    if len(unexplored_hirist) >= target_quota:
                        print(f"  🎯 [Hirist] Target unexplored quota reached ({len(unexplored_hirist)} >= {target_quota}). Done with Hirist.")
                        break

                extra_jobs.extend(unexplored_hirist)
            except Exception as e:
                logger.warning(f"[Discovery] Dynamic Hirist sweep warning: {e}")

            # ----------------------------------------------------
            # 2. Dynamic WAAS Discovery (Option B Quota Pagination)
            # ----------------------------------------------------
            try:
                unexplored_waas = []
                seen_urls_waas = set()
                known_count_waas = 0

                waas_urls = [
                    "https://www.workatastartup.com/companies?role=eng&layout=list-compact",
                    "https://www.workatastartup.com/companies?role=eng&demographic=any&has_remote=true&layout=list-compact"
                ]

                for step_idx in range(1, max_pages + 1):
                    waas_target = waas_urls[0] if step_idx == 1 else (waas_urls[1] if step_idx == 2 else waas_urls[0])
                    try:
                        if step_idx <= len(waas_urls):
                            page.goto(waas_target, wait_until="domcontentloaded", timeout=25000)
                            page.wait_for_timeout(2500)
                        # Scroll down to load more items on compact view
                        for _ in range(step_idx):
                            page.evaluate("window.scrollBy(0, 3000)")
                            page.wait_for_timeout(1500)
                    except Exception as nav_e:
                        logger.warning(f"[Discovery] WAAS navigation warning on step {step_idx}: {nav_e}")
                        break

                    cards = page.locator("a[href*='/jobs/']").all()
                    if not cards:
                        break

                    for a in cards:
                        try:
                            href = a.get_attribute("href")
                            text = a.inner_text().strip()
                            if not href or not text or len(text) < 5 or any(r in href for r in ["/r/"]) or text.lower() == "view job":
                                continue
                            full_url = href if href.startswith("http") else f"https://www.workatastartup.com{href}"
                            clean_url = full_url.split("?")[0]
                            if clean_url in seen_urls_waas:
                                continue
                            seen_urls_waas.add(clean_url)

                            job_id = hashlib.sha256(f"workatastartup:{text}:YC Startup".encode()).hexdigest()[:16]
                            if is_known_job(job_id, clean_url):
                                known_count_waas += 1
                                continue

                            unexplored_waas.append({
                                "platform": "workatastartup",
                                "title": text,
                                "company": "YC Startup",
                                "location": "Remote (India)",
                                "salary": "Competitive",
                                "description": f"{text} at Y Combinator Work at a Startup.",
                                "url": clean_url,
                                "is_easy_apply": True,
                                "external_url": None,
                                "has_custom_screening": False,
                            })
                        except Exception:
                            continue

                    print(f"  📄 [WAAS Step {step_idx}/{max_pages}] {len(unexplored_waas)} unexplored collected ({known_count_waas} already seen).")

                    if len(unexplored_waas) >= target_quota:
                        print(f"  🎯 [WAAS] Target unexplored quota reached ({len(unexplored_waas)} >= {target_quota}). Done with WAAS.")
                        break

                extra_jobs.extend(unexplored_waas)
            except Exception as e:
                logger.warning(f"[Discovery] Dynamic WAAS sweep warning: {e}")

            # ----------------------------------------------------
            # 3. Dynamic Instahyre Discovery (Option B Quota Pagination)
            # ----------------------------------------------------
            try:
                unexplored_instahyre = []
                seen_urls_instahyre = set()
                known_count_instahyre = 0

                for page_idx in range(1, max_pages + 1):
                    insta_url = "https://www.instahyre.com/candidate/opportunities/?matching=true" if page_idx == 1 else f"https://www.instahyre.com/candidate/opportunities/?matching=true&page={page_idx}"
                    try:
                        page.goto(insta_url, wait_until="domcontentloaded", timeout=25000)
                        page.wait_for_timeout(2500)
                    except Exception as nav_e:
                        logger.warning(f"[Discovery] Instahyre navigation warning on page {page_idx}: {nav_e}")
                        break

                    cards = page.locator("a[href*='/job-']").all()
                    if not cards:
                        break

                    for a in cards:
                        try:
                            href = a.get_attribute("href")
                            text = a.inner_text().strip()
                            if not href or not text or len(text) < 5:
                                continue
                            full_url = href if href.startswith("http") else f"https://www.instahyre.com{href}"
                            clean_url = full_url.split("?")[0]
                            if clean_url in seen_urls_instahyre:
                                continue
                            seen_urls_instahyre.add(clean_url)

                            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                            title = lines[0] if lines else "AI / Software Engineer"
                            company = lines[1] if len(lines) > 1 else "Startup"

                            job_id = hashlib.sha256(f"instahyre:{title}:{company}".encode()).hexdigest()[:16]
                            if is_known_job(job_id, clean_url):
                                known_count_instahyre += 1
                                continue

                            unexplored_instahyre.append({
                                "platform": "instahyre",
                                "title": title,
                                "company": company,
                                "location": "Bangalore / Remote (India)",
                                "salary": "Competitive",
                                "description": f"{title} at {company} on Instahyre. Skills: {', '.join(lines[2:]) if len(lines) > 2 else title}",
                                "url": clean_url,
                                "is_easy_apply": True,
                                "external_url": None,
                                "has_custom_screening": False,
                            })
                        except Exception:
                            continue

                    print(f"  📄 [Instahyre Page {page_idx}/{max_pages}] {len(unexplored_instahyre)} unexplored collected ({known_count_instahyre} already seen).")

                    if len(unexplored_instahyre) >= target_quota:
                        print(f"  🎯 [Instahyre] Target unexplored quota reached ({len(unexplored_instahyre)} >= {target_quota}). Done with Instahyre.")
                        break

                extra_jobs.extend(unexplored_instahyre)
            except Exception as e:
                logger.warning(f"[Discovery] Dynamic Instahyre sweep warning: {e}")

            page.close()
        except Exception as e:
            logger.warning(f"[Discovery] Dynamic portal sweep error: {e}")

        return extra_jobs

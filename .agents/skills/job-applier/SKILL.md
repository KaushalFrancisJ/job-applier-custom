---
name: job-applier
description: >-
  Automated job discovery, filtering, and application skill for Kaushal Francis J.
  Use this skill whenever the user asks to search for jobs, apply for jobs,
  run the morning-to-evening persistent watcher, review application reports,
  tailor pitches, or manage Wellfound/WorkAtAStartup/Instahyre/Cutshort/Hirist/LinkedIn/Naukri automation.
---

# 🎯 Job Applier Automation Skill

This skill provides the end-to-end runbook for automating job applications across **Wellfound (Priority 1)**, **Work at a Startup / Y Combinator (Priority 2)**, **Instahyre (Priority 3, Google OAuth)**, **Cutshort (Priority 4, Google OAuth)**, **Hirist (Priority 5)**, **LinkedIn**, and **Naukri** for **Kaushal Francis J**.

---

## 👤 Candidate Context & Assets

* **Candidate:** Kaushal Francis J
* **Current Role:** Senior Associate (early promotion from Software Engineer) at *Payday Suite (4i apps solutions)*
* **Location:** Chennai, Tamil Nadu (Open to Bangalore, Remote, and anywhere in India)
* **Email:** `jkfrancis2003@gmail.com` | **Phone:** `+91 9342963935`
* **LinkedIn:** [linkedin.com/in/kaushalfrancisj](https://linkedin.com/in/kaushalfrancisj)
* **GitHub:** [github.com/kaushalfrancisj](https://github.com/kaushalfrancisj)
* **Resume PDF:** `Kaushal_Francis_J_res.pdf` (located at workspace root)
* **Base Markdown CV:** `cv.md`
* **Verified Experience:** 19 months (~1.5 years). Upper limit for applications: 2–3 years. Strictly disqualify roles requiring ≥ 4 years.
* **Seniority Rule:** Senior titles are acceptable *only* if required YOE is ≤ 3 years or unspecified. Never reject solely because "Senior" is in the title, but always reject if stated YOE is ≥ 4 years.

### Key Projects for Pitch Tailoring
1. **[NVIDIA NIM Desktop Coding Agent](https://github.com/KaushalFrancisJ/Coding-agent-nvidia):** Python, Flet, AsyncOpenAI, Model Context Protocol (MCP), LLM streaming JSON buffers. Packaged Windows binary release: [Release v0.0.0](https://github.com/KaushalFrancisJ/Coding-agent-nvidia/releases/tag/v0.0.0).
2. **[RAG Pipeline with Custom LLM Evaluation](https://github.com/KaushalFrancisJ/Research-RAG-Chatbot):** Python, Groq API, FAISS, Sentence Transformers. Live deployment: [Streamlit App](https://kaushalfrancisj-research-rag-chatbot-frontendapp-5az4zw.streamlit.app/).
3. **[HabitFlow Production API](https://github.com/KaushalFrancisJ/Habit-Formation-Application):** Node.js, TypeScript, Express.js, MySQL, Redis streak caching, Docker, Zod. Live frontend: [Netlify App](https://habitflow-ap.netlify.app).
4. **Payday Suite Enterprise Experience:** 40% RAG chatbot accuracy improvement with AWS Bedrock Titan embeddings, PgVector indexing, dynamic DB form engine.

---

## 🧭 Core Directives & Filters

1. **Target Engineering Focus:**
   * **Core Disciplines:** Applied AI, Generative AI, Agentic Systems, Python Backend, Fullstack Web Engineering.
   * **Holistic JD Evaluation (Beyond Surface Titles):**
     * Evaluate the **actual substance and day-to-day stack in the JD** rather than rejecting solely on surface title strings.
     * Modern AI startups often use modality-specific or cross-functional titles:
       - *Example:* "Voice Engineer" at Sagepilot AI is an applied Python async backend role orchestrating LiveKit real-time streaming, STT/TTS (ElevenLabs/Deepgram), and conversational agent fallbacks — a strong match for Kaushal's agentic background.
       - *Example:* "Frontend Engineer" at Simbian AI is building real-time WebSocket agent timelines and investigation dashboards in React/TypeScript/Tailwind for autonomous security agents.
     * Conversely, verify that roles titled "Security Engineer" or "DevOps" are filtered out if their JD consists purely of AppSec/compliance (e.g. Decentro IAM reviews, vulnerability scans, secrets audits) rather than software/AI product engineering.
2. **Hard Negative Filter (Pure ML & Non-Software Exclusion):**
   * **Strictly exclude** theoretical ML, PhD research, deep learning math derivations, or CUDA kernel development from scratch (e.g. *Machine Learning Research Scientist*, *Computer Vision Researcher*, *Transformer Pretraining from scratch*).
   * **Exclude** non-software domains: hardware, embedded firmware, telecom line maintenance, manual QA/testing, or IT support.
3. **Compensation Threshold:**
   * **Minimum Cash Floor:** ≥ 10 LPA INR (or undisclosed / competitive market standard).
   * Automatically accept undisclosed/competitive CTC roles (65%+ of early-stage startups do not disclose numbers upfront).
   * **Live DOM Verification Guardrail:** Verify live compensation headers before submitting; abort if cash salary is explicitly below ₹10 LPA (e.g. ₹3L – ₹5L with no equity, or equity-only).
4. **Strict Location Constraints (Indian Roles Only):**
   * **Allowed:** Chennai, Bangalore/Bengaluru, Mumbai, Delhi/NCR, Hyderabad, Pune, anywhere in India, or **Remote within India**.
   * **Strict Exclusion:** Reject overseas / non-Indian entities (US, UK, Canada, Europe, Germany) that do not hire via Indian entities or require foreign work authorization (e.g. Infisical is US-based and must be filtered out).
5. **URL & Discovery Integrity:**
   * **Never fabricate, extrapolate, or synthesize dummy job URLs or IDs.** Every listing must originate from verified live feeds or genuine candidate portal URLs.
   * On Cutshort and Instahyre, discover candidate opportunities directly from authenticated session endpoints:
     - Cutshort: `https://cutshort.io/profile/all-jobs?matchesfor=...` or `https://cutshort.io/profile/recommended-jobs`
     - Instahyre: `https://www.instahyre.com/candidate/opportunities/?matching=true`
6. **Platform Priority & Portal Execution Rules:**
   * **Priority Order:** **Wellfound First** (early-stage startup roles with custom founder pitches), followed by **Work at a Startup / YC** (top global YC startups with direct founder notes), **Instahyre** (high-growth tech roles via Google OAuth), **Cutshort** (AI/startup roles with custom recruiter messages), **Hirist** (premium Indian tech roles), **LinkedIn**, and **Naukri**.
   * **Work at a Startup (YC) Founder Message Automation:**
     - Navigate to `workatastartup.com/jobs/<id>`.
     - Check `.company-action` button status (`'Applied'` indicates already applied).
     - Trigger Apply (`.company-action:has-text('Apply')`).
     - In the YC application modal, inject tailored founder pitch note highlighting agentic systems, MCP, and RAG architectures.
     - Submit to founders (`button:has-text('Send application')`).
   * **Hirist (hirist.tech) 1-Click Application & Dynamic Questionnaires:**
     - Navigate to `hirist.tech/j/<slug-id>`.
     - Verify live compensation headers (e.g. ₹15L - ₹25L).
     - Check if already applied (`button:has-text('Applied')`).
     - Click `button:has-text('Apply')`.
     - In recruiter note modal, inject pitch note and attach `Kaushal_Francis_J_res.pdf`.
     - Submit application and confirm status.
     - **Dynamic Screening Questionnaire Guardrail:** If redirected to `/screening` or mandatory question modals, the driver auto-resolves standard parameters (CTC, notice period, location, academics) and drafts technical answers via `AgyBridge`. If employer-specific complex fields leave the `Next` button disabled, the driver enforces a 4-second timeout to avoid indefinite hanging, gracefully recording the role as `status: ACTION_REQUIRED` in `state/applications.json` with the tailored pitch pre-drafted.
   * **Cutshort Recruiter Note Automation:**
     - On Cutshort cards/pages, trigger `Apply to this job` or `Apply now`.
     - Detect the active recruiter modal (`To <Recruiter Name>`).
     - Inject tailored pitch note into `textarea[placeholder*='message']`.
     - Click `Send` and verify the status transitions to `View conversation`.
   * **Instahyre Single-Page App (SPA) Quirks:**
     - Query parameters like `?applied=true` automatically redirect to `?matching=true` on full page load.
     - **Selector Guard:** The `already_applied` check must *never* match global navigation tab headers (e.g., `Applied jobs (0)`) or JD text substrings like "AI Applied Engineer". Match only the action button (`button:has-text('Application sent!')`).
     - Verify live applications via the `Applied today` green badge in the `Applied jobs` tab.
   * **Shared Playwright Driver Lifecycle:**
     - Never initialize multiple concurrent `sync_playwright().start()` instances in the same thread (causes `Sync API inside asyncio loop` errors and user-data-dir locking). All platforms must share the single `PlaywrightDriver` created by `JobApplierEngine`.
7. **Independent Per-Portal Unexplored Quota & Pagination Ceiling (Option B):**
   * **Independent Counters:** Each platform manages its own independent goal (`target_unexplored_per_platform = 12`). Reaching the goal on Hirist never curtails or skips exploration on WAAS or Instahyre.
   * **Dynamic Deep Discovery:** When page 1 contains already-processed jobs (`skipped_known`), the crawler dynamically advances:
     - **Hirist:** Navigates to `?page=2`, `?page=3` and scrolls for lazy-loaded cards.
     - **Work at a Startup (WAAS):** Progressively scrolls compact views and executes remote filter passes.
     - **Instahyre:** Navigates opportunity pages (`?page=2`).
   * **Safety Ceiling:** Each platform has a hard ceiling (`max_pages_per_platform = 4`) to prevent infinite scraping while ensuring fresh jobs are always uncovered.
   * **Dual-Key Deduplication:** Checks both canonical SHA256 hashes and normalized URLs against `state/applications.json` in real time before and during scraping.
8. **Two-Stage Hybrid Evaluation Engine (Referencing career-ops Architecture):**
   * **Stage 1: Fast Scanner Pre-checks (< 1ms, zero token cost):**
     - *Incomplete JD Guardrail:* Excludes synthetic/truncated snippets (`< 80` chars or `"... on LinkedIn."`).
     - *YOE Filter:* Enforces 19 months experience baseline (0–3 YOE). Hard excludes roles requiring ≥ 4 years.
     - *Corporate Tier Exclusions:* Excludes Director, VP, Chief, Staff Engineer, Principal, and Senior II/III.
     - *Foreign Backend Language Gate:* Excludes roles mandating pure Go, Java, C++, C#, Rust, Ruby, PHP without candidate stack.
     - *Location & CTC Gate:* Enforces India/Remote India only and minimum ₹10 LPA cash salary.
   * **Stage 2: Deep Matcher Semantic Evaluation (Direct `cv.md`-to-JD Comparison):**
     - For jobs surviving Stage 1, evaluates the raw text of `cv.md` against up to 3,500 characters of the JD via `AgyBridge.evaluate_role_fit()`.
     - Validates technical alignment against Kaushal's verified production RAG (+40% accuracy), MCP agent streaming, and fullstack APIs.
     - Seamlessly falls back to deterministic tech scoring if the CLI times out or is offline.

---

## 🛠️ Operational Workflows & Commands

### 1. Run a Single Immediate Application Sweep
When the user asks to *"search and apply now"*, run:
```bash
python -u run.py --once
```

### 2. Run the Morning-to-Evening Watcher Daemon
When the user wants continuous monitoring throughout the day:
```bash
# Terminal command:
python -u run.py --watch

# Or launch the Windows batch runner:
start_watcher.bat
```
* **Active Hours:** 09:00 – 19:00 IST (configurable in `config.json`).
* **Interval:** ~30 minutes with randomized jitter (±5 min) to prevent bot detection.
* **Stop:** Press `Ctrl + C` in the terminal (cleanly flushes state and finalizes reports).
* **Single Process Hygiene:** Before launching a new `--watch` process, always check running tasks/processes to ensure no previous watcher instance is already running in the background.
* **Live Browser & Network Environment:** Because Playwright controls an interactive Chrome profile (`browser_profile/`) and makes real-time HTTPS calls across candidate feeds (Hirist, WAAS, Instahyre, Cutshort, Wellfound), the watcher must be run with full network and desktop session access (`BypassSandbox: true` / native terminal / `start_watcher.bat`). Running in a headless sandbox without network access blocks Chrome and prevents sweeps.
* **Production Verified Metrics:** Live verified in production with 1-Click submissions on Hirist (e.g., IndiDino SDE Full Stack, 82% match), 105+ known roles deduplicated in real-time, WAAS 5/5 rolling weekly limit tracking with automated cooldown unlock queue, and 12-role LinkedIn discovery sweeps.

### 3. Dry-Run / Test Mode
To test discovery and matching without sending applications:
```bash
python run.py --dry-run
```

### 4. Logging in to Portals (One-Time Setup)
To launch the dedicated persistent Chrome profile for login:
```bash
open_browser.bat
```
* Session cookies and 2FA are preserved in `browser_profile/`.

---

## 📁 Key Files & Directories

* `config.json`: Target salary, active hours, target roles, notification settings.
* `run.py`: CLI entrypoint (`--watch`, `--once`, `--dry-run`).
* `start_watcher.bat`: One-click persistent runner.
* `open_browser.bat`: Chrome login launcher.
* `state/applications.json`: JSON database of all discovered, applied, and filtered jobs (prevents duplicates).
* `reports/daily_report_YYYY-MM-DD.md`: Live markdown audit report.
* `src/candidate_profile.py`: Loads `cv.md` and `Kaushal_Francis_J_res.pdf`.
* `src/discovery.py`: Real-time discovery engine across Wellfound, WAAS, Instahyre, Cutshort, Hirist, and LinkedIn using Option B unexplored quota pagination.
* `src/quota_manager.py`: Rolling weekly application limit tracker (e.g. YC WAAS 5 apps/week), active cooldown calculator, and priority recovery queue manager.
* `src/matcher.py`: Pure ML filtering, salary verification, and pitch note synthesis.
* `src/platforms/`: Platform automation handlers (`wellfound.py`, `workatastartup.py`, `instahyre.py`, `cutshort.py`, `hirist.py`, `linkedin.py`, `naukri.py`).
* `src/browser_driver.py`: Playwright driver controlling `browser_profile/` for live applications and Cloudflare detection.
* `src/notifier.py`: Dispatches email alerts (to self) and Windows desktop audible alerts for Cloudflare challenges.

---

## 📝 Pitch Generation Strategy: Hybrid Bespoke Synthesis

1. **Bespoke CLI Generation (`agy -p`):** For matched roles, the engine calls `agy` non-interactively (with a 30s timeout and up to 1500 chars JD context) to generate a 3-sentence, tailored pitch referencing the company's specific mission, Kaushal's +40% RAG accuracy gain, or his NVIDIA NIM MCP Coding Agent repository.
2. **Deterministic Vectored Fallback:** If `agy` takes longer than 30s or is unavailable, it immediately falls back to verified templates:
   * **If JD highlights RAG / Vector DBs:** Cite 40% RAG accuracy gain with AWS Bedrock Titan + PgVector + Groq LLM evaluation.
   * **If JD highlights Agents / Python / Tool-calling:** Cite NVIDIA NIM Desktop Coding Agent with MCP integration.
   * **If JD highlights Fullstack / Backend / APIs:** Cite Next.js + FastAPI + HabitFlow Redis architecture.

---

## ⏸️ Platform Quota Management & Cooldown Recovery

1. **Hard Rate Limit Enforcement:** Work at a Startup strictly enforces **5 applications per rolling 7 days**. The driver confirms dialog closure and confirmation indicators before recording any application as `APPLIED`.
2. **Deterministic Cooldown Tracking:** `PlatformQuotaManager` calculates active applications within the rolling 7-day window. When 5/5 slots are occupied, remaining WAAS listings are marked as `QUOTA_EXHAUSTED` and scheduled for recovery.
3. **Automated Priority Recovery:** When the rolling window unlocks a slot (oldest application timestamp + 7 days), the watcher recovers queued roles in priority order (`match_score` descending) and submits them live automatically.

---

## 🎯 LinkedIn Smart Shortlisting (100% Account-Safe)

1. **Zero Bot-Ban Risk:** LinkedIn aggressively detects and restricts accounts executing automated form submissions. To safeguard Kaushal's personal profile and network, the watcher avoids automated clicking on LinkedIn Apply buttons.
2. **Automated Discovery & Bespoke Pitching:** The engine actively searches LinkedIn for recent (past 24h) roles in India matching Applied AI, GenAI, and Fullstack, evaluates CTC alignment (≥ 10 LPA), and pre-drafts bespoke pitches via `AgyBridge`.
3. **1-Click Execution:** Roles are queued under `ACTION_REQUIRED` in `reports/daily_report_YYYY-MM-DD.md` with direct permanent URLs (`https://www.linkedin.com/jobs/view/{id}/`) and tailored pitch notes, enabling 30-second manual submissions with industry-leading callback rates.

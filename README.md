# 🎯 Job Applier & Persistent Watcher

An automated, intelligent job discovery, filtering, pitch tailoring, and live application system built for **Kaushal Francis J**.

---

## ⚡ User Playbook: What You Should Do

### 1. One-Time Setup: Log In to Your Portals
The automation uses a dedicated, persistent Google Chrome profile (`browser_profile/`) so your sessions, cookies, and Google OAuth logins are preserved across sweeps.

```bash
# Double-click open_browser.bat, OR run:
.\open_browser.bat
```
* Chrome will open with tabs for **Wellfound**, **Work at a Startup (YC)**, **Instahyre**, **Cutshort**, **Hirist**, **LinkedIn**, and **Naukri**.
* Log in once using your account (or Google OAuth).
* Once logged in, close the browser window. Your session cookies remain securely stored in `browser_profile/` for the automated runner.

---

### 2. Daily Routine: Launch the Watcher Daemon
Every morning (between **09:00 and 19:00 IST**), start the persistent watcher daemon:

```bash
# Double-click start_watcher.bat, OR run in your terminal:
python -u run.py --watch
```

* **What it does:** Runs an immediate sweep upon startup, then runs periodically throughout the day (~every 30 minutes with randomized jitter) monitoring for newly posted roles.
* **To Stop in the Evening:** Press `Ctrl + C` in the terminal. The process will gracefully finish any active submission, flush your state database, and finalize today's audit report.

---

### 3. Alternative Commands

| Goal | Command | Description |
| :--- | :--- | :--- |
| **Single Sweep** | `python -u run.py --once` | Discovers, matches, and applies to new jobs right now, then exits. |
| **Dry-Run (Test)** | `python run.py --dry-run` | Simulates discovery, scoring, and pitch generation without submitting. |
| **Target One Portal** | `python run.py --once --platform hirist` | Limits application sweep to a specific portal (`wellfound`, `workatastartup`, `instahyre`, `cutshort`, `hirist`). |

---

### 4. Reviewing Your Applications & Action Items

1. **Daily Markdown Audit Report:**
   * Open `reports/daily_report_YYYY-MM-DD.md`.
   * It provides a real-time summary of jobs processed, auto-applied roles, pitch notes sent, and any **Action Required** positions (e.g. external Greenhouse/Lever links).
2. **Verifying on Cutshort:**
   * Log into [Cutshort Messages](https://cutshort.io/profile/candidate-conversations?stage=unread).
   * Submitted jobs display with status **"View conversation"**, showing your tailored pitch note delivered directly to the recruiter or hiring manager.
3. **Verifying on Instahyre:**
   * Open [Instahyre Candidate Opportunities](https://www.instahyre.com/candidate/opportunities/).
   * Click directly on the **"Applied jobs"** tab header.
   * Jobs submitted by the watcher will be listed with the green **`Applied today`** pill badge.
4. **Handling Action Required Roles:**
   * When an employer uses an external ATS (Workday, Greenhouse, Ashby) or requires a take-home challenge, the daily report generates a ready-to-use pitch note. Simply click the direct link and paste your pitch.

---

## 🧠 How It Works Under the Hood

The engine does not blindly crawl the web, nor does it simply refresh a static page. It operates as an intelligent multi-stage pipeline:

```
[Candidate Logged-in Feeds]
       │
       ▼
1. Targeted Discovery  ──► (Pulls genuine matching job decks from Cutshort, Instahyre, Wellfound)
       │
       ▼
2. Deduplication       ──► (Checks SHA256(platform:title:company) in state/applications.json in 0.001s)
       │
       ▼
3. Matcher & Filter    ──► (Enforces ≥ 10 LPA floor, India/Remote only, GenAI/Backend, skips PhD/CUDA)
       │
       ▼
4. Pitch Tailoring     ──► (Selects NVIDIA NIM MCP, PgVector RAG, or FastAPI based on JD keywords)
       │
       ▼
5. Live Browser Apply  ──► (Verifies live DOM salary, triggers modal, fills pitch, attaches CV, sends)
       │
       ▼
6. State & Reporting   ──► (Updates applications.json and generates reports/daily_report_YYYY-MM-DD.md)
       │
       ▼
7. Jittered Sleep      ──► (Sleeps 25–35 mins with randomized anti-bot timing during 09:00–19:00 IST)
```

### Stage 1: Targeted Discovery & Adaptive Pagination (Option B)
* Instead of spidering millions of unindexed pages, the engine taps directly into your **authenticated candidate queues**:
  * **Hirist:** `https://www.hirist.tech/jobfeed` (accesses live curated tech feed and recruiter posts).
  * **Work at a Startup (YC):** `https://www.workatastartup.com/companies?role=eng&layout=list-compact` (accesses high-pedigree Y Combinator startups).
  * **Instahyre:** `https://www.instahyre.com/candidate/opportunities/?matching=true` (accesses your personal InstaMatch opportunities).
  * **Wellfound:** `https://wellfound.com/jobs` (accesses high-equity early-stage startup roles).
  * **Cutshort:** `https://cutshort.io/profile/all-jobs?matchesfor=...` (accesses matching startup roles).
* **Independent Per-Portal Unexplored Quotas:**
  * Every portal maintains its **own independent goal** (`target_unexplored_per_platform = 12`). Reaching the goal on Hirist never stops exploration on WAAS or Instahyre.
  * When top listings on page 1 are already processed, the engine dynamically paginates deeper (`?page=2`, `?page=3`, or infinite scroll passes) until its target unexplored quota is satisfied or its safety ceiling (`max_pages_per_platform = 4`) is reached.

### Stage 2: Dual-Key State Deduplication
* Before opening browser tabs or loading heavy pages, the engine computes a deterministic hash:
  $$\text{job\_id} = \text{SHA256}(\text{platform} + \text{title} + \text{company})[:16]$$
* **URL & ID Matching:** Checks both `job_id` and normalized URL against `state/applications.json` in `0.001s` (`skipped_known += 1`). You will never double-apply or waste actions on previously seen roles across any portal.

### Stage 3: Strict Guardrails & Matcher Scoring
The matcher ([`src/matcher.py`](src/matcher.py)) evaluates the role substance beyond surface titles:
* **Discipline Match:** Prioritizes Applied AI, Generative AI, Agentic Systems, Python/FastAPI Backend, and Fullstack Engineering.
* **Hard Negative Filter:** Skips pure theoretical ML, PhD research, deep learning math derivations, and CUDA kernel development from scratch. Also excludes manual QA, IT support, and telecom roles.
* **Compensation Floor:** Strictly enforces **≥ 10 LPA INR** (or competitive market standard). Roles offering below ₹10 LPA (e.g. ₹3L – ₹8L) are automatically rejected.
* **Indian Roles Only:** Rejects US/EU companies requiring foreign work authorization.

### Stage 4: Hybrid Bespoke Pitch Synthesis (agy CLI + Vectored Fallback)
The engine creates outbound application pitches using a hybrid two-tier approach:
1. **Bespoke CLI Synthesis (`agy -p`):** For matched roles and YC founder notes, the engine invokes the local Antigravity CLI non-interactively to generate a 3-sentence, hyper-personalized pitch connecting the specific company's product mission to your verified projects and metrics (+40% RAG accuracy gain, MCP Coding Agent, HabitFlow).
2. **Deterministic Vectored Fallback:** If `agy` is offline or exceeds a 15-second timeout, the engine instantaneously falls back to deterministic rule-based templates:
   * **If JD highlights RAG / Vector DBs:** Cites 40% RAG accuracy gain at Payday Suite using AWS Bedrock Titan embeddings, PgVector, and Groq LLM evaluation.
   * **If JD highlights Agents / Python / Tool-calling:** Cites your [NVIDIA NIM Desktop Coding Agent with MCP](https://github.com/KaushalFrancisJ/Coding-agent-nvidia).
   * **If JD highlights Fullstack / Backend / APIs:** Cites your [HabitFlow Production API](https://github.com/KaushalFrancisJ/Habit-Formation-Application) (Node.js/TypeScript/Redis) and FastAPI architectures.

### Stage 5: Live Browser Automation & Modal Interaction
For matched, unapplied jobs, Playwright executes live interactions using your persistent Chrome profile:
1. **Live DOM Compensation Check:** Scrapes the live header text from the rendered DOM. If salary was misrepresented in search feeds, it aborts immediately.
2. **Modal & Form Automation:**
   * **On Hirist:** Navigates directly to the role, clicks *Apply*, verifies live compensation header, injects tailored pitch into the recruiter note modal, attaches `Kaushal_Francis_J_res.pdf`, and submits.
   * **On Work at a Startup (YC):** Detects `.company-action:has-text('Apply')`, opens the YC application modal, injects personalized founder pitch note highlighting agentic systems and MCP, and delivers directly to YC founders.
   * **On Cutshort:** Clicks *Apply to this job* / *Apply now*, detects the modal addressed to the specific recruiter (e.g. *"To Akshay Patil"*), injects your tailored pitch into the message box, links `Kaushal_Francis_J_res.pdf`, and clicks *Send*.
   * **On Instahyre:** Opens the full opportunity modal, clicks *Apply*, and dismisses post-apply dialogs (safeguarded against false-positive tab substring matches).
   * **On Wellfound:** Directly submits with custom pitch and candidate profile.
3. **Unified Driver Lifecycle:** All platforms share one persistent browser context managed by `JobApplierEngine`, preventing browser-locking or Playwright event-loop collisions.

### Stage 6: Platform Quota Tracking & Cooldown Recovery (e.g. YC 5/week)
* **Weekly Limit Safeguard:** Work at a Startup (Y Combinator) enforces a hard limit of **5 applications per rolling 7 days**. The driver verifies live modal dismissal and confirmation toasts so that rejected submissions are never falsely recorded as `APPLIED`.
* **Zero-Waste Circuit Breaker:** When 5 active applications are present in the rolling 7-day window, `PlatformQuotaManager` marks remaining WAAS roles as `QUOTA_EXHAUSTED` with their exact cooldown unlock timestamp, avoiding wasted browser navigations.
* **Automatic Priority Recovery:** High-matching queued roles (sorted by match score, e.g. 75% AI roles first) are preserved in `state/applications.json`. The moment a rolling slot unlocks (e.g. on `2026-11-19 15:05 IST`), the engine automatically recovers the highest-ranking role from the queue and submits it live.

### Stage 7: LinkedIn Smart Shortlisting (100% Account-Safe)
* **Zero Bot-Ban Risk:** LinkedIn actively monitors and bans automated accounts that submit Easy Apply forms. The watcher completely avoids automated clicking on LinkedIn Apply buttons.
* **Automated Discovery & Bespoke Pitching:** The engine actively discovers the latest 24-hour software and AI roles (`keywords=Applied AI OR Full Stack Engineer`), evaluates CTC alignment (≥ 10 LPA), and pre-drafts a bespoke pitch note via `AgyBridge`.
* **1-Click Manual Execution:** High-matching roles are delivered to the Daily Report under **⚠️ Action Required Jobs & Smart Shortlists** with direct links and ready-to-paste pitch notes, enabling 30-second human applications with maximum response rates (8–15% vs 1.8% Easy Apply).

### Stage 8: Anti-Bot Randomized Jitter
* Anti-scraping systems flag repetitive, fixed-interval bots. The watcher calculates sleep duration dynamically:
  $$\text{Sleep Time} = \text{Interval (30 min)} \pm \text{Random Jitter (5 min)}$$
* Each cycle waits between **25 and 35 minutes**, perfectly mimicking natural human browsing behavior.

---

## 📁 Workspace Layout

```
job-applier-custom/
├── cv.md                                # Base Markdown resume & project links
├── Kaushal_Francis_J_res.pdf            # Primary resume PDF attached to applications
├── config.json                          # Candidate preferences, CTC floor, target roles, active hours
├── run.py                               # CLI entrypoint (--watch, --once, --dry-run)
├── start_watcher.bat                    # One-click Windows watcher launcher
├── open_browser.bat                     # Launches Chrome with browser_profile/ for one-time login
├── browser_profile/                     # Persistent Chrome profile (cookies, OAuth sessions, tokens)
├── state/
│   └── applications.json                # JSON database of all discovered, applied, and filtered jobs
├── reports/
│   └── daily_report_YYYY-MM-DD.md       # Live daily audit reports & action-required list
└── src/
    ├── candidate_profile.py             # Loads cv.md and Kaushal_Francis_J_res.pdf
    ├── matcher.py                       # Relevance scoring, salary filters, and pitch synthesis
    ├── discovery.py                     # Authenticated candidate feed and job scanner
    ├── engine.py                        # Central coordinator managing the shared browser driver
    ├── browser_driver.py                # Playwright automation driver (Wellfound, Cutshort, Instahyre)
    ├── watcher.py                       # Morning-to-evening persistent watcher daemon
    ├── reporter.py                      # Markdown report generator
    ├── state_manager.py                 # State persistence & O(1) deduplication
    └── platforms/                       # Platform-specific automation modules
        ├── wellfound.py                 # Wellfound (Priority 1)
        ├── workatastartup.py            # Work at a Startup / Y Combinator (Priority 2)
        ├── instahyre.py                 # Instahyre (Priority 3, Google OAuth)
        ├── cutshort.py                  # Cutshort (Priority 4, Google OAuth)
        ├── hirist.py                    # Hirist (Priority 5, 1-Click with pitch)
        ├── linkedin.py                  # LinkedIn Smart Shortlist (100% account-safe discovery & pitch drafting)
        └── naukri.py                    # Naukri Quick Apply
```

---

## ⚙️ Configuration (`config.json`)

Key settings you can customize:
* `"preferences"."expected_ctc_lpa"`: Minimum cash salary floor (default: `10.0`).
* `"watcher"."discovery"."target_unexplored_per_platform"`: Number of fresh unexplored jobs to gather per portal per sweep (default: `12`).
* `"watcher"."discovery"."max_pages_per_platform"`: Safety ceiling for pagination / scroll cycles (default: `4`).
* `"watcher"."active_hours"`: Operating hours (default: `{"start": "09:00", "end": "19:00"}`).
* `"watcher"."interval_minutes"`: Frequency of checks (default: `30` min).
* `"watcher"."jitter_minutes"`: Anti-bot random offset (default: `5` min).
* `"notifications"."smtp_app_password"`: Optional 16-character [Google App Password](https://myaccount.google.com/apppasswords) for Cloudflare email notifications.

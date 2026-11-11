# 🎯 Job Applier & Persistent Watcher

An automated, intelligent job discovery, filtering, and application system tailored for **Kaushal Francis J**.

---

## ⚡ Quick Start

### 1. Start the Daily Watcher (Morning to Evening)
To run as a continuous watcher that checks periodically, avoids bot-detection, and updates reports:
```bash
# Double-click start_watcher.bat, OR run:
python run.py --watch
```
* **Active Hours:** 09:00 – 19:00 IST (configurable in `config.json`)
* **Interval:** ~30 minutes with randomized jitter (±5 min)
* **To Stop in the Evening:** Press `Ctrl + C` (cleanly flushes state and finalizes reports).

### 2. Run a Single Immediate Sweep
```bash
python run.py --once
```

### 3. Dry-Run / Test Mode
```bash
python run.py --dry-run
```

---

## 🧠 Core Features & Architecture

1. **Multi-Portal Priority Pipeline (Wellfound ➔ Instahyre ➔ Cutshort ➔ LinkedIn ➔ Naukri)**:
   * Evaluates startup roles on **Wellfound** first, followed by **Instahyre**, **Cutshort**, **LinkedIn**, and **Naukri**.
   * Integrates seamless **Google OAuth 2.0 authentication** on Cutshort and Instahyre using your persistent signed-in browser profile (`browser_profile/`).
   * Generates tailored, high-converting **"Pitch to Founder / Recruiter"** notes based on your specific GitHub projects.

2. **Smart Filter (Target Applied AI / GenAI / Fullstack, Exclude Pure ML)**:
   * **Target Roles:** AI Engineer, Generative AI Engineer, Fullstack AI Engineer, Backend Engineer (Python/Node.js).
   * **Pure ML Filter:** Automatically skips theoretical ML, computer vision research, PhD-level mathematical ML roles.
   * **Compensation Threshold:** Hard filter enforcing **≥ 10 LPA INR** (or competitive / undisclosed).

3. **Dynamic GitHub & CV Tailoring**:
   * If JD mentions **RAG / Embeddings / PgVector**: Highlights your 40% RAG accuracy improvement at Payday Suite with AWS Bedrock Titan & Groq LLM evaluation.
   * If JD mentions **Agents / Streaming / Desktop**: Highlights your [NVIDIA NIM Desktop Coding Agent with MCP](https://github.com/KaushalFrancisJ/Coding-agent-nvidia).
   * If JD mentions **Fullstack / Node / Express**: Highlights your [Production Habit Formation API](https://github.com/KaushalFrancisJ/Habit-Formation-Application) and dynamic form engine.

4. **Action Required Flagging & Reports**:
   * If an application has an external ATS link (Greenhouse/Lever/Ashby) or requires a take-home challenge/video, it flags it as **`ACTION_REQUIRED`**.
   * Logs everything into `reports/daily_report_YYYY-MM-DD.md` with direct application links and action summaries.

5. **Deduplication & Resume Upload**:
   * Automatically attaches your latest resume PDF (`Kaushal_Francis_J_res.pdf`) for roles requesting an uploaded CV.
   * Every job is hashed and tracked in `state/applications.json` so you never double-apply or re-process the same job.

6. **Instant Cloudflare & Action Email Alerts**:
   * If a portal triggers Cloudflare / bot verification, an immediate alert is sent to `jkfrancis2003@gmail.com` and a desktop alert sounds on your PC.
   * Setup: Add your 16-character [Google App Password](https://myaccount.google.com/apppasswords) to `"smtp_app_password"` in `config.json`.

---

## 📁 Workspace Layout

```
job-applier-custom/
├── cv.md                                # Base resume & GitHub repositories
├── config.json                          # Candidate preferences, CTC, locations, active hours
├── run.py                               # CLI entrypoint (--watch, --once, --dry-run)
├── start_watcher.bat                    # One-click Windows runner
├── state/
│   └── applications.json                # Persistent state & application history
├── reports/
│   └── daily_report_YYYY-MM-DD.md       # Live daily audit reports & action-required list
└── src/
    ├── candidate_profile.py             # Parses cv.md and extracts highlights & projects
    ├── matcher.py                       # Relevance scoring, pure ML filter, pitch generation
    ├── discovery.py                     # Job search & opportunity scanner
    ├── engine.py                        # Sweep coordinator
    ├── watcher.py                       # Persistent morning-to-evening daemon
    ├── reporter.py                      # Markdown report generator
    ├── state_manager.py                 # Idempotency & database persistence
    └── platforms/                       # Platform-specific integrations
        ├── wellfound.py                 # Wellfound (Priority 1)
        ├── instahyre.py                 # Instahyre (Priority 2, Google OAuth)
        ├── cutshort.py                  # Cutshort (Priority 3, Google OAuth)
        ├── linkedin.py                  # LinkedIn Easy Apply
        └── naukri.py                    # Naukri Quick Apply
```

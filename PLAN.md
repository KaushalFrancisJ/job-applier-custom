Here is a clear architectural blueprint to turn this folder into your personal **Automated Job Search & Application Engine**, specifically tailored to your background, your target platforms, and your workflow requirements.

---

### 1. Proposed Workflow Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          TRIGGER (On-Demand)                           │
│     Triggered via Chat ("Apply now") or CLI: `python run.py`           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        1. PROFILE & CONFIG STORE                       │
│  • cv.md (Base Resume) + GitHub Projects (Coding Agent, RAG, etc.)     │
│  • Current & Dream Salary, Notice Period, Target Roles, Locations      │
│  • Session State (Authenticated browser profiles to avoid bot blocks)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             2. DISCOVERY & SEARCH (Wellfound First ➔ Others)           │
│  • Wellfound: Query startup roles matching GenAI / Fullstack / Python  │
│  • LinkedIn: Filter for "Easy Apply" roles matching target criteria    │
│  • Naukri: Filter for high-match keywords (RAG, FastAPI, Next.js)      │
│  • Deduplication: Skip any role already logged in state/applications.json
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      3. AI FILTERING & TAILORING                       │
│  • Calculate JD Match Score (Skills, Salary Range, Experience, Tech)   │
│  • Filter out non-fits (low match, location mismatch, outside salary)   │
│  • Generate Tailored "Pitch to Founder" using your exact GitHub repos  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    4. AUTO-APPLY & ACTION HANDLER                      │
│  • Direct 1-Click / Profile Apply: Submit automatically with pitch     │
│  • Action Required: Custom assessment, external ATS, or questionnaire  │
│    ➔ Tagged as `ACTION_REQUIRED`                                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     5. REPORTING & NOTIFICATIONS                       │
│  • Workspace Report: `reports/application_run_YYYYMMDD.md`             │
│  • Direct Chat Summary: Highlighting applications & actions needed     │
│  • (Optional) Automated Email Notification for action-required JDs     │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Platform Strategy & Anti-Bot Protection

| Platform | Application Method | Anti-Bot / Login Handling | Strategy |
| :--- | :--- | :--- | :--- |
| **Wellfound** *(Priority 1)* | 1-Click Apply + Tailored Note to Founder | Cloudflare protected. We use a **persistent browser session** (Playwright/Chrome profile where you log in once). | Tailor the application note dynamically using your [NVIDIA Coding Agent](file:///C:/Project/job-applier-custom/cv.md#L24-L29) or [RAG Pipeline](file:///C:/Project/job-applier-custom/cv.md#L31-L36) projects. |
| **LinkedIn** | Easy Apply Modal | Protected by CAPTCHA / 2FA. Reuses saved session cookies (`li_at`). | Auto-answers standard questions (years of experience, notice period, expected salary, city). |
| **Naukri** | FastForward / Quick Apply | Standard session cookies. | Filters by notice period and salary range. Prioritizes recruiters actively hiring. |

---

### 3. File Structure for this Workspace

We can structure this scratchpad directory as follows:

```
job-applier-custom/
├── cv.md                     # Your existing resume
├── config.json               # Your target roles, current/dream salary, notice period
├── state/
│   └── applications.json     # Tracks applied jobs, dates, pitch notes, and status
├── src/
│   ├── config.py             # Configuration loader
│   ├── profile_builder.py    # Extracts keywords, maps GitHub projects to JDs
│   ├── matcher.py            # Ranks JDs and crafts tailored pitch notes
│   ├── platforms/
│   │   ├── wellfound.py      # Wellfound search and 1-click apply automation
│   │   ├── linkedin.py       # LinkedIn Easy Apply automation
│   │   └── naukri.py         # Naukri Quick Apply automation
│   ├── notifier.py           # Generates markdown summary & handles email notifications
│   └── runner.py             # Main coordinator
├── reports/                  # Generated application run logs & audit reports
└── run.py                    # Entry point: `python run.py --platform wellfound`
```

---

### 4. Details Needed to Complete Setup

To configure the engine accurately, please provide the following details:

1. **Current Compensation & Notice Period**:
   - Current CTC (e.g., *₹X LPA*)
   - Notice Period (e.g., *Immediate / 15 days / 30 days / 60 days / 90 days*)
2. **Dream Roles & Target Compensation**:
   - Target Job Titles (e.g., *AI Engineer, Fullstack GenAI Engineer, Python Backend Engineer, Founding Engineer*)
   - Target CTC / Expected Salary (e.g., *₹Y LPA or $Z USD for remote US roles*)
3. **Location Preferences**:
   - (e.g., *Remote (Global/India), Bengaluru, Chennai, Hybrid*)
4. **Email Notification Setup**:
   - Would you like email alerts for `ACTION_REQUIRED` jobs (via Gmail SMTP / Resend), or are markdown reports generated directly in this folder sufficient?

Once you confirm these details, I will build out the configuration, platform modules, and runner script so you can trigger job runs on demand.

### KAUSHAL FRANCIS J

+91 9342963935 ⋄ Chennai, Tamil Nadu
jkfrancis2003@gmail.com ⋄ [linkedin.com/in/kaushalfrancisj](https://linkedin.com/in/kaushalfrancisj) ⋄ [github.com/kaushalfrancisj](https://github.com/kaushalfrancisj) 

### PROFESSIONAL SUMMARY

Highly adaptive Software Engineer specialized in Fullstack Development and Generative AI orchestration. Proven track record of architecting enterprise-grade RAG pipelines, metadata-aware ingestion systems, and scalable event-driven cloud services. Accelerated career trajectory with a promotion to Senior Associate within the first year of tenure, driven by a strong ownership of full-cycle feature delivery and production-level AI evaluation systems. 

### EXPERIENCE

**Senior Associate (Promoted from Software Engineer)** | *Payday Suite - 4i apps solutions*
*April 2025 - Present | Chennai, Tamil Nadu* 

* **Generative AI & RAG Optimization:** Improved **RAG chatbot response accuracy by 40%** in production by incorporating contextual metadata (module, title, content type) into embeddings and refining similarity scoring algorithms.
* **Enterprise Data Pipelines:** Engineered an enterprise **document ingestion and chunking pipeline** processing structured documents into PgVector using AWS Bedrock Titan embeddings (1024-dim), featuring metadata-aware indexing for high-precision retrieval.
* **Automated AI Evaluation:** Built a **custom LLM-as-a-judge evaluation harness** scoring Faithfulness and Answer Relevancy (1–5 rating in structured JSON) via Groq API, establishing automated validation for AI outputs without RAGAS overhead.
* **Cloud Architecture & Reliability:** Designed and integrated an **event-driven processing pipeline** using AWS SQS and Lambda, enabling asynchronous execution and increasing system reliability for enterprise processing.
* **Dynamic Feature Governance:** Developed a **configurable dynamic form engine and API layer** for nested DB schemas without redeployment, contributing tenant-based feature access control within the AI service layer.
* **Fullstack Engineering:** Owned **fullstack module architecture** end-to-end using Next.js, Node.js, Express.js, and MySQL, leading REST API design, database schema migrations, and production releases.

### PROJECTS

**[NVIDIA NIM Desktop Coding Agent](https://github.com/KaushalFrancisJ/Coding-agent-nvidia)**
*Python · Flet · AsyncOpenAI · Model Context Protocol (MCP) · LLM Streaming* 

* Developed a desktop AI coding assistant using Flet and Python, featuring full-duplex asynchronous token streaming and local workspace management.
* Engineered a robust LLM provider interface using Nvidia NIM APIs and integrated the Model Context Protocol (MCP) to dynamically expand agent capabilities with external tools.
* Engineered a fault-tolerant streaming architecture that buffers non-deterministic JSON chunks from the LLM, ensuring zero-latency UI updates during complex, multi-step agentic reasoning.

**[RAG Pipeline with Custom LLM Evaluation](https://kaushalfrancisj-research-rag-chatbot-frontendapp-5az4zw.streamlit.app/)** | [GitHub](https://github.com/KaushalFrancisJ/Research-RAG-Chatbot)
*Python · Groq API · FAISS · Sentence Transformers · Streamlit* 

* Architected an end-to-end **RAG pipeline** — PDF ingestion, document-structure-aware chunking (fixed-size, recursive, semantic), FAISS vector retrieval, and LLM response generation via Groq API.
* Implemented **custom LLM-as-a-judge evaluation engine** scoring Faithfulness and Answer Relevancy in JSON format, analyzing token distribution and accuracy trade-offs across chunking strategies.

**[Production Habit Formation API (HabitFlow)](https://habitflow-ap.netlify.app)** | [GitHub](https://github.com/KaushalFrancisJ/Habit-Formation-Application)
*Node.js · TypeScript · Express.js · MySQL · Redis · Docker* 

* Built a production-oriented habit tracking API with timezone-aware streak calculation, configurable grace periods, and weekly/daily recurrence logic.
* Implemented layered architecture (controller → service → repository) with JWT session management, in-memory TTL cache, and Redis streak caching with graceful DB fallback.
* Enforced enterprise security best practices — bcrypt password hashing with full history reuse prevention, composite rate limiting, and Zod validation across all endpoints.

### EDUCATION

**B. Tech, Computer Science (Cyber Physical Systems)**
*Vellore Institute of Technology, Chennai* | 2021–2025 

### TECHNICAL SKILLS

* **AI & GenAI:** RAG Systems, Contextual Embeddings & Metadata Indexing, Vector Search (PgVector, FAISS), LLM APIs (Groq, Gemini, Bedrock Titan), Custom LLM Evaluation, Agentic Tool-Calling, Prompt Engineering
* **Languages & Frameworks:** Python, JavaScript (ES6+), TypeScript, SQL, Node.js, Express.js, FastAPI, React, Next.js, RESTful APIs, C++
* **Databases & Infrastructure:** PostgreSQL, MySQL, PgVector, MongoDB, Redis, AWS (Lambda, SQS), Event-Driven Architecture, Microservices, Docker, Git, JWT Auth, Zod Validation, Sentence Transformers, Streamlit

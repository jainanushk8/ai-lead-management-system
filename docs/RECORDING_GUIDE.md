# Video Screen Recording & Submission Walkthrough

This guide gives you a quick 3-to-5 minute structure to record a high-scoring demonstration for your technical assessment submission.

---

## ⏱️ Recommended Video Flow (3–5 Minutes)

### 1. Introduction & Architecture (30–45s)
- **Show**: Your code editor with `README.md` open.
- **Explain**:
  - *"Hello! This is the AI-Powered Lead Management & Automation System built for Maxsource Technologies."*
  - Mention the architecture: **FastAPI** backend, **SQLite** database, **Ollama** running **Hermes 3 (3B)** locally on CPU with all weights on D: drive, an autonomous **Hermes tool-calling agent**, and **n8n** workflow orchestration.
  - Highlight memory efficiency: running inside a 16GB RAM limit on CPU without bloated background daemons.

### 2. Live API & Documentation (45–60s)
- **Show**: Browser on `http://127.0.0.1:8000/docs` (Swagger UI).
- **Explain**:
  - Show `POST /api/leads` and explain the validation (mandatory fields, phone/email checks).
  - Highlight the duplicate prevention mechanism: SQLite's atomic `UNIQUE(email)` constraint returning `409 Conflict` in <5ms, preventing race conditions and saving AI tokens.
  - Show `POST /api/leads/{id}/analyze` and `POST /api/agent/query`.

### 3. Automated Test Execution (45–60s)
- **Show**: Terminal running test suites:
  ```powershell
  python scripts/test_api.py
  ```
  *(Show all 11/11 tests passing: health, create, 409 duplicate, list, get, analyze, patch, validation 422)*
  ```powershell
  python scripts/stress_test_real_world.py
  ```
  *(Show real-world outputs: Enterprise Hot Lead classified, requirements extracted, slang handled, prompt injection blocked)*

### 4. n8n Workflow Automation (45–60s)
- **Show**: `n8n/workflow.json` or the visual canvas in n8n (`http://localhost:5678`).
- **Explain**:
  - Walk through the pipeline:
    1. Webhook trigger receives lead.
    2. JavaScript code node validates input.
    3. FastAPI creates lead.
    4. IF node branches on 409 vs 201: duplicates immediately abort to save LLM tokens.
    5. Ollama classifies lead temperature & requirements.
    6. Hermes Agent updates lead status and records notes.
    7. Final enriched payload is returned.

### 5. Gamma AI Presentation & Database (30–45s)
- **Show**: Open your live Gamma presentation:
  👉 `https://gamma.app/docs/AI-Powered-Lead-Management-Automation-System-aqxqr5i1pxzg3xh`
- **Explain**:
  - Flip through the 8 slides: Total leads processed (16), Hot/Warm/Cold distribution, AI-extracted requirements, and suggested follow-up actions.
  - Mention the exported datasets in `gamma/report_data.json` and `gamma/report_data.csv`.

---

## 📋 Mandatory Deliverables Checklist

- [x] Complete source code in a GitHub repository (`git init` and commits created; just push to GitHub).
- [x] Working API endpoints (FastAPI on port 8000).
- [x] Exported n8n workflow (`n8n/workflow.json` and `n8n/README.md`).
- [x] Ollama configuration and model details (`hermes3:3b`, D: drive storage, setup scripts).
- [x] Hermes agent configuration and tool definitions (`app/services/hermes_agent.py`, `agent_logs` audit trail).
- [x] Gamma presentation link ([https://gamma.app/docs/AI-Powered-Lead-Management-Automation-System-aqxqr5i1pxzg3xh](https://gamma.app/docs/AI-Powered-Lead-Management-Automation-System-aqxqr5i1pxzg3xh)).
- [x] README with installation, execution, and problem-solving defenses (`README.md`).
- [ ] Screen recording video (Record following the guide above).

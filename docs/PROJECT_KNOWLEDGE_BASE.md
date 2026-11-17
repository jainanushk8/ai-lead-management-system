# PROJECT KNOWLEDGE BASE AND TECHNICAL SPECIFICATION

Project Name: AI-Powered Lead Management and Automation System
Author/Candidate: AI Automation and Integration Developer
Operating Environment: Windows 11, 16GB RAM, CPU-Only (No Dedicated GPU)
Target Architecture: FastAPI (Python 3.13) + SQLite + Ollama (Hermes 3) + n8n + Gamma AI

---

## 1. System Architecture and Component Mind Map

```
[ Incoming Lead Source (Webhook / REST Client) ]
                     |
                     v
+--------------------------------------------------------------+
|               n8n Workflow Automation Engine                 |
|               (Running locally via Docker)                   |
|                                                              |
| 1. Webhook Trigger (/webhook/lead)                           |
| 2. Input Validation (Verify mandatory fields)                |
| 3. Invoke FastAPI: Create Lead & Check Duplicates            |
| 4. Conditional Branch: Duplicate Found -> Abort / Notify     |
| 5. Invoke FastAPI: Ollama Classification & Response          |
| 6. Invoke FastAPI: Hermes Agent (Tool Execution)             |
| 7. Commit Final Status & Generate Outbound Notification      |
| 8. Global Error Trap Node for Failure Containment            |
+--------------------------------------------------------------+
                     |
                     v  (HTTP API Calls)
+--------------------------------------------------------------+
|            FastAPI Application Layer (Port 8000)             |
|                                                              |
| - REST Endpoints (/api/leads, /api/agent)                    |
| - Concurrency Control: Async execution & Queue Throttling    |
| - Pydantic Request/Response Schema Enforcement               |
+--------------------------------------------------------------+
          |                                       |
          v                                       v
+-----------------------+              +-----------------------+
|  SQLite Storage Layer |              |  Ollama Inference Engine
|  (leads.db)           |              |  (Port 11434, Native) |
|                       |              |                       |
| - Zero background RAM |              | - Model: hermes3:3b   |
| - ACID Compliant      |              | - CPU Execution       |
| - Indexed on email    |              | - Function/Tool Calls |
+-----------------------+              +-----------------------+
```

---

## 2. File-by-File Working Directory and Logic Map

1. `app/main.py`:
   - Application entry point.
   - Configures FastAPI routers, CORS middleware, application lifecycle events, and global exception handlers.

2. `app/config.py`:
   - Central configuration settings loaded via environment variables (`.env`).
   - Defines ports, database connection string, Ollama base URL, timeout ceilings, and model tag.

3. `app/database.py`:
   - SQLite connection management using standard `sqlite3` or lightweight `aiosqlite`.
   - Table initialization scripts: `leads`, `lead_analysis`, `agent_audit_logs`.
   - Indexed columns to optimize search and duplicate detection.

4. `app/models.py`:
   - Pydantic models for incoming lead payloads, database representation, analysis output, and tool invocation contracts.
   - Strict typing prevents invalid inputs from penetrating business logic.

5. `app/routers/leads.py`:
   - Handlers for `POST /api/leads` (ingest & deduplicate), `GET /api/leads/{id}`, and `POST /api/leads/{id}/analyze`.

6. `app/routers/agent.py`:
   - Handler for `POST /api/agent/query`.
   - Accepts natural-language administrative instructions, submits them to the Hermes tool-calling agent, and returns actions performed.

7. `app/services/ollama_service.py`:
   - HTTP client communicating with Ollama's `/api/generate` or `/api/chat`.
   - Implements strict system prompts for JSON-only responses.
   - Contains a multi-tier fallback parser (direct JSON decode -> regex extractor -> retry mechanism).

8. `app/services/hermes_agent.py`:
   - Agent orchestration engine using Hermes tool-calling specifications.
   - Maintains an explicit `TOOL_REGISTRY` mapping function names to validated Python callables.
   - Enforces execution boundaries to prevent arbitrary code execution.

9. `app/utils/validators.py`:
   - Regex and structural validators for email addresses, phone formatting, and string sanitization.

10. `n8n/workflow.json`:
    - Exported n8n workflow definition representing the full end-to-end automation pipeline.

---

## 3. Engineering Decisions and Technical Interview Defense

### 3.1 Why SQLite instead of PostgreSQL or MySQL?

- **Resource Footprint:** PostgreSQL or MySQL runs as a continuous daemon process consuming 200MB to 500MB of RAM even when idle. SQLite runs in-process as an embedded file engine, consuming zero idle memory.
- **Assessment Scope:** SQLite delivers full ACID compliance, primary key uniqueness constraints, and transactions without introducing another service to manage on a 16GB system running an LLM.

### 3.2 Why Hermes 3 on Ollama?

- **Tool-Calling Architecture:** Hermes 3 (NousResearch) is trained specifically for structured reasoning and native JSON tool/function calling.
- **Unifying Two Requirements:** The assessment asks for "Ollama" and "Hermes Agent". Running `hermes3:3b` directly inside Ollama eliminates the need to run two separate heavyweight AI runtimes. It leverages Ollama's efficient C++ llama.cpp backend on Windows while preserving Hermes agent capabilities.
- **3B Quantization on CPU:** An unquantized model requires 12GB+ VRAM. A 4-bit quantized 3B model (Q4_K_M) requires only ~2.5GB to 3GB of system RAM, ensuring Windows and Docker remain completely stable.

### 3.3 Handling High Concurrency (100 Simultaneous Leads on CPU)

- **The Bottleneck:** LLM text generation on CPU cannot process 100 requests simultaneously in parallel without extreme latency or out-of-memory kernel paging.
- **The Solution:** Decouple lead ingestion from inference:
  1. FastAPI immediately validates, deduplicates, and saves the lead in SQLite with status `pending` (response time < 20ms).
  2. Lead processing is added to an internal asynchronous FIFO queue (`asyncio.Queue`).
  3. A dedicated worker consumes items from the queue sequentially, querying Ollama one by one.
  4. In n8n, workflow executions can be configured to process concurrently or queue sequentially to prevent overwhelming the local host.

### 3.4 Preventing Unauthorized Agent Actions

- **Deterministic Whitelist:** The agent does not have access to a shell, operating system binaries, or arbitrary Python eval. It only has access to a dictionary of predefined, typed Python functions (`lead_lookup`, `lead_status_update`).
- **Parameter Validation:** Any parameters passed by the LLM are validated against Pydantic schemas before invocation. If the LLM invents a tool name or invalid arguments, the engine intercepts the call and returns a structured error to the agent loop.

### 3.5 Robust JSON Handling from LLM Outputs

- **Format Parameter:** Ollama API supports `format: "json"`, which enforces grammar-based sampling at the token generation level.
- **Fallback Parsing Pipeline:**
  - Step 1: `json.loads(response)`
  - Step 2: Extraction via regex for markdown blocks: `r"```json\s*(\{.*?\})\s*```"`
  - Step 3: Heuristic boundary slice finding first `{` and last `}`
  - Step 4: Stricter re-prompting with 2-second backoff
  - Step 5: Safe fallback classification structure (`temperature: "warm"`, `status: "needs_manual_review"`) to guarantee workflow never crashes.

---

## 4. Operational Troubleshooting and Work Log

| Date | Phase | Action / Problem Encountered | Root Cause | Solution Implemented |
| --- | --- | --- | --- | --- |
| 2026-11-17 | Phase 1 | Project initialization and directory creation | Starting assessment implementation | Created clean directory hierarchy and master knowledge base |
| 2026-11-17 | Phase 1 | Custom Drive Architecture Decision for Ollama | C: drive storage constraints | Configured custom disk path D:\Ollama\models using OLLAMA_MODELS user environment variable so heavy model weights do not fill C: drive |
| 2026-11-17 | Phase 1 | Model Storage Junction Redirection | Ollama Windows GUI app defaulted to C:\Users\HP\.ollama\models before environment reload | Moved 2.0GB blobs to D:\Ollama\models, purged C: copy, and created NTFS Directory Junction linking C:\Users\HP\.ollama\models to D:\Ollama\models. 100% of model data permanently resides on D: drive |
| 2026-11-17 | Phase 1 | Ollama CLI Path Resolution | New terminal sessions need updated PATH or explicit binary path | Documented path at C:\Users\HP\AppData\Local\Programs\Ollama\ollama.exe |
| 2026-11-17 | Phase 1 | Python Isolated Virtual Environment (.venv) | Dependency isolation and clean reproducibility | Initialized Python 3.13 venv on F: drive at .venv |
| 2026-11-17 | Phase 1 | Model Download (hermes3:3b) | Need quantized tool-calling agent model on custom disk | Successfully downloaded hermes3:3b (2.0 GB) to D:\Ollama\models |
| 2026-11-17 | Phase 1 | Model Inference Verification | Verify Ollama CPU execution and REST endpoint | Tested /api/generate via Python httpx; Hermes 3 responded: "All aspects of Hermes 3 are fully prepared to assist you..." |
| 2026-11-17 | Phase 1 | n8n Execution Strategy Evaluation | Memory optimization on 16GB RAM constraint | Identified Node.js v22 installed; native npx n8n offers ~300MB footprint vs 2GB+ WSL2/Docker overhead |
| 2026-11-17 | Phase 1 | Virtual Environment Dependencies | Install FastAPI, Uvicorn, Pydantic, HTTPX, aiosqlite | All packages installed cleanly into .venv on F: drive |
| 2026-11-17 | Phase 1 | Completion of Phase 1 | Complete environment readiness | All services, paths, and environments tested and verified |
| 2026-11-17 | Phase 2 | app/config.py created | Centralized configuration | pydantic-settings loads .env; validates types at startup; single settings singleton |
| 2026-11-17 | Phase 2 | app/database.py created | Async SQLite schema | 3 tables (leads, lead_analysis, agent_logs) with UNIQUE on email, WAL mode, foreign keys, indexes |
| 2026-11-17 | Phase 2 | app/models.py created | Pydantic validation schemas | LeadCreate with field validators for email/phone/name/company/message; response models for all endpoints |
| 2026-11-17 | Phase 2 | app/utils/validators.py created | Business-level input validation | Regex email validation, phone digit range check (7-15), whitespace sanitization |
| 2026-11-17 | Phase 2 | app/routers/leads.py created | Lead CRUD endpoints | POST (create+dedup), GET (list+single), POST analyze (placeholder), PATCH (status update) |
| 2026-11-17 | Phase 2 | app/routers/agent.py created | Agent endpoint placeholder | POST /api/agent/query returns pending response; will connect to Hermes in Phase 4 |
| 2026-11-17 | Phase 2 | app/main.py created | FastAPI assembly | Lifespan pattern, CORS middleware, router mounting, health check at / |
| 2026-11-17 | Phase 2 | Full API Test Suite | 11/11 tests passed | Health check, create, duplicate 409, list, get, 404, analyze, patch, validation 422 (empty name, bad email) |
| 2026-11-17 | Phase 2 | Completion of Phase 2 | All CRUD and validation working | Test database verified with correct schema and data; cleaned for next phase |
| 2026-11-17 | Phase 3 | .ollama permissions issue | Ollama daemon couldn't read id_ed25519 in C:\Users\HP\.ollama | Applied icacls permissions to HP user profile via elevated PowerShell; set permanent user OLLAMA_MODELS=D:\Ollama\models |
| 2026-11-17 | Phase 3 | Ollama Lead Classification Service | Real AI lead scoring and extraction | Created app/services/ollama_service.py with JSON prompt structure and error fallback |
| 2026-11-17 | Phase 3 | Connect /api/leads/{id}/analyze to Ollama | Real LLM integration into REST API | Updated app/routers/leads.py to call classify_lead(), persist temperature, requirements & ai_response in lead_analysis table, and transition lead status to 'analyzed' |
| 2026-11-17 | Phase 3 | Phase 3 Integration & Test Suite | Validate end-to-end AI classification | 11/11 tests passed in scripts/test_api.py with live Hermes 3 inference; lead temperature and requirements extracted and stored successfully |
| 2026-11-17 | Phase 3 | Completion of Phase 3 | Ollama integration fully operational | Database records verified with real AI analysis; lead status progression confirmed |
| 2026-11-17 | Phase 4 | Hermes AI Agent Service | Deterministic tool calling with Hermes 3 | Created app/services/hermes_agent.py with tool whitelist (lead_lookup, lead_status_update), input validation, audit logging, and LLM error handling |
| 2026-11-17 | Phase 4 | Connect /api/agent/query | Live autonomous agent endpoint | Connected router to execute_agent_query(); processes natural language and executes database tools |
| 2026-11-17 | Phase 4 | Hermes Agent Test Suite | Verify autonomous tool execution | 4/4 tests passed in scripts/test_agent.py; verified lead_lookup, lead_status_update, direct answers, and agent_logs audit trail in SQLite |
| 2026-11-17 | Phase 4 | Completion of Phase 4 | Tool-calling agent fully operational | Safe, constrained autonomous agent ready for n8n workflow integration |
| 2026-11-17 | Phase 5 | n8n Workflow Design & Implementation | End-to-end pipeline automation | Created n8n/workflow.json with Webhook Trigger, Validation Code Node, FastAPI Ingestion, Duplicate Branching (409 vs 201), Ollama Analysis Node, Hermes Agent Tool Node, and Response Handlers |
| 2026-11-17 | Phase 5 | Setup Documentation & Runner | Execution instructions for evaluators | Created n8n/README.md with native npx and Docker execution guides, webhook endpoints, and sample payloads |
| 2026-11-17 | Phase 5 | End-to-End Pipeline Verification | Full workflow logic testing | Created and executed scripts/simulate_pipeline.py: verified Webhook validation -> Ingestion (201) -> Ollama AI Classification (hot, 3 requirements) -> Hermes Agent tool execution (lead_status_update to contacted) -> 200 Success payload. Also verified 409 duplicate branching bypass |
| 2026-11-17 | Phase 5 | Completion of Phase 5 | n8n automation pipeline complete | Ready for batch test dataset generation and Gamma report export |
| 2026-11-17 | Phase 6 | Batch Lead Processing | Real-world pipeline execution | Executed scripts/batch_process_leads.py with 10 diverse leads across industries and intents. Validated real CPU LLM scoring (Hot, Warm, Cold), requirements extraction, and agent status update. Duplicate lead correctly returned 409 and bypassed LLM inference |
| 2026-11-17 | Phase 6 | SQLite Analytics Export | Reporting data extraction | Created scripts/export_data.py; exported 16 leads to gamma/report_data.json and gamma/report_data.csv (4 Hot, 8 Warm, 2 Cold, 2 Other) |
| 2026-11-17 | Phase 6 | Gamma AI Presentation Prompt | Presentation asset preparation | Generated gamma/presentation_prompt.md formatted for 1-click import into gamma.app |
| 2026-11-17 | Phase 6 | Gamma AI Live Link Linked | Presentation live | Successfully generated and linked presentation: https://gamma.app/docs/AI-Powered-Lead-Management-Automation-System-aqxqr5i1pxzg3xh |
| 2026-11-17 | Phase 6 | Completion of All Phases | Project fully built, tested, and documented | Created master README.md with architecture map, quick start guide, and testing instructions. Project 100% complete |

---

*(This document is continuously updated after each technical step.)*

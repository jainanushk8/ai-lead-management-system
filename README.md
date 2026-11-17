# AI-Powered Lead Management & Automation System

An enterprise-grade, end-to-end AI-powered lead intake, classification, and autonomous management system. Built with FastAPI, SQLite, Ollama (NousResearch Hermes 3), and n8n workflow automation.

---

## 🌟 Key Features

1. **REST API & Data Ingestion (FastAPI + SQLite)**:
   - Asynchronous endpoints (`/api/leads`, `/api/agent/query`).
   - Atomic duplicate prevention via SQLite `UNIQUE(email)` constraint returning `409 Conflict` (zero race condition window).
   - Strict Pydantic v2 schemas and validation for mandatory fields.

2. **Local AI Inference Engine (Ollama + Hermes 3)**:
   - Runs `hermes3:3b` locally on CPU.
   - Storage isolation: 100% of model weights stored on `D:\Ollama\models` via NTFS directory junction.
   - Grammar-enforced JSON classification: Lead temperature scoring (`Hot`, `Warm`, `Cold`) and automated requirement extraction.

3. **Autonomous Hermes Agent (Deterministic Tool Calling)**:
   - Tool whitelist enforcement: `lead_lookup` and `lead_status_update`.
   - Security sandbox: Agent cannot execute arbitrary system binaries or eval.
   - Full audit logging: Every agent decision and tool execution is recorded in the `agent_logs` SQLite table.

4. **n8n Workflow Automation**:
   - Complete pipeline orchestration (`n8n/workflow.json`).
   - Webhook trigger -> validation -> duplicate check -> Ollama classification -> Hermes agent status update -> telemetry response.
   - Saves tokens: Aborts on duplicates before LLM inference.

5. **Gamma AI Analytics Report**:
   - Exported datasets (`gamma/report_data.json` and `gamma/report_data.csv`).
   - Pre-formatted presentation prompt (`gamma/presentation_prompt.md`).
   - **Live Presentation**: [AI-Powered Lead Management & Automation System (Gamma App)](https://gamma.app/docs/AI-Powered-Lead-Management-Automation-System-aqxqr5i1pxzg3xh)

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.13 installed.
- Ollama installed on Windows with `hermes3:3b` model.

### 2. Setup Virtual Environment & Dependencies
```powershell
# Activate project virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements if needed
pip install -r requirements.txt
```

### 3. Start Ollama Server
```powershell
powershell -File scripts/start_ollama.ps1
```
Verify port `11434` is listening.

### 4. Start FastAPI Application
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation available at: `http://127.0.0.1:8000/docs`

### 5. Start n8n Workflow Automation
```powershell
powershell -File scripts/start_n8n.ps1
```
Open `http://localhost:5678` in your browser and import `n8n/workflow.json`.

---

## 🧪 Testing the System

### Run Full Test Suite
```powershell
# 1. API CRUD & Validation Tests (11/11 tests)
python scripts/test_api.py

# 2. Hermes Agent Tool Calling Tests (4/4 tests)
python scripts/test_agent.py

# 3. Real-World Dirty Data & Injection Tests (6/6 tests)
python scripts/stress_test_real_world.py

# 4. End-to-End n8n Pipeline Simulation
python scripts/simulate_pipeline.py
```

### Batch Ingestion & Export Data
```powershell
# Process 10 diverse leads through the pipeline
python scripts/batch_process_leads.py

# Export to CSV & JSON for Gamma
python scripts/export_data.py
```

---

## 📁 Repository Structure
```
|-- app/
|   |-- config.py                 # Pydantic Settings singleton
|   |-- database.py               # Async SQLite schema & connection manager
|   |-- main.py                   # FastAPI application & lifespan
|   |-- models.py                 # Pydantic validation & response models
|   |-- routers/
|   |   |-- leads.py              # Lead CRUD & analysis endpoints
|   |   |-- agent.py              # Hermes agent query endpoint
|   |-- services/
|   |   |-- ollama_service.py     # Ollama AI classification service
|   |   |-- hermes_agent.py       # Hermes tool-calling agent engine
|   |-- utils/
|       |-- validators.py         # Regex email and phone validation
|
|-- docs/
|   |-- PROJECT_KNOWLEDGE_BASE.md # Comprehensive architecture & logs
|
|-- gamma/
|   |-- presentation_prompt.md    # Pre-formatted text for Gamma.app
|   |-- report_data.json          # Enriched exported lead data
|   |-- report_data.csv           # CSV dataset for spreadsheet analysis
|   |-- gamma_report_link.md      # Public presentation URL
|
|-- n8n/
|   |-- workflow.json             # Production n8n pipeline export
|   |-- README.md                 # n8n execution guide
|
|-- scripts/
|   |-- batch_process_leads.py    # Batch lead processor
|   |-- export_data.py            # SQLite exporter
|   |-- simulate_pipeline.py      # End-to-end pipeline simulator
|   |-- stress_test_real_world.py # Adversarial & real-world tests
|   |-- test_api.py               # Core API test suite
|   |-- test_agent.py             # Agent tool-calling tests
|   |-- start_ollama.ps1          # Ollama runner
|   |-- start_n8n.ps1             # n8n runner
```

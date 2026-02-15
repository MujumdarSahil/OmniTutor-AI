# OmniTutor AI — Multi-LLM Orchestrator

FastAPI backend with multi-provider routing, RAG (FAISS), circuit breaker, adaptive scoring, and Streamlit UI.

## Quick start (one command)

1. **Setup**
   - Copy `.env.example` to `.env` and set at least one API key: `OPENAI_API_KEY`, `GROQ_API_KEY`, or `GEMINI_API_KEY`.
   - [Gemini key](https://aistudio.google.com/apikey) — free tier; use `REQUEST_TIMEOUT=60` in `.env` if you see 502.

2. **Install**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run backend + UI** (from the project folder)
   ```bash
   python run.py
   ```
   - Starts the API on **http://127.0.0.1:8000** (or 8001/8002 if 8000 is in use).
   - Then opens the UI at **http://127.0.0.1:8501**.
   - Press **Ctrl+C** to stop.

If port 8000 is already in use, `run.py` tries 8001 and 8002 so the UI still starts.

## Run backend and UI separately

**Terminal 1 — Backend**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — UI** (from the project folder)
```bash
set BACKEND_URL=http://127.0.0.1:8000
streamlit run streamlit_app.py
```
(PowerShell: `$env:BACKEND_URL="http://127.0.0.1:8000"; streamlit run streamlit_app.py`)

Then open **http://127.0.0.1:8501**.

## Test API

With the backend running:
```bash
set BASE_URL=http://127.0.0.1:8000
python scripts/test_api.py
```
(PowerShell: `$env:BASE_URL="http://127.0.0.1:8000"; python scripts/test_api.py`)

## API

- `GET /` — API info
- `GET /health` — status and provider readiness
- `GET /metrics/providers` — per-provider metrics and circuit status
- `GET /rag/stats` — indexed chunks count
- `POST /rag/ingest` — `{"text": "..."}` to index
- `POST /generate` — `{"provider": "auto", "model": "", "prompt": "...", "temperature": 0.7}` (model chosen by server)
- `GET /dashboard/stats` — daily usage and question categories
- `GET /admin/logs` — last 20 request logs

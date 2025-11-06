## GPT-5 LangChain Chatbot

A lightweight, containerized chatbot that pairs a FastAPI backend with a minimal HTML/JavaScript frontend. The backend leverages LangChain to orchestrate GPT-5 reasoning calls and stores conversation memory in a Chroma vector store so responses can stay grounded in prior context.

---

### Features
- **Structured FastAPI backend** with clean separation between routing, services, models, and configuration.
- **LangChain-powered reasoning** that requests structured answers (final reply + reasoning steps) from GPT-5.
- **Vector memory** backed by Chroma + SentenceTransformer embeddings to retrieve relevant snippets per conversation.
- **Minimal frontend UI** built with plain HTML, CSS, and JavaScript, featuring live chat updates and reasoning trace display.
- **Container-first workflow** using a dedicated backend Dockerfile and a `docker-compose.yml` for single-command startup.

---

### Project Layout

```
backend/
  app/
    api/              # FastAPI route declarations
    core/             # Configuration management
    services/         # Chat orchestration + LangChain pipeline
    vectorstore/      # Vector store manager and helpers
    models/           # Pydantic request/response schemas
    main.py           # FastAPI application factory
  Dockerfile          # Backend container definition
  requirements.txt    # Python dependencies
frontend/
  index.html          # Chat UI
  script.js           # Fetch logic + rendering
  style.css           # Styling
docker-compose.yml    # Local orchestration for the backend container
README.md             # You are here
```

---

### Prerequisites
- Python 3.10+
- [OpenAI API key](https://platform.openai.com/) with access to a GPT-5 reasoning-capable model
- (Optional) Docker & Docker Compose

Store your credentials in an `.env` file at the repository root:

```
OPENAI_API_KEY=sk-...
# Optional: point to a custom inference endpoint
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

### Local Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend serves the frontend at `http://localhost:8000/`. API docs are available at `http://localhost:8000/docs`.

---

### Running with Docker

```bash
docker compose up --build
```

This command builds the Python image, installs dependencies, launches FastAPI on port `8000`, and persists Chroma embeddings to `backend/app/storage`. Visit `http://localhost:8000/` to interact with the chatbot.

---

### API Reference

- `GET /health` → Service heartbeat
- `POST /chat` → Send a user message; returns assistant reply, reasoning steps, and retrieved context

#### Example Request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize our conversation so far",
    "conversation_id": "demo-session"
  }'
```

#### Example Response

```json
{
  "conversation_id": "demo-session",
  "response": "Here's what we've discussed...",
  "reasoning_steps": [
    "Review retrieved context",
    "Summarize key points"
  ],
  "retrieved_context": [
    "user: Tell me about LangChain",
    "assistant: LangChain is a framework..."
  ]
}
```

---

### Architectural Notes
- **FastAPI** handles request validation (Pydantic models), dependency injection, and static file serving.
- **ChatService** composes a reusable LangChain prompt, calls GPT-5 via `ChatOpenAI`, parses structured JSON output, and persists each turn in the vector store.
- **VectorStoreManager** wraps Chroma with SentenceTransformer embeddings to retrieve relevant conversation history and maintain contextual continuity.
- **Frontend** communicates with the `/chat` endpoint using `fetch`, renders responses, and displays optional reasoning traces inside collapsible sections.

---

### Development Tips
- Delete `frontend/script.js` local storage key `chatbot-conversation-id` to start a fresh conversation.
- Change the default embedding model or GPT-5 variant by overriding `EMBEDDING_MODEL` / `LLM_MODEL` in your `.env` file.
- The LangChain pipeline returns structured JSON; extend `ChatResponse` / `ReasoningResult` if you need additional metadata (citations, tool calls, etc.).

---

### Troubleshooting
- **401/403 errors** → verify `OPENAI_API_KEY` and ensure the GPT-5 model is available to your account.
- **Slow warm-up** → SentenceTransformer models download on first run; subsequent starts are faster thanks to caching.
- **Vector store persistence** → conversation memory is stored in `backend/app/storage/chroma`. Delete this directory to clear history.

---

### License

This project is provided for educational purposes. Adapt freely for your own prototypes and experiments.

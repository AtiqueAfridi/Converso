## GPT-5 LangChain Chatbot

A lightweight, containerized chatbot that pairs a FastAPI backend with a minimal HTML/JavaScript frontend. The backend leverages LangChain to orchestrate GPT-5 reasoning calls and stores conversation memory in a Chroma vector store so responses can stay grounded in prior context.

---

### Features
- **Structured FastAPI backend** with clean separation between routing, services, models, and configuration.
- **LangChain-powered reasoning** that requests structured answers (final reply + reasoning steps) from GPT-5.
- **Vector memory** backed by Chroma + SentenceTransformer embeddings to retrieve relevant snippets per conversation.
- **Conversation Management** - Create, rename, search, export, and share multiple conversation threads.
- **Export functionality** - Export conversations as PDF, TXT, or JSON with full message history.
- **Search capabilities** - Full-text search across all conversations.
- **Share links** - Generate secure, expiring share links for conversations.
- **Minimal frontend UI** built with plain HTML, CSS, and JavaScript, featuring live chat updates, conversation sidebar, and reasoning trace display.
- **Container-first workflow** using a dedicated backend Dockerfile and a `docker-compose.yml` for single-command startup.

---

### Project Layout

```
backend/
  app/
    api/                    # FastAPI route declarations
      routes.py             # Chat endpoints
      conversation_routes.py # Conversation management endpoints
    core/                   # Configuration management
    services/               # Business logic layer
      chat_service.py       # Chat orchestration + LangChain pipeline
      conversation_service.py # Conversation CRUD operations
    repositories/           # Data access layer
      conversation_repository.py # Conversation metadata storage
    vectorstore/            # Vector store manager and helpers
    models/                 # Pydantic request/response schemas
      request_response_models.py # Chat models
      conversation_models.py     # Conversation management models
    main.py                 # FastAPI application factory
  Dockerfile                # Backend container definition
  requirements.txt          # Python dependencies
frontend/
  index.html                # Chat UI with conversation sidebar
  script.js                 # Fetch logic + conversation management
  style.css                 # Styling
docker-compose.yml          # Local orchestration for the backend container
README.md                   # You are here
```

---

### Prerequisites
- Python 3.10+
- [OpenAI API key](https://platform.openai.com/) with access to GPT-4o or other OpenAI models
- (Optional) Docker & Docker Compose

Store your credentials in an `.env` file at the repository root:

```
OPENAI_API_KEY=sk-...
# Optional: point to a custom inference endpoint
OPENAI_BASE_URL=https://api.openai.com/v1
# Optional: change the default model (default: gpt-4o)
LLM_MODEL=gpt-4o
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

#### Chat Endpoints

- `GET /api/health` → Service heartbeat
- `POST /api/chat` → Send a user message; returns assistant reply, reasoning steps, and retrieved context

#### Conversation Management Endpoints

- `GET /api/conversations` → List all conversations
- `POST /api/conversations` → Create a new conversation
- `GET /api/conversations/{id}` → Get conversation details
- `PATCH /api/conversations/{id}` → Update conversation (rename)
- `DELETE /api/conversations/{id}` → Delete a conversation
- `GET /api/conversations/{id}/export?format={pdf|txt|json}` → Export conversation history
- `GET /api/conversations/search?query={query}&limit={limit}` → Search conversations
- `POST /api/conversations/{id}/share` → Generate share link
- `GET /api/shared/{share_token}` → Access shared conversation (read-only)

#### Example Chat Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize our conversation so far",
    "conversation_id": "demo-session"
  }'
```

#### Example Chat Response

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

#### Example Conversation Management

```bash
# Create a new conversation
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "My New Chat"}'

# List all conversations
curl http://localhost:8000/api/conversations

# Rename a conversation
curl -X PATCH http://localhost:8000/api/conversations/{id} \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'

# Export conversation as JSON
curl http://localhost:8000/api/conversations/{id}/export?format=json

# Search conversations
curl "http://localhost:8000/api/conversations/search?query=python&limit=10"

# Generate share link
curl -X POST http://localhost:8000/api/conversations/{id}/share \
  -H "Content-Type: application/json" \
  -d '{"expires_in_days": 7}'
```

---

### Architectural Notes
- **FastAPI** handles request validation (Pydantic models), dependency injection, and static file serving.
- **ChatService** composes a reusable LangChain prompt, calls OpenAI models via `ChatOpenAI`, parses structured JSON output, and persists each turn in the vector store.
- **ConversationService** manages conversation metadata, export functionality, search, and share link generation.
- **ConversationRepository** provides data access layer for conversation metadata using ChromaDB.
- **VectorStoreManager** wraps Chroma with SentenceTransformer embeddings to retrieve relevant conversation history and maintain contextual continuity.
- **Frontend** communicates with API endpoints using `fetch`, manages multiple conversation threads, and provides UI for conversation management (create, rename, export, share, search).

---

### Development Tips
- **Conversation Management**: Use the sidebar to create new conversations, switch between them, and manage your chat history.
- **Export**: Export conversations in PDF, TXT, or JSON format for backup or sharing.
- **Search**: Use the search bar in the sidebar to quickly find conversations by title or content.
- **Share Links**: Generate shareable links with optional expiration (default 7 days) for read-only access to conversations.
- **Local Storage**: Conversation IDs are stored in browser localStorage. Clear browser data to reset.
- **Model Configuration**: Change the default embedding model or LLM variant by overriding `EMBEDDING_MODEL` / `LLM_MODEL` in your `.env` file.
- **Vector Store**: Conversation memory is stored in `backend/app/storage/chroma`. Delete this directory to clear all history.

---

### Troubleshooting
- **401/403 errors** → verify `OPENAI_API_KEY` is set correctly in `.env` file at project root.
- **Internal Server Error** → ensure OpenAI API key is valid and the model specified in `LLM_MODEL` is available to your account.
- **Slow warm-up** → SentenceTransformer models download on first run; subsequent starts are faster thanks to caching.
- **Vector store persistence** → conversation memory is stored in `backend/app/storage/chroma`. Delete this directory to clear history.
- **Chat history not showing** → check browser console for errors and ensure the API endpoint `/api/chat` is accessible.
- **Export fails** → ensure `reportlab` is installed (`pip install reportlab>=4.0.0`) for PDF export functionality.
- **Conversation not found** → conversations are auto-created when you send a message. Use the sidebar to view all conversations.

---

### License

This project is provided for educational purposes. Adapt freely for your own prototypes and experiments.

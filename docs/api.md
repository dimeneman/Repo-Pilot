# RepoPilot API Reference Documentation

**Base URL**: `/api/v1`  
**Interactive Docs**: `/docs` (Swagger UI) & `/redoc` (ReDoc)

---

## 1. Repositories API

### Ingest Repository
Start asynchronous ingestion of a GitHub repository.

- **URL**: `POST /repos/ingest`
- **Status**: `202 Accepted`
- **Request Body**:
  ```json
  {
    "url": "https://github.com/fastapi/fastapi",
    "branch": "master"
  }
  ```
- **Response**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "url": "https://github.com/fastapi/fastapi",
    "name": "fastapi",
    "owner": "fastapi",
    "status": "pending",
    "file_count": 0,
    "chunk_count": 0,
    "language_stats": null,
    "description": null,
    "error_message": null,
    "last_indexed_at": null,
    "created_at": "2026-10-29T18:00:00Z",
    "updated_at": "2026-10-29T18:00:00Z"
  }
  ```

---

### List Repositories
Retrieve all tracked repositories with pagination.

- **URL**: `GET /repos?skip=0&limit=20`
- **Response**:
  ```json
  {
    "repositories": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "url": "https://github.com/fastapi/fastapi",
        "name": "fastapi",
        "owner": "fastapi",
        "status": "ready",
        "file_count": 128,
        "chunk_count": 482,
        "language_stats": { "Python": 120, "Markdown": 8 }
      }
    ],
    "total": 1
  }
  ```

---

### Ingestion Status
Poll the progress of an indexing job.

- **URL**: `GET /repos/{repo_id}/status`
- **Response**:
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "indexing",
    "progress": 0.75,
    "file_count": 128,
    "chunk_count": 482,
    "step_description": "Generating vector embeddings for 482 chunks"
  }
  ```

---

### List Repository Files
Retrieve the list of parsed source and documentation files.

- **URL**: `GET /repos/{repo_id}/files`
- **Response**:
  ```json
  [
    {
      "id": "a1b2c3d4-...",
      "path": "fastapi/applications.py",
      "language": "Python",
      "size": 4200,
      "line_count": 180
    }
  ]
  ```

---

### Re-index Repository
Trigger re-chunking and re-embedding.

- **URL**: `POST /repos/{repo_id}/reindex`
- **Status**: `202 Accepted`

---

### Delete Repository
Purge repository metadata, source files, chunks, and vector store points.

- **URL**: `DELETE /repos/{repo_id}`
- **Status**: `204 No Content`

---

### Repository Architecture Summary
Generate an architectural review with Mermaid diagram.

- **URL**: `GET /repos/{repo_id}/summary`
- **Response**:
  ```json
  {
    "answer": "### Architecture Summary...",
    "mode": "summary",
    "tech_stack": ["Python", "FastAPI", "Pydantic"],
    "file_tree_preview": ["app/main.py", "app/api/..."],
    "mermaid_diagram": "graph TD\n  Client --> Gateway\n  Gateway --> DB"
  }
  ```

---

## 2. Chat / RAG API

### Query Codebase
Ask a natural language question with grounded citations.

- **URL**: `POST /chat`
- **Request Body**:
  ```json
  {
    "repo_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "question": "Where is OAuth2 authentication implemented?",
    "mode": "chat",
    "include_sources": true,
    "top_k": 8
  }
  ```
- **Response**:
  ```json
  {
    "answer": "Authentication is implemented in `fastapi/security/oauth2.py` via `OAuth2PasswordBearer`...",
    "sources": [
      {
        "file_path": "fastapi/security/oauth2.py",
        "start_line": 140,
        "end_line": 175,
        "snippet": "class OAuth2PasswordBearer(OAuth2):\n    def __init__(...):",
        "relevance_score": 0.89,
        "language": "Python",
        "chunk_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
      }
    ],
    "mode": "chat",
    "query_id": "8c2eeb4d-...",
    "model_used": "gemini-2.5-flash",
    "processing_time_ms": 780,
    "mermaid_diagram": null
  }
  ```

---

### Chat History
Fetch historical queries and answers for a repository.

- **URL**: `GET /chat/history/{repo_id}?skip=0&limit=20`

---

## 3. Sources API

### Source Chunk Detail
Fetch surrounding lines and context for a specific chunk.

- **URL**: `GET /sources/{chunk_id}`
- **Response**:
  ```json
  {
    "chunk": {
      "id": "...",
      "start_line": 40,
      "end_line": 80,
      "content": "..."
    },
    "file": {
      "path": "app/core/security.py"
    },
    "surrounding_chunks": []
  }
  ```

---

## 4. System & Health API

### Health Check
- **URL**: `GET /health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "vector_store": "connected",
    "embedding_model": "all-MiniLM-L6-v2"
  }
  ```


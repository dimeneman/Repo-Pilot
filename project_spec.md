# GitHub Repository RAG Assistant

## 1. Project Goal
Build a Retrieval-Augmented Generation (RAG) application that can analyze a GitHub repository and answer questions about the codebase with source citations.

## 2. Core Use Case
The user provides a GitHub repository URL. The system clones the repository, parses the files, chunks the content, creates embeddings, stores them in a vector database, and lets the user ask natural-language questions about the repository.

## 3. Primary User Flows
1. User submits a GitHub repository URL.
2. System ingests the repository in the background.
3. System indexes code and documents.
4. User asks questions about the repository.
5. System retrieves relevant chunks and generates answers with citations.
6. User sees answers along with source file names and line ranges.

## 4. Functional Requirements

### 4.1 Repository Ingestion
- Accept GitHub repository URL.
- Clone the repository or download it as ZIP.
- Ignore irrelevant folders and files such as:
  - `.git`
  - `node_modules`
  - `dist`
  - `build`
  - `venv`
  - `__pycache__`
- Detect supported file types.
- Store ingestion status.

### 4.2 File Parsing and Chunking
- Read source files and documents.
- Split files into meaningful chunks.
- Preserve metadata for each chunk:
  - repository name
  - file path
  - language
  - chunk index
  - start line
  - end line
- Support code-aware chunking where possible.

### 4.3 Embedding and Indexing
- Generate embeddings for each chunk.
- Store embeddings in a vector database.
- Store chunk metadata in a relational database.
- Support re-indexing when repository changes.

### 4.4 Question Answering
- Accept user questions about the repository.
- Retrieve relevant chunks from vector DB.
- Optionally rerank results.
- Send retrieved context to the LLM.
- Return a grounded answer.
- Include citations with:
  - file name
  - line range
  - matched snippet

### 4.5 Source Citations
- Every answer should show sources.
- Citations should be traceable to the repository.
- Display at least:
  - file path
  - line numbers
  - short snippet

### 4.6 Repository Summary
- Generate a high-level summary of the repository.
- Summarize:
  - tech stack
  - folder structure
  - main modules
  - APIs
  - data flow

## 5. Non-Functional Requirements
- Fast response time for chat queries.
- Background processing for large repositories.
- Clean modular architecture.
- Easy to extend with more file types.
- Dockerized deployment.
- Production-style logging and error handling.

## 6. Recommended Tech Stack

### 6.1 Frontend
- Next.js or React
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Query or SWR

### 6.2 Backend
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy or SQLModel
- Alembic

### 6.3 Repository Processing
- GitPython or git CLI
- pathlib
- zipfile
- requests

### 6.4 Chunking
- tree-sitter for code-aware parsing
- LangChain text splitters or custom chunker
- token-aware splitting if needed

### 6.5 Background Jobs
- Celery + Redis
- or RQ + Redis for a simpler setup

### 6.6 Embeddings
- sentence-transformers locally (all-MiniLM-L6-v2)

### 6.7 Vector Database
- Qdrant for stronger production value
- or Chroma for faster MVP
- or pgvector if keeping everything in PostgreSQL

### 6.8 Metadata Database
- PostgreSQL

### 6.9 Object Storage
- S3
- or MinIO for local development
- or filesystem storage for MVP

### 6.10 LLM
- Gemini 2.5 Flash (Google Gemini)

### 6.11 Orchestration
- LangChain
- or LangGraph for an agentic workflow

### 6.12 Auth
- JWT authentication
- optional GitHub OAuth

### 6.13 Monitoring
- logging with Loguru or standard logging
- Sentry for errors
- Langfuse or OpenTelemetry for tracing

### 6.14 Testing
- pytest
- httpx
- pytest-asyncio
- unittest.mock

### 6.15 Deployment
- Docker
- Docker Compose
- GitHub Actions
- Vercel for frontend
- Render / Railway / Fly.io for backend

## 7. Core Components

### 7.1 Frontend UI
Responsibilities:
- repository upload screen
- question/chat screen
- indexing status screen
- citations panel
- repository summary screen

### 7.2 API Layer
Responsibilities:
- receive repository ingestion requests
- receive chat requests
- expose status and source endpoints
- validate inputs
- return structured outputs

### 7.3 Ingestion Service
Responsibilities:
- clone/download repository
- clean file tree
- detect file types
- prepare content for chunking

### 7.4 Chunking Service
Responsibilities:
- split files into chunks
- preserve line ranges
- attach metadata
- support code/document specific rules

### 7.5 Embedding Service
Responsibilities:
- create vector embeddings for each chunk
- prepare vectors for storage and retrieval

### 7.6 Vector Retrieval Service
Responsibilities:
- semantic search over chunks
- return top-k relevant chunks
- optionally rerank results

### 7.7 Citation Resolver
Responsibilities:
- map retrieved chunks to file names
- map chunks to line ranges
- produce citation-ready source output

### 7.8 Answer Generation Service
Responsibilities:
- build prompt with retrieved context
- generate concise answer
- include source-backed response

### 7.9 Job Queue / Worker
Responsibilities:
- run ingestion asynchronously
- handle large repository processing
- update job status

### 7.10 Storage Layer
Responsibilities:
- store metadata
- store embeddings
- store raw repo artifacts
- store indexing state and chat history

## 8. Suggested API Endpoints
- `POST /repos/ingest`
- `GET /repos/{repo_id}/status`
- `POST /chat`
- `GET /repos/{repo_id}/summary`
- `GET /sources/{chunk_id}`
- `GET /repos/{repo_id}/files`
- `GET /health`

## 9. Suggested Data Models

### 9.1 Repository
- id
- url
- name
- owner
- status
- created_at
- updated_at

### 9.2 File
- id
- repo_id
- path
- language
- size
- checksum

### 9.3 Chunk
- id
- file_id
- repo_id
- chunk_index
- start_line
- end_line
- content
- embedding_id

### 9.4 Query
- id
- repo_id
- user_question
- response_text
- created_at

### 9.5 Job
- id
- repo_id
- job_type
- status
- progress
- error_message
- started_at
- completed_at

## 10. Ingestion Pipeline
1. User submits repo URL.
2. Backend validates URL.
3. Repo is cloned or downloaded.
4. Unwanted files are removed from processing.
5. Files are parsed.
6. Content is chunked.
7. Embeddings are generated.
8. Chunks are stored in vector DB.
9. Metadata is stored in PostgreSQL.
10. Job status is marked complete.

## 11. Question Answering Pipeline
1. User asks a question.
2. Query is embedded.
3. Vector DB returns relevant chunks.
4. Citation Resolver formats file and line references.
5. LLM generates answer using retrieved context.
6. Response is returned with sources.

## 12. Resume-Worthy Enhancements
- GitHub OAuth login
- multi-repo support
- chat history per repository
- repo summary generation
- API discovery mode
- bug-finding mode
- README generation
- Mermaid architecture generation
- reranking layer
- hybrid retrieval with keyword + semantic search
- source citations with line numbers

## 13. MVP Scope
Build first:
- repo ingestion
- file parsing
- chunking
- embeddings
- vector search
- chat Q&A
- citations
- FastAPI backend
- simple frontend
- Docker

## 14. Nice-to-Have Scope
Add later:
- background queue
- auth
- repo summaries
- bug detection
- API docs generation
- advanced monitoring
- tests
- deployment pipeline

## 15. Output Format for Answers
Each answer should return:
- final natural-language answer
- source file list
- line ranges
- short supporting snippets
- confidence or relevance score if available

## 16. Final Product Vision
The final product should feel like:
- AI assistant for codebases
- a developer assistant for understanding GitHub repositories
- a searchable, source-grounded repository intelligence platform
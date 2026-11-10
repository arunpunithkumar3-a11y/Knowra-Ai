# 🧠 Knowra: Enterprise Multi-Tenant Agentic RAG Platform

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20Workflows-1C3C3C.svg?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Hybrid%20Vector%20DB-DC2626.svg?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async%20SQLModel-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-Async%20Task%20Queue-37814A.svg?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Tests](https://img.shields.io/badge/Tests-123%20Passed%20(100%25)-brightgreen.svg?style=for-the-badge)](src/tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <strong>Production-ready, multi-tenant autonomous AI knowledge assistant powered by LangGraph ReAct agents, hybrid dense-sparse vector retrieval, cross-encoder reranking, sentence-window expansion, dual-layer guardrails, and asynchronous ingestion pipelines.</strong>
</p>

[System Architecture](#-system-architecture) •
[Core Features](#-core-engineering-features) •
[Quickstart](#-quickstart-guide) •
[API Reference](#-api-specification--endpoints) •
[Benchmarking & Testing](#-testing--evaluation) •
[Configuration](#-environment-configuration)

</div>

---

## 🌟 Overview

**Knowra** is a high-throughput, enterprise-grade Retrieval-Augmented Generation (RAG) platform architected to eliminate the core failure modes of conventional RAG systems:
- **Lost-in-the-Middle Context Dilution**: Solved via a **Hierarchical Sentence-Window + Parent-Child Retriever** that searches against granular child chunks (75 tokens) while reconstructing surrounding parent window context ($\pm 2$ parent windows) on the fly directly from Qdrant vector metadata.
- **Lexical vs. Semantic Recall Gaps**: Solved via **Hybrid Retrieval** combining **NVIDIA NIM Dense Embeddings** (`nv-embedqa-e5-v5`, 2048 dimensions) and **BM25 Sparse Vectors** (`FastEmbedSparse`), fused with **Reciprocal Rank Fusion (RRF)** and cross-encoder re-scored via **NVIDIA Llama-3.2 Reranker**.
- **Ingestion Latency & Server Blocking**: Solved via an **Asynchronous Celery + Redis** task distribution pipeline that processes and embeds complex multi-page PDF documents off the critical HTTP thread.
- **Unbounded Agent Loops & Prompt Injection**: Solved via dual-tier guardrails (an ultra-fast sub-20ms local ML safety classifier paired with **NVIDIA Nemotron Content Safety Guard**) and hard loop ceilings on LangGraph tool execution.
- **Tenant Data Bleed**: Enforced strictly through tenant IDs (`business_id`) validated across database row policies and vector store payload filters.

---

## 🏛️ System Architecture

Knowra is organized into decoupled services communicating asynchronously across PostgreSQL, Redis, and Qdrant.

```mermaid
flowchart TD
    subgraph Clients["Clients & Integration"]
        Browser["Authenticated Client (Dashboard)"]
        Widget["Embeddable Website Widget"]
    end

    subgraph Gateway["API Gateway Layer (FastAPI)"]
        Router["FastAPI Application Router (/api/v1)"]
        AuthMid["JWT Auth & Argon2 Verification"]
        TenantMid["Tenant Scoping & Access Control"]
        RedisRevoke[("Redis Token Blacklist")]
    end

    subgraph AsyncIngestion["Asynchronous Ingestion Engine"]
        DocAPI["Document Upload Endpoint"]
        RedisBroker[("Redis Message Broker")]
        CeleryWorker["Celery Distributed Workers"]
        PDFParser["pypdf Text Extraction"]
        Chunker["Parent-Child Hierarchical Splitter"]
        DenseModel["NVIDIA nv-embedqa-e5-v5 (2048-dim)"]
        SparseModel["FastEmbed BM25 Sparse Vectorizer"]
        QdrantStore[("Qdrant Hybrid Vector Store")]
    end

    subgraph AgenticRAG["LangGraph Stateful Agentic Engine"]
        ChatAPI["SSE Streaming Chat Endpoint"]
        Checkpointer[("PostgreSQL State Checkpointer")]
        SafetyGate{"Dual-Tier Safety Guardrail"}
        ClassifierML["Local ML Safety Classifier (<20ms)"]
        NemotronGuard["NVIDIA Nemotron Guardrail"]
        ReActAgent["LangGraph ReAct Agent (Llama-3.3-70B)"]
        KBTool["search_knowledge_base Tool"]
        
        subgraph HybridSearch["Hybrid Search & Reranking"]
            QdrantDense["Dense Cosine Search (k=4)"]
            QdrantSparse["BM25 Sparse Search (k=3)"]
            RRF["Reciprocal Rank Fusion (RRF k=60)"]
            Rerank["NVIDIA Llama-3.2 QA Reranker (top_n=3)"]
            WindowReconstruct["Stateless Parent-Window Reconstruction"]
        end

        ThinkFilter["Streaming ThinkFilter (Regex SSE)"]
    end

    subgraph AnalyticsEngine["Analytics & Question Mining"]
        RelevanceML["Scikit-Learn Query Classifier"]
        QuestionRepo[("PostgreSQL Questions Table")]
        ClusterChain["Two-Stage LLM Clustering & Topic Insight Synthesis"]
    end

    Browser --> Router
    Widget --> Router
    Router --> AuthMid
    AuthMid <--> RedisRevoke
    AuthMid --> TenantMid

    TenantMid --> DocAPI
    DocAPI --> RedisBroker
    RedisBroker --> CeleryWorker
    CeleryWorker --> PDFParser --> Chunker
    Chunker --> DenseModel & SparseModel
    DenseModel & SparseModel --> QdrantStore

    TenantMid --> ChatAPI
    ChatAPI --> ReActAgent
    ReActAgent <--> Checkpointer
    ChatAPI --> SafetyGate
    SafetyGate --> ClassifierML
    SafetyGate --> NemotronGuard
    SafetyGate -->|Safe| ReActAgent
    SafetyGate -->|Unsafe| ThinkFilter

    ReActAgent -->|Invoke Tool| KBTool
    KBTool --> QdrantDense & QdrantSparse
    QdrantStore -.-> QdrantDense & QdrantSparse
    QdrantDense & QdrantSparse --> RRF --> Rerank --> WindowReconstruct
    WindowReconstruct --> KBTool
    KBTool --> ReActAgent

    ReActAgent --> ThinkFilter
    ThinkFilter -->|text/event-stream| Browser
    ThinkFilter -->|text/event-stream| Widget

    ChatAPI -.-> RelevanceML
    RelevanceML -->|Relevant Inquiries| QuestionRepo
    QuestionRepo --> ClusterChain
```

---

## 🔄 Sequence Workflows

### 1. Document Ingestion Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Business Admin
    participant API as FastAPI Gateway
    participant DB as PostgreSQL
    participant Redis as Redis Broker
    participant Celery as Celery Worker
    participant Qdrant as Qdrant Vector DB

    Admin->>API: POST /api/v1/create_document/{biz_id} (PDF File)
    API->>API: Validate PDF, MIME, Page Count (≤10 pages)
    API->>DB: Create Document record (status = PENDING)
    API->>Redis: Enqueue ingestion task (document_id, business_id)
    API-->>Admin: 202 Accepted (document_id, task_id)

    Redis->>Celery: Dequeue ingestion job
    Celery->>DB: Update status to PROCESSING
    Celery->>Celery: Extract clean text via pypdf
    Celery->>Celery: Split parents (350 tokens) with ±2 window context
    Celery->>Celery: Split child chunks (75 tokens) referencing parent window
    Celery->>Qdrant: Index child vectors (NVIDIA Dense + BM25 Sparse + Window Metadata)
    Celery->>DB: Update status to COMPLETED
```

### 2. Conversational Agent Streaming & Retrieval

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / End User
    participant Stream as SSE Controller
    participant Safety as Safety Classifier & Guard
    participant Agent as LangGraph ReAct Agent
    participant KB as Knowledge Base Retriever
    participant Rerank as NVIDIA Reranker
    participant LLM as Llama-3.3-70B

    User->>Stream: POST /api/v1/knowra/chat/{biz_id} (message, thread_id)
    Stream->>Safety: Check query safety
    alt Unsafe or Prompt Injection
        Safety-->>Stream: Refusal / Safety Response
        Stream-->>User: data: {"type": "content", "content": "Refusal..."}
    else Query is Safe
        Safety->>Agent: Run ReAct step with message history
        Agent->>LLM: Evaluate user query
        alt Agent requires context
            LLM-->>Agent: tool_call: search_knowledge_base(query)
            Agent->>KB: Hybrid query (Dense + BM25)
            KB->>Rerank: Top candidate windows
            Rerank-->>KB: Scored & ranked windows (top_n=3)
            KB-->>Agent: Formatted context passages
            Agent->>LLM: Synthesize grounded response
        end
        LLM-->>Agent: Stream token chunks
        Agent->>Stream: Filter internal reasoning (<think> tags)
        Stream-->>User: Server-Sent Events (SSE chunks)
        Stream-->>User: data: [DONE]
    end
```

---

## ✨ Core Engineering Features

### 1. Hybrid Sentence-Window + Parent-Child Retrieval
Traditional chunking suffers from a severe trade-off: large chunks contain necessary background context but produce diluted embeddings, while small chunks produce precise embeddings but fail to give the LLM enough context to answer comprehensively.

Knowra implements a **Dual-Tier Sentence-Window Architecture**:
- **Child Chunks (75 tokens, 20 overlap)**: Used exclusively for vector matching. These small semantic units ensure high-fidelity cosine similarity against specific facts.
- **Parent Window Context ($\pm 2$ parent chunks, 350 tokens each)**: During chunking, neighboring parent chunks are concatenated into a sliding window string stored directly in the child document payload inside Qdrant (`parent_window`).
- **Stateless Re-constitution**: No secondary database query or document store lookup is required at query time. The retriever instantly reconstructs the enriched multi-paragraph window directly from vector metadata.
- **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k + \text{rank}_m(d)} \quad (k = 60)$$
- **Cross-Encoder Reranking**: Candidate passages are scored by the **NVIDIA Llama-3.2 Reranker** (`nvidia/llama-3.2-nv-rerankqa-1b-v2`), preserving only the most semantically relevant contexts for generation.

### 2. Autonomous LangGraph ReAct Agent
- **Stateful Thread Checkpointing**: Built with LangGraph's `StateGraph` and backed by `AsyncPostgresSaver`. Multi-turn conversations retain conversation state, tool calls, and document citations seamlessly across network disconnections.
- **Dual-Tier Safety Guardrail**:
  1. *Tier 1 (Sub-20ms ML Classifier)*: A vectorized Scikit-Learn pipeline (`safety_classifier_pipeline.pkl`) intercepts prompt injections, adversarial queries, and out-of-scope interactions before any LLM execution occurs.
  2. *Tier 2 (NVIDIA Nemotron Safety)*: Unsafe inputs are routed through `nvidia/llama-3.1-nemotron-safety-guard-8b-v3` to formulate compliant, standardized refusals.
- **Streaming ThinkFilter**: Meta Llama-3.3-70B emits chain-of-thought `<think>...</think>` tags during internal reasoning. Knowra's custom `ThinkFilter` processes streaming tokens in real time, stripping internal thought blocks dynamically without stalling token delivery over Server-Sent Events (`text/event-stream`).
- **Loop Prevention**: Implements a strict hard ceiling of at most 3 tool invocations per conversational turn, preventing runaway agent loops and API credit exhaustion.

### 3. Decoupled Asynchronous Processing (Celery + Redis)
- Document uploading and parsing is decoupled from the web gateway. Large multi-page PDF documents are ingested, tokenized, and embedded via background **Celery workers** using **Redis** as a distributed message broker.
- Supports lifecycle state transitions (`pending` $\rightarrow$ `processing` $\rightarrow$ `completed` / `failed`) with real-time status query endpoints.

### 4. Multi-Tenant Isolation & Enterprise Security
- **Tenant Boundaries**: Complete isolation across users and businesses. Queries and vector searches are sandboxed using strict metadata filters (`business_id = <uuid>`), guaranteeing zero data leakage between different organizations.
- **Argon2 Password Hashing**: Cryptographic password hashing using `passlib` with Argon2 bindings.
- **JWT Authentication & Redis Revocation**: Short-lived access tokens (1 hour) paired with long-lived refresh tokens (7 days). Token IDs (`jti`) are validated against an in-memory **Redis revocation blacklist**, enabling instant global logout.
- **Embeddable Website Widget**: Dedicated public widget endpoints (`/api/v1/widget/{public_key}`) allow customers to embed chat assistants into third-party sites using public API keys while safeguarding administrative routes.

### 5. Automated Analytics & Question Clustering
- **Relevance Classifier**: Real-time evaluation of all incoming end-user queries using a pre-trained ML classifier (`question_relevance_pipeline.pkl`). Genuine business inquiries are automatically persisted to PostgreSQL.
- **Two-Stage Topic Mining**:
  1. *Stage 1 (Clustering)*: Groups logged customer questions into semantically distinct topic clusters using LLM structured output.
  2. *Stage 2 (Executive Summarization)*: Synthesizes clustered questions into high-level business insights and actionable operational recommendations for business owners.

---

## 📊 Testing & Evaluation

Knowra features a **123-test automated test suite** covering unit, integration, and security layers, alongside a **DeepEval RAG Benchmarking Suite**.

```bash
# Run the complete test suite (123 tests)
pytest src/tests -v -p no:deepeval
```

### Test Coverage Highlights
| Test Suite | File | Tests | Focus Area |
| :--- | :--- | :---: | :--- |
| **Authentication API** | `test_api_auth.py` | 14 | Signup, Argon2 hashing, JWT refresh, Redis token blacklist, password reset |
| **Business Management API** | `test_api_business.py` | 10 | Tenant registration, access boundaries, public keys, widget metadata |
| **Chat & Agent Streaming API** | `test_api_chat.py` | 7 | SSE streaming, thread persistence, widget chat, question logging |
| **Document Ingestion API** | `test_api_document.py` | 8 | PDF upload validation, tenant isolation, embedding status lifecycle |
| **Feature Analytics API** | `test_api_feature.py` | 6 | Total questions calculation, bounds checking, topic clustering |
| **Business Service** | `test_business_service.py` | 21 | CRUD operations, relationship queries, ownership checks |
| **Document Service** | `test_document_service.py` | 14 | Document CRUD, chunk association, embedding status updates |
| **Question Service** | `test_question_service.py` | 9 | Question persistence, pagination, business range filtering |
| **User Service** | `test_user_service.py` | 13 | User CRUD, email uniqueness, password hashing verification |
| **Security Utilities** | `test_security.py` | 8 | Token generation, JTI validation, expired token rejection, URL-safe tokens |
| **App & Exception Handling** | `test_main_app.py`, `test_exceptions.py`| 13 | Global exception handlers, OpenAPI schema integrity, health checks |
| **Total** | | **123** | **100% Pass Rate** |

### DeepEval RAG Benchmarks (`src/evals/`)
The evaluation pipeline benchmarks retrieval accuracy and generation quality against a verified golden dataset (`golden_dataset.json`):
- **Contextual Recall ($\ge 0.70$)**: Measures whether all ground truth answers are contained in retrieved parent windows.
- **Contextual Precision ($\ge 0.70$)**: Measures whether retrieved chunks are ranked in optimal relevance order.
- **Faithfulness**: Validates that LLM responses do not hallucinate claims absent from source documents.
- **Answer Relevancy**: Assesses alignment of final responses with user queries.

---

## 📂 Project Structure

```text
Knowra/
├── alembic/                         # Database schema migrations
│   ├── versions/
│   │   ├── 001_initial_migration.py # Core schema (users, businesses, documents)
│   │   └── 002_add_questions_table.py # Analytics questions table
│   └── env.py                       # Async SQLAlchemy migration configuration
├── src/
│   ├── analyse/                     # Business Intelligence & Topic Mining
│   │   ├── cluster.py               # Two-stage question clustering orchestrator
│   │   └── prompt.py                # Few-shot prompts & Pydantic structured output chains
│   ├── api/                         # FastAPI Route Controllers
│   │   ├── auth.py                  # Signup, login, refresh, logout, password reset
│   │   ├── business.py              # Tenant profile creation & public key resolution
│   │   ├── chat.py                  # Authenticated & widget SSE streaming endpoints
│   │   ├── document.py              # PDF upload, listing, deletion, status checks
│   │   └── feature.py               # Question counts & topic clustering endpoints
│   ├── core/                        # Infrastructure & Security Layer
│   │   ├── dependency.py            # FastAPI dependencies (JWT token verification)
│   │   ├── main.py                  # Async PostgreSQL engine & session factory
│   │   ├── password.py              # Argon2 password hashing & verification
│   │   ├── postgres.py              # LangGraph AsyncPostgresSaver checkpointer pool
│   │   ├── redis.py                 # Redis connection pool & token blacklist store
│   │   └── security.py              # JWT encoding/decoding & URL-safe token utils
│   ├── evals/                       # RAG Benchmarking Suite
│   │   ├── data/                    # Golden evaluation datasets & sample test PDFs
│   │   ├── generator_eval.py        # Faithfulness & Answer Relevancy tests
│   │   ├── pipeline_evals.py        # End-to-end evaluation runner
│   │   ├── retriever.py             # Evaluation retrieval wrapper
│   │   └── retriever_eval.py        # Contextual Precision & Recall benchmark
│   ├── knowra/                      # Core RAG & Agentic Engine
│   │   ├── agent/                   # LangGraph ReAct Implementation
│   │   │   ├── graph.py             # StateGraph definition & PostgreSQL compilation
│   │   │   ├── nodes.py             # Agent, Safety, Guard, and Tool routing nodes
│   │   │   ├── state.py             # AgentState typed dictionary definition
│   │   │   ├── stream.py            # SSE stream generator & ThinkFilter
│   │   │   └── tools.py             # search_knowledge_base LangChain tool
│   │   ├── guardrails/              # NeMo Guardrails configuration & Colang rails
│   │   ├── pipeline.py              # Hybrid RAG orchestrator & reranking pipeline
│   │   ├── prompt.py                # System prompt templates & few-shot examples
│   │   └── retrievers.py            # Sentence-window parent-child hybrid retriever
│   ├── models/                      # SQLModel ORM & Pydantic Schemas
│   │   ├── analyse_schemas.py       # Topic clustering request/response models
│   │   ├── auth_schemas.py          # User registration, login, token schemas
│   │   ├── business_schemas.py      # Business creation & public profile models
│   │   ├── chat_schemas.py          # Chat request & conversation thread models
│   │   ├── database.py              # SQLModel tables (User, Business, Documents, Questions)
│   │   └── document_schemas.py      # Document upload & embedding status models
│   ├── services/                    # Business Logic Layer
│   │   ├── business.py              # Tenant management service
│   │   ├── document.py              # Document management service
│   │   ├── questions.py             # Query repository & pagination service
│   │   └── user.py                  # User management service
│   ├── tests/                       # Automated Test Suite (123 Tests)
│   ├── celery_tasks.py              # Celery background tasks (PDF ingestion, email)
│   ├── client.py                    # Qdrant client singleton
│   ├── config.py                    # Pydantic Settings configuration & lazy models
│   ├── exceptions.py                # Unified application exception hierarchy
│   ├── mail.py                      # FastMail SMTP email notification integration
│   └── main.py                      # FastAPI initialization, CORS, global exception handlers
├── .env.example                     # Environment variables configuration template
├── alembic.ini                      # Alembic CLI configuration
├── LICENSE                          # MIT License
├── main.py                          # Application entry point
├── question_relevance_pipeline.pkl  # Trained ML pipeline for query relevance
├── safety_classifier_pipeline.pkl   # Trained ML pipeline for content safety
├── requirements.txt                 # Production dependencies
└── start.sh                         # Linux deployment entrypoint script
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python**: Version `3.11`, `3.12`, or `3.13`
- **PostgreSQL**: Version `14+` (with asyncpg support)
- **Redis**: Version `6+` (local or hosted via Upstash)
- **Qdrant**: Version `1.8+` (local container or Qdrant Cloud)
- **API Keys**: NVIDIA NIM (for dense embeddings, reranker, and LLM) and/or Groq

### 2. Clone & Environment Setup

```bash
# Clone the repository
git clone https://github.com/arunpunithkumar3-a11y/Knowra-Ai.git
cd Knowra-Ai

# Create and activate virtual environment
python -m venv venv

# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file and customize your credentials:

```bash
cp .env.example .env
```

Ensure the following critical variables are configured in `.env`:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/knowra
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

JWT_SECRET=super_secret_production_key_change_me_now
JWT_ALGORITHM=HS256

NVIDIA_API_KEY=nvapi-your_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5
RERANKER_MODEL=nvidia/llama-3.2-nv-rerankqa-1b-v2
LLM_MODEL=meta/llama-3.3-70b-instruct
```

### 4. Database Initialization

Execute the Alembic migrations to construct the database schema:

```bash
alembic upgrade head
```

### 5. Launch Knowra

Open two terminal windows to run both the API Gateway and the Asynchronous Worker:

**Terminal 1: FastAPI Gateway**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2: Celery Background Ingestion Worker**
```bash
# On Linux / macOS:
celery -A src.celery_tasks.celery_app worker --loglevel=info

# On Windows:
celery -A src.celery_tasks.celery_app worker --loglevel=info --pool=solo
```

### 6. Verify Services
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 API Specification & Endpoints

### System & Health
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/health` | None | Returns server health status, timestamp, and version |
| `GET` | `/` | None | Service discovery and welcome payload |

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/signup` | None | Register new user account with Argon2 password hashing |
| `POST` | `/api/v1/auth/login` | None | Authenticate credentials; returns access & refresh tokens |
| `POST` | `/api/v1/auth/refresh` | None | Exchange valid refresh token for fresh access token |
| `POST` | `/api/v1/auth/logout` | JWT | Invalidate current access and refresh tokens via Redis |
| `POST` | `/api/v1/auth/password-reset-request` | None | Send password reset token to user email |
| `POST` | `/api/v1/auth/password-reset-confirm/{token}` | None | Confirm password reset with new credentials |

### Tenant / Business Management (`/api/v1`)
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/business` | JWT | Create a new tenant profile (generates unique `public_key`) |
| `GET` | `/api/v1/business/{business_id}` | JWT | Retrieve business details by UUID |
| `GET` | `/api/v1/business` | JWT | List all business profiles owned by authenticated user |
| `PUT` | `/api/v1/business/{business_id}` | JWT | Update business metadata (name, description, website) |
| `DELETE`| `/api/v1/business/{business_id}` | JWT | Delete business and cascade documents/vectors |
| `GET` | `/api/v1/widget/business/{public_key}` | None | Public metadata endpoint for frontend widget initialization |

### Document Management & Ingestion (`/api/v1`)
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/create_document/{biz_id}` | JWT | Upload PDF document (≤10 pages) for async Celery ingestion |
| `GET` | `/api/v1/document/{document_id}` | JWT | Get document details and current `embedding_status` |
| `GET` | `/api/v1/documents/{business_id}` | JWT | List all documents belonging to a business |
| `DELETE`| `/api/v1/document/{document_id}` | JWT | Delete document from PostgreSQL and remove vectors from Qdrant |

### Conversational Agent (`/api/v1`)
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/knowra/chat/{business_id}` | JWT | Authenticated multi-turn agent chat with SSE streaming |
| `POST` | `/api/v1/widget/{public_key}` | None | Public embeddable widget chat with SSE streaming |

### Analytics & Topic Mining (`/api/v1`)
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/feature/questions/{business_id}` | JWT | Fetch total count of customer questions logged |
| `POST` | `/api/v1/feature/cluster/{business_id}` | JWT | Execute two-stage topic clustering and insight extraction |

---

## 💻 API Usage Examples

### 1. Authenticate & Obtain Tokens
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "message": "Login successfully",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "uid": "b78b0f92-5643-4f9a-9e12-32a249c5efba",
    "email": "admin@example.com",
    "user_name": "Admin"
  }
}
```

### 2. Asynchronously Ingest a Knowledge Base Document
```bash
curl -X POST "http://localhost:8000/api/v1/create_document/3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@knowledge_base.pdf;type=application/pdf"
```

**Response:**
```json
{
  "message": "Document uploaded successfully and processing has started",
  "document_id": "8a32a67e-bf33-4f51-b0db-64efb645b23d",
  "status": "pending"
}
```

### 3. Stream Conversational Agent Response (SSE)
```bash
curl -N -X POST "http://localhost:8000/api/v1/knowra/chat/3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is our corporate refund policy for enterprise plans?",
    "thread_id": "thread-user-session-42"
  }'
```

**Stream Output:**
```text
data: {"type": "content", "content": "According to"}

data: {"type": "content", "content": " our enterprise terms, refunds are"}

data: {"type": "content", "content": " issued within 30 days of billing."}

data: [DONE]
```

### 4. Synthesize Topic Clusters & Insights
```bash
curl -X POST "http://localhost:8000/api/v1/feature/cluster/3fa85f64-5717-4562-b3fc-2c963f66afa6?start=1&end=50" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Response:**
```json
{
  "message": [
    {
      "topic_name": "Pricing & Invoicing Queries",
      "insight": "Customers frequently inquire about annual versus monthly billing discounts and invoice generation timelines."
    },
    {
      "topic_name": "Integration & API Limits",
      "insight": "High volume of requests seeking webhook documentation and rate limit escalation procedures."
    }
  ]
}
```

---

## ⚙️ Environment Configuration

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `DATABASE_URL` | String | *Required* | Async PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | String | `redis://localhost:6379/0` | Redis connection URL for Celery broker & token blacklist |
| `JWT_SECRET` | String | *Required* | Secret key for signing JWT tokens ($\ge 32$ chars) |
| `JWT_ALGORITHM` | String | `HS256` | JWT signing algorithm |
| `QDRANT_URL` | String | `http://localhost:6333` | Qdrant vector database URL |
| `QDRANT_API_KEY` | String | `""` | Qdrant API key (required for Qdrant Cloud) |
| `NVIDIA_API_KEY` | String | *Required* | NVIDIA NIM API key (`nvapi-...`) |
| `GROQ_API_KEY` | String | `""` | Groq API key for alternative LLM inference |
| `NVIDIA_BASE_URL` | String | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM base URL endpoint |
| `EMBEDDING_MODEL` | String | `nvidia/nv-embedqa-e5-v5` | Dense vector embedding model (2048 dims) |
| `RERANKER_MODEL` | String | `nvidia/llama-3.2-nv-rerankqa-1b-v2` | Cross-encoder reranker model |
| `LLM_MODEL` | String | `meta/llama-3.3-70b-instruct` | Core generator LLM for ReAct agent |
| `JUDGE_MODEL` | String | `meta/llama-3.3-70b-instruct` | LLM judge for DeepEval benchmark evaluations |
| `PARENT_CHUNK_SIZE` | Integer | `350` | Character size for parent window chunks |
| `PARENT_CHUNK_OVERLAP` | Integer | `50` | Character overlap between adjacent parents |
| `CHILD_CHUNK_SIZE` | Integer | `75` | Character size for fine-grained child search chunks |
| `CHILD_CHUNK_OVERLAP` | Integer | `20` | Character overlap between child chunks |
| `WINDOW_SIZE` | Integer | `2` | Number of neighboring parent chunks ($\pm 2$) for window expansion |
| `DENSE_K` | Integer | `4` | Number of dense vector candidates retrieved from Qdrant |
| `SPARSE_K` | Integer | `3` | Number of sparse BM25 candidates retrieved |
| `RRF_K` | Integer | `60` | Constant smoothing parameter for Reciprocal Rank Fusion |
| `TOP_K_RERANK` | Integer | `3` | Final count of top passages delivered to the generator LLM |
| `MAIL_SERVER` | String | `""` | SMTP mail server hostname |
| `MAIL_PORT` | Integer | `587` | SMTP mail server port |
| `MAIL_USERNAME` | String | `""` | SMTP username |
| `MAIL_PASSWORD` | String | `""` | SMTP password |
| `DOMAIN` | String | `localhost:8000` | Application host domain for password reset links |

---

## 🔒 Security & Best Practices

- **Zero Unsanitized LLM Output**: The agent incorporates output filtering to scrub internal scratchpad tokens and prevents exposure of system prompts.
- **Fail-Safe Fallbacks**: If the cross-encoder reranker is temporarily unreachable, Knowra seamlessly falls back to RRF fused candidates without service interruption.
- **Stateless Vector Store**: Child vectors in Qdrant store their corresponding parent window context directly in vector payloads, eliminating multi-table joins and external key-value lookups during real-time retrieval.
- **Clean Dependency Scoping**: Fully isolated Celery worker execution guarantees that computationally heavy tokenization and embedding generation do not degrade API responsiveness.

---

## 🤝 Contributing

Contributions are welcomed. Please adhere to the following workflow:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/amazing-feature`.
3. Commit your changes: `git commit -m 'feat: implement amazing feature'`.
4. Ensure all tests pass: `pytest src/tests -v -p no:deepeval`.
5. Push to your branch: `git push origin feature/amazing-feature`.
6. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

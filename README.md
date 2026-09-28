# ReguLens — Version-Aware Regulatory Intelligence & Retrieval System

ReguLens is an AI-powered RAG system designed for Indian financial and regulatory documents (RBI, SEBI, IRDAI, etc.). It goes beyond basic vector search by understanding document structure, tracking amendments, resolving supersessions, and providing answers with precise provenance and citations.

## Key Features

1. **Idempotent Ingestion Pipeline**: Extracts text using PyMuPDF/pdfplumber, detects structural headers, and chunks text while maintaining provenance. Identical content is deduplicated automatically.
2. **Supersession Engine**: Builds a directed graph of relationships between documents (e.g., "Supersedes", "Partially Amends"). LLMs use this to correctly answer questions about the *current* state of the law vs *historical* rules.
3. **Hybrid Retrieval**: Combines semantic meaning (MongoDB Atlas Vector Search) with exact keywords (MongoDB Atlas Search) using Reciprocal Rank Fusion (RRF).
4. **Cross-Document Reasoning**: A query decomposer breaks complex temporal or comparative questions into sub-queries, retrieving evidence across multiple documents.
5. **Traceable Evidence Graph**: Every answer generated is backed by a DAG connecting the question → subqueries → documents → sections → chunks → claims → final answer.
6. **Robust Evaluation Engine**: Compares ReguLens against a Naive RAG baseline across 30+ edge cases covering single-doc, cross-doc, historical, and supersession questions.

## Technology Stack

*   **Backend**: Python, FastAPI, Pydantic, PyTest
*   **Database**: MongoDB Atlas (Vector Search, Full-Text Search, Metadata Filtering)
*   **AI/LLM**: OpenAI / Google Gemini (via Strategy Pattern for easy swapping)
*   **Frontend**: Next.js 14 (App Router), React, Tailwind CSS, Glassmorphism UI
*   **Deployment**: Docker & Docker Compose

## Setup Instructions

### 1. Prerequisites
*   Python 3.11+
*   Node.js 18+
*   MongoDB Atlas Account
*   OpenAI API Key (or Gemini API Key)

### 2. Environment Setup
Copy `.env.example` to `.env` in the root directory and fill in your keys:
```bash
cp .env.example .env
```
Ensure `MONGODB_URI` points to your Atlas cluster and `LLM_API_KEY`/`EMBEDDING_API_KEY` are set. (Note: URL-encode any special characters like `@` in the MongoDB password as `%40`).

### 3. MongoDB Indexes
Run the setup script to create regular indexes and get the JSON definitions for the Atlas Search/Vector Search indexes:
```bash
python scripts/setup_mongo_indexes.py
```
*Note: You must manually create the Vector Search and Atlas Search indexes in the MongoDB Atlas UI using the JSON provided by the script.*

### 4. Running Locally (Without Docker)
**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
The app will be available at `http://localhost:3000`.

### 5. Running with Docker Compose
```bash
docker-compose up --build
```

## Testing & Evaluation

### Run Unit & Integration Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Run Scalability Benchmark (10x Test)
Tests the system's performance at 1x, 2x, 5x, and 10x corpus sizes, generating synthetic regulatory documents to measure ingestion, indexing, and retrieval latency.
```bash
python scripts/run_scalability_benchmark.py
```

### Evaluation Dataset (30+ Edge Cases)
1. Seed the evaluation cases into the database:
   ```bash
   python scripts/seed_evaluation.py
   ```
2. Run the evaluation through the Frontend UI (`http://localhost:3000/evaluation`) or via API to compare ReguLens against the Naive RAG baseline.

## Project Structure
*   `/backend/app/`: FastAPI application, ingestion pipeline, detection engine, RAG engine
*   `/backend/tests/`: PyTest test suite
*   `/frontend/`: Next.js web application
*   `/scripts/`: Setup, synthetic data generation, benchmarking, and evaluation scripts
*   `/docker-compose.yml`: Local deployment orchestration

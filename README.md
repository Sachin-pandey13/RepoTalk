# RepoTalk 🚀
### Explainable Repository Intelligence Engine

**RepoTalk** is an intelligent repository analysis system that transforms codebases into machine-readable models using AST parsing, graph visualization, semantic vector retrieval, and autonomous local LLM agent reasoning.

---

## 🌟 Key Capabilities

- 🤖 **Autonomous Repository Agent Loop (`agents/repository_agent.py`)**: Iterative tool-calling controller (Mistral via Ollama) that plans investigations, selects structural/semantic tools, and delivers evidence-backed answers.
- 🌳 **AST Structural Code Parsing (`parser_service.py`)**: Uses `tree-sitter-python` to extract functions, classes, imports, and function call invocations.
- 📊 **Dependency & Call Graph Visualization (`call_graph_service.py`, `graph_service.py`)**: Generates interactive HTML and PNG diagrams of module import dependencies and function-to-function call chains.
- 🔍 **Hybrid Vector Retrieval (`embedding_service.py`)**: Chunks parsed code summaries, generates embeddings via `SentenceTransformers` (`all-MiniLM-L6-v2`), and indexes them in a persistent Chroma vector database.
- 💬 **Evidence-Backed Q&A**: Constructs execution paths and cites exact files and symbol definitions examined during investigation.

---

## 🏗️ System Architecture

```
                    ┌──────────────┐
                    │     User     │
                    └──────┬───────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Repository Agent│
                  │ (Ollama / LLM)  │
                  └────────┬────────┘
                           │
                    Tool Selection
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
 ┌─────────────┐    ┌─────────────┐   ┌─────────────┐
 │ Vector      │    │ AST / Symbol│   │ Call Graph  │
 │ Search      │    │ Analysis    │   │ Traversal   │
 └──────┬──────┘    └──────┬──────┘   └──────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                   Repository Evidence
                           │
                           ▼
                    Evidence-Backed
                      Explanation
```

---

## 🔌 API Endpoints

### Agentic Intelligence Endpoints
- `POST /agent/ask`: Autonomous tool-calling agent investigation (`{"repo_name": "...", "question": "..."}`)
- `GET /agent/ask?repo_name=...&question=...`: GET trigger for agent investigation

### Repository Management & Retrieval
- `POST /clone?repo_url=...`: Clone remote Git repository
- `GET /scan?repo_name=...`: Scan directory & language breakdown
- `GET /parse-repo?repo_name=...`: Run tree-sitter AST parsing across repository
- `GET /index-repo?repo_name=...`: Generate embeddings and index repository into ChromaDB
- `GET /search?query=...`: Perform semantic vector search
- `GET /visualize?repo_name=...`: Render module import dependency graph
- `GET /call-graph?repo_name=...`: Render interactive function call graph

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 2. Start Local Ollama Model
```bash
ollama run mistral
```

### 3. Run FastAPI Backend
```bash
python -m uvicorn backend.main:app --reload
```

### 4. Ask the Repository Agent
```bash
curl -X POST "http://localhost:8000/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": ".",
    "question": "How does parse_python_file work and what functions call it?"
  }'
```
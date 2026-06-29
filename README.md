# 🚀 NIFTY 50 FinBot: Hybrid Graph-Vector RAG Chatbot

FinBot is a state-of-the-art financial research assistant built using a **Hybrid Graph-Vector RAG (Retrieval-Augmented Generation)** architecture. It maps and analyzes corporate metrics, leadership connections, sector distributions, and shareholding patterns for all 50 companies listed on the **National Stock Exchange of India (NSE) NIFTY 50** index.

---

## 🏗️ Architecture Overview

FinBot combines the strengths of structured Knowledge Graphs and unstructured Vector Search:

1. **Knowledge Graph (NetworkX)**: Models structured entities (Companies, Sectors, Directors) and quantitative financial metrics (Revenue, Profit, Shareholding %) as nodes and edges.
2. **Vector Store (ChromaDB)**: Houses semantic chunks of unstructured company descriptions and Wikipedia records embedded using `BAAI/bge-small-en-v1.5`.
3. **Community Detection & Summarization (Ollama)**: Automatically clusters graph sub-sections (using Louvain communities) and generates summaries using a local LLM (`llama3.2:3b`) to answer multi-hop or macro-level financial queries.
4. **Hybrid Retrieval**: Standard semantic documents and graph-level properties are retrieved in parallel to compile a comprehensive context window for the user query.

---

## 📁 Project Structure

```text
FinBot/
├── backend/                  # FastAPI Python backend application
│   ├── main.py               # Main API endpoints (chat, history, sessions)
│   ├── retriever.py          # Hybrid retrieval logic combining Graph & Vector DB
│   ├── ingest.py             # Parses documents and creates networkx graph + vector database
│   ├── communities.py        # Detects communities and runs Ollama summaries
│   └── visualize_graph.py    # Generates interactive network HTML visualization
├── frontend/                 # Vite + React + Tailwind CSS client application
│   ├── src/                  # React source files (App.jsx chatbot layout)
│   ├── public/               # Static assets
│   └── vercel.json           # Vercel SPA rewrite routing rules
├── data/                     # Source documents and database persistence
│   ├── docs/                 # Wiki pages & raw financial data
│   ├── chromadb/             # Pre-built ChromaDB vector collection (Git-tracked)
│   └── networkx/             # Pre-built NetworkX graph files (Git-tracked)
├── .env                      # Global backend environment configurations
├── pyproject.toml / uv.lock  # Python dependencies managed via uv package manager
└── run_pipeline.sh           # Executable script running the complete ingestion pipeline
```

---

## 🛠️ Local Setup

### Prerequisites
- [uv](https://github.com/astral-sh/uv) (Fast Python package manager)
- [Node.js & npm](https://nodejs.org/)
- [Ollama](https://ollama.com/) (For generating new community summaries locally)

### 1. Clone & Install Python Dependencies
```bash
# Clone the repository
git clone <your-repo-url>
cd FinBot

# Sync dependencies and create a working .venv automatically
uv sync
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# LLM Providers (Required for Chat API)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key

# Local LLM config (For community clustering / local run)
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=llama3.2:3b

# Paths (Keep defaults for local development)
NETWORKX_GRAPH_PATH=data/networkx/nifty_graph.pkl
CHROMA_PATH=data/chromadb
CHAT_DB_URL=sqlite:///./nifty_chat_history.db

# HuggingFace Token (For embeddings)
HF_TOKEN=your_huggingface_token
```

### 3. Run Ingestion Pipeline (Optional)
The pre-built vector database and graph pickle files are already tracked in Git inside the `data/` folder, so you don't need to rebuild them to get started. If you want to update the data:
1. Ensure Ollama is running locally and you have the model pulled:
   ```bash
   ollama pull llama3.2:3b
   ```
2. Execute the pipeline script:
   ```bash
   ./run_pipeline.sh
   ```

---

## 🚀 Running the Application Locally

### Start Python Backend
From the root directory:
```bash
uv run python backend/main.py
```
The server will start at `http://127.0.0.1:8000`.

### Start React Frontend
In a new terminal window, navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```
The dev server will spin up (typically at `http://localhost:5173`).

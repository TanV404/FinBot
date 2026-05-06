# NIFTY50 Graph RAG Chatbot

An advanced financial analysis chatbot that uses a **Hybrid Graph-Vector RAG** architecture to provide high-precision insights into NIFTY 50 companies.

## Features
- **Knowledge Graph**: Built with NetworkX to map corporate leadership, sectors, and financial metrics.
- **Vector Store**: ChromaDB integration for semantic search over Wikipedia documents.
- **Community Summaries**: Automated clustering and summarization of graph sub-sections for better multi-hop reasoning.
- **Evaluation Suite**: End-to-end scoring for Faithfulness, Relevance, and Completeness.

## Installation
1. Clone the repo: `git clone <repo-url>`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment: Create a `.env` file with your `HF_TOKEN` and `OLLAMA_BASE_URL`.

## Usage
- **Ingest Data**: `python ingest.py`
- **Start Backend**: `python main.py`
- **Run Evaluation**: `python evaluate_rag.py`
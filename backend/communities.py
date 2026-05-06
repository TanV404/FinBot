"""
communities.py — Detects communities in the NetworkX graph, generates text summaries
using a local LLM (via Ollama), and stores them in ChromaDB to improve complex
query retrieval and multi-hop reasoning (similar to GraphRAG).

Fixes applied:
  1. Removed unused ChatOpenAI import (was imported but never used correctly).
  2. LLM is now constructed once and reused (was reconstructed inside the loop).
  3. Individual community summarization errors are isolated — one failure does
     not abort the entire run.
  4. store_summaries_in_chroma uses add_documents instead of from_documents so
     it appends to the existing ChromaDB collection rather than wiping it.
"""

import os
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any

import networkx as nx
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

load_dotenv()

BASE_DIR              = Path(__file__).resolve().parent.parent
GRAPH_PATH            = BASE_DIR / "data" / "networkx" / "nifty_graph.pkl"
CHROMA_PATH           = str(BASE_DIR / "data" / "chromadb")
COMMUNITIES_OUT_PATH  = BASE_DIR / "data" / "communities" / "community_summaries.json"

# ── LLM factory ──────────────────────────────────────────────

def _build_llm():
    """
    Build the LLM used for community summarization.
    Reads OLLAMA_BASE_URL and OLLAMA_MODEL from the environment,
    matching the same variables used everywhere else in the project.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    model    = os.getenv("OLLAMA_MODEL",    "llama3.2")
    return ChatOpenAI(
        base_url=base_url,
        api_key="ollama",       # Required by the ChatOpenAI wrapper
        model=model,
        temperature=0,
        max_tokens=1200,
    )


# ── Subgraph helpers ──────────────────────────────────────────

def extract_subgraph_text(G: nx.MultiDiGraph, community_nodes: set) -> str:
    """Convert a community subgraph into a text block for the LLM."""
    subgraph = G.subgraph(community_nodes)
    lines = ["Nodes in Community:"]

    for node, data in subgraph.nodes(data=True):
        label = data.get("label", "Entity")
        lines.append(f"  - {node} ({label})")

    lines.append("\nRelationships in Community:")
    for u, v, data in subgraph.edges(data=True):
        relation  = data.get("relation", "LINKED_TO")
        formatted = data.get("formatted") or data.get("value", "")
        if formatted:
            lines.append(f"  - {u} -> {relation} -> {v} (Value: {formatted})")
        else:
            lines.append(f"  - {u} -> {relation} -> {v}")

    return "\n".join(lines)


# ── Community detection ───────────────────────────────────────

def detect_communities(G: nx.MultiDiGraph) -> List[set]:
    """Detect communities using Louvain (falls back to label propagation)."""
    G_simple = nx.Graph(G)
    try:
        communities = nx.community.louvain_communities(G_simple, resolution=1.0)
    except AttributeError:
        communities = list(nx.community.label_propagation_communities(G_simple))
    return list(communities)


# ── Summarization ─────────────────────────────────────────────

_SUMMARY_PROMPT = PromptTemplate.from_template(
    "You are an expert financial analyst. Analyze the following graph community and provide "
    "a concise summary of its key themes, relationships, and significance. "
    "This is part of a Nifty 50 knowledge graph.\n"
    "Focus on highlighting multi-hop relationships, common sectors, shared metrics, "
    "or overarching trends.\n\n"
    "Community Subgraph Details:\n"
    "{subgraph_text}\n\n"
    "Community Summary:"
)


def summarize_communities(
    G: nx.MultiDiGraph,
    communities: List[set],
) -> List[Dict[str, Any]]:
    """Generate LLM summaries for each community (skips tiny ones)."""
    llm   = _build_llm()
    chain = _SUMMARY_PROMPT | llm

    summaries: List[Dict[str, Any]] = []

    for i, community in enumerate(communities):
        if len(community) < 3:
            continue

        print(f"Summarizing Community {i} ({len(community)} nodes)…")
        subgraph_text = extract_subgraph_text(G, community)

        # Guard against huge communities exceeding the model context
        if len(subgraph_text) > 20_000:
            subgraph_text = subgraph_text[:20_000] + "\n…[truncated]"

        try:
            response     = chain.invoke({"subgraph_text": subgraph_text})
            summary_text = response.content.strip()
        except Exception as e:
            print(f"  ⚠️ Error summarizing community {i}: {e}")
            summary_text = ""   # Skip rather than store a placeholder

        if not summary_text:
            continue

        summaries.append({
            "community_id": i,
            "nodes":        list(community),
            "summary":      summary_text,
        })

    return summaries


# ── ChromaDB storage ──────────────────────────────────────────

def store_summaries_in_chroma(summaries: List[Dict[str, Any]]):
    """
    Embed and store community summaries in ChromaDB.

    FIX: Uses Chroma(...).add_documents() instead of Chroma.from_documents()
    so that this step APPENDS to the existing collection (populated by ingest.py)
    rather than replacing it.
    """
    docs = []
    for summary in summaries:
        doc = Document(
            page_content=(
                f"Community {summary['community_id']} Summary: {summary['summary']}\n\n"
                f"Nodes in community: {', '.join(str(n) for n in summary['nodes'])}"
            ),
            metadata={
                "source":       "community_summary",
                "community_id": summary["community_id"],
                "node_count":   len(summary["nodes"]),
            },
        )
        docs.append(doc)

    if not docs:
        print("⚠️  No valid summaries to ingest into ChromaDB.")
        return

    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
    )

    # Append to existing collection
    vector_store = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
    )
    vector_store.add_documents(docs)
    print(f"✅ Ingested {len(docs)} community summaries into ChromaDB at {CHROMA_PATH}.")


# ── Entry point ───────────────────────────────────────────────

def process_communities():
    if not GRAPH_PATH.exists():
        print(f"❌ Graph not found at {GRAPH_PATH}. Run ingest.py first.")
        return

    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)

    print(f"Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")

    communities = detect_communities(G)
    print(f"Detected {len(communities)} communities.")

    COMMUNITIES_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    summaries = summarize_communities(G, communities)

    with open(COMMUNITIES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(summaries)} community summaries → {COMMUNITIES_OUT_PATH}")

    store_summaries_in_chroma(summaries)


if __name__ == "__main__":
    process_communities()
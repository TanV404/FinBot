"""
communities.py — Detects communities in the NetworkX graph, generates text summaries
using an LLM, and stores them in ChromaDB to improve complex query retrieval and 
multi-hop reasoning (similar to GraphRAG).
"""

import os
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any

import networkx as nx
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = BASE_DIR / "data" / "networkx" / "nifty_graph.pkl"
CHROMA_PATH = str(BASE_DIR / "data" / "chromadb")
COMMUNITIES_OUT_PATH = BASE_DIR / "data" / "communities" / "community_summaries.json"


def extract_subgraph_text(G: nx.MultiDiGraph, community_nodes: set) -> str:
    """Convert a subgraph of community nodes into a text representation for the LLM."""
    subgraph = G.subgraph(community_nodes)
    lines = []
    
    # Add node info
    lines.append("Nodes in Community:")
    for node, data in subgraph.nodes(data=True):
        label = data.get("label", "Entity")
        lines.append(f" - {node} ({label})")
                
    # Add edges within the community
    lines.append("\nRelationships in Community:")
    for u, v, data in subgraph.edges(data=True):
        relation = data.get("relation", "LINKED_TO")
        formatted = data.get("formatted") or data.get("value", "")
        if formatted:
            lines.append(f" - {u} -> {relation} -> {v} (Value: {formatted})")
        else:
            lines.append(f" - {u} -> {relation} -> {v}")
            
    return "\n".join(lines)


def detect_communities(G: nx.MultiDiGraph) -> List[set]:
    """Detect communities in the graph."""
    # Convert MultiDiGraph to simple undirected Graph for community detection
    G_simple = nx.Graph(G)
    
    # Using Louvain community detection
    try:
        communities = nx.community.louvain_communities(G_simple, resolution=1.0)
    except AttributeError:
        # Fallback if louvain is not available in this networkx version
        communities = list(nx.community.label_propagation_communities(G_simple))
        
    return list(communities)


def summarize_communities(G: nx.MultiDiGraph, communities: List[set]) -> List[Dict[str, Any]]:
    """Generate LLM summaries for each community."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
        max_tokens=800
    )
    
    prompt = PromptTemplate.from_template(
        "You are an expert financial analyst. Analyze the following graph community and provide a concise summary of its key themes, relationships, and significance. This is part of a Nifty 50 knowledge graph.\n"
        "Focus on highlighting multi-hop relationships, common sectors, shared metrics, or overarching trends.\n\n"
        "Community Subgraph Details:\n"
        "{subgraph_text}\n\n"
        "Community Summary:"
    )
    
    chain = prompt | llm
    summaries = []
    
    for i, community in enumerate(communities):
        # Skip tiny communities
        if len(community) < 3:
            continue
            
        print(f"Summarizing Community {i} ({len(community)} nodes)...")
        subgraph_text = extract_subgraph_text(G, community)
        
        # Limit text length to avoid token limits
        if len(subgraph_text) > 20000:
            subgraph_text = subgraph_text[:20000] + "\n...[truncated]"
            
        try:
            response = chain.invoke({"subgraph_text": subgraph_text})
            summary_text = response.content
        except Exception as e:
            print(f"Error summarizing community {i}: {e}")
            summary_text = "Error generating summary."
            
        summaries.append({
            "community_id": i,
            "nodes": list(community),
            "summary": summary_text
        })
        
    return summaries


def store_summaries_in_chroma(summaries: List[Dict[str, Any]]):
    """Embed and store the community summaries in ChromaDB."""
    docs = []
    for summary in summaries:
        if summary["summary"] == "Error generating summary.":
            continue
            
        doc = Document(
            page_content=f"Community {summary['community_id']} Summary: {summary['summary']}\n\nNodes in community: {', '.join(summary['nodes'])}",
            metadata={
                "source": "community_summary", 
                "community_id": summary["community_id"],
                "node_count": len(summary["nodes"])
            }
        )
        docs.append(doc)
        
    if docs:
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_PATH)
        print(f"✅ Ingested {len(docs)} community summaries into ChromaDB at {CHROMA_PATH}.")
    else:
        print("⚠️ No valid summaries to ingest into ChromaDB.")


def process_communities():
    if not GRAPH_PATH.exists():
        print(f"Graph not found at {GRAPH_PATH}. Please run ingest.py first.")
        return
        
    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)
        
    print(f"Loaded graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    
    communities = detect_communities(G)
    print(f"Detected {len(communities)} communities.")
    
    COMMUNITIES_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    summaries = summarize_communities(G, communities)
    
    with open(COMMUNITIES_OUT_PATH, "w") as f:
        json.dump(summaries, f, indent=4)
        
    print(f"Saved {len(summaries)} community summaries to {COMMUNITIES_OUT_PATH}")
    
    store_summaries_in_chroma(summaries)


if __name__ == "__main__":
    process_communities()

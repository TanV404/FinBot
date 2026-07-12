"""
retriever.py — Hybrid graph + vector retriever for the NIFTY knowledge graph.
"""

import pickle
from typing import Any, List

from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
import os
from huggingface_hub import InferenceClient
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma


# ── Pydantic schema for LLM structured output ────────────────
class EntityExtraction(BaseModel):
    companies: List[str] = Field(
        description="Exact NSE stock ticker symbols (e.g. TCS, RELIANCE, INFY) found in the query."
    )


# Labels that are values / time nodes — never valid query anchors
_SKIP_LABELS = {"FinancialMetric", "TimePeriod", "Shareholding"}


# ── Graph retriever ───────────────────────────────────────────
class NiftyGraphRetriever(BaseRetriever):
    graph_path: str
    max_hops: int = 2
    llm: Any = None
    _G: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with open(self.graph_path, "rb") as f:
            self._G = pickle.load(f)

    # ── Anchor resolution ─────────────────────────────────────

    def _substring_anchors(self, query: str) -> list:
        """
        Fallback: find graph nodes whose name or full_name appears verbatim in the query.
        """
        q_lower = query.lower()
        matches = []
        for node in self._G.nodes:
            if not isinstance(node, str) or len(node) <= 1:
                continue
            
            data = self._G.nodes[node]
            label = data.get("label", "")
            if label in _SKIP_LABELS:
                continue
            
            # 1. Exact node ID match (e.g., "TCS", "Energy")
            if node.lower() in q_lower:
                if node not in matches: matches.append(node)
                continue
            
            # 2. Full name match mapping (e.g., "Infosys Limited" -> INFY)
            full_name = data.get("full_name", "").lower()
            if full_name:
                clean_name = full_name.replace(" limited", "").replace(" ltd.", "").replace(" ltd", "").strip()
                if clean_name and clean_name in q_lower:
                    if node not in matches: 
                        matches.append(node)
                    continue
                
                # First word match if highly distinctive (e.g., "Infosys", "Maruti")
                first_word = clean_name.split()[0]
                if len(first_word) >= 4 and first_word in q_lower:
                    if node not in matches: 
                        matches.append(node)

        # Prefer Company nodes first, then others
        matches.sort(key=lambda n: 0 if self._G.nodes[n].get("label") == "Company" else 1)
        return matches[:4]

    def _resolve_anchors(self, query: str) -> list:
        """
        Resolve query to graph anchor nodes.
        Short-circuits LLM entirely if substring matching successfully finds a company.
        """
        substring = self._substring_anchors(query)
        
        # SHORT-CIRCUIT: Massive speedup. If we already found a company via name mapping, skip the LLM.
        if any(self._G.nodes[n].get("label") == "Company" for n in substring):
            return substring[:4]

        if not self.llm:
            return substring[:2]

        # ── LLM ticker extraction ─────────────────────────────
        valid_tickers: list = []
        try:
            extractor = self.llm.with_structured_output(EntityExtraction)
            result = extractor.invoke(
                "Extract the exact NSE stock ticker symbols (e.g. TCS, RELIANCE, INFY, "
                "HDFCBANK, WIPRO) for Indian companies mentioned in this query. "
                "Return ONLY valid tickers as a JSON list. "
                "If no company is mentioned, return an empty list. "
                f"Query: {query}"
            )
            candidates = [t.strip().upper() for t in (result.companies or [])]
            valid_tickers = [n for n in candidates if n in self._G.nodes]
        except Exception as e:
            print(f"[GraphRetriever] LLM extraction failed: {e}")

        if valid_tickers:
            extras = [n for n in substring if self._G.nodes[n].get("label") != "Company"
                      and n not in valid_tickers]
            return (valid_tickers + extras)[:4]

        return substring[:2]

    # ── Graph traversal ───────────────────────────────────────

    def _traverse(self, anchor: str) -> str:
        if anchor not in self._G:
            return ""

        node_data = self._G.nodes[anchor]
        node_label = node_data.get("label", "Entity")
        full_name  = node_data.get("full_name", anchor)

        lines = [
            f"=== {anchor} | {node_label} | {full_name} ===",
        ]

        if node_label == "Company":
            metrics: dict[str, list] = {}

            for _, v, data in self._G.out_edges(anchor, data=True):
                rel = data.get("relation", "")

                if rel == "VALUE_AT":
                    metric   = str(v)
                    date_str = data.get("date", "N/A")
                    val      = data.get("formatted") or data.get("value", "N/A")
                    metrics.setdefault(metric, []).append(f"{val} ({date_str})")

                elif rel == "IN_SECTOR":
                    lines.append(f"Sector: {v}")

                elif rel == "IN_INDUSTRY":
                    lines.append(f"Industry: {v}")

                elif rel in ("HELD_BY_INSIDERS", "HELD_BY_INSTITUTIONS"):
                    sh_data = self._G.nodes.get(str(v), {})
                    pct     = sh_data.get("value", "N/A")
                    label_clean = rel.replace("HELD_BY_", "").replace("_", " ").title()
                    lines.append(f"{label_clean} Holding: {pct}")

            for metric in sorted(metrics):
                entries = " | ".join(metrics[metric])
                lines.append(f"{metric}: {entries}")

            for u, _, data in self._G.in_edges(anchor, data=True):
                if data.get("relation") == "LEADS":
                    lines.append(f"Leadership: {u}")

        elif node_label in ("Sector", "Industry"):
            rel_type = "IN_SECTOR" if node_label == "Sector" else "IN_INDUSTRY"
            member_companies = []
            for u, v, data in self._G.in_edges(anchor, data=True):
                if data.get("relation") == rel_type:
                    company_name = self._G.nodes.get(u, {}).get("full_name", u)
                    member_companies.append(f"{u} ({company_name})")

            if member_companies:
                lines.append(f"Companies in {anchor} [{node_label}]:")
                lines.extend(f"  - {c}" for c in sorted(member_companies))
            else:
                lines.append(f"No companies found under {anchor}.")

        elif node_label == "Person":
            for _, v, data in self._G.out_edges(anchor, data=True):
                if data.get("relation") == "LEADS":
                    company_name = self._G.nodes.get(v, {}).get("full_name", v)
                    lines.append(f"Leads: {v} ({company_name})")

        result = "\n".join(lines)
        return result if len(lines) > 1 else ""

    def _get_relevant_documents(self, query: str, *, run_manager=None):
        anchors = self._resolve_anchors(query)
        print(f"[GraphRetriever] Query='{query}' → Anchors={anchors}")

        docs = []
        for anchor in anchors:
            txt = self._traverse(anchor)
            if txt:
                docs.append(Document(
                    page_content=txt,
                    metadata={"source": "graph", "anchor": anchor},
                ))
        return docs


class HuggingFaceAPIEmbeddings(Embeddings):
    """Hugging Face Inference API Embeddings client (lightweight, doesn't load PyTorch or model weights locally)."""
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self.api_key = os.getenv("HF_TOKEN")
        self.client = InferenceClient(model=model_name, token=self.api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        res = self.client.feature_extraction(texts)
        if hasattr(res, "tolist"):
            return res.tolist()
        return [list(x) for x in res]

    def embed_query(self, text: str) -> list[float]:
        res = self.client.feature_extraction(text)
        if hasattr(res, "tolist"):
            return res.tolist()
        return list(res)


# ── Hybrid retriever (graph + vector) ────────────────────────
class HybridNiftyRetriever(BaseRetriever):
    graph_path:  str
    chroma_path: str
    llm: Any = None
    _graph:  Any = PrivateAttr()
    _vector: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._graph = NiftyGraphRetriever(graph_path=self.graph_path, llm=self.llm)

        emb = HuggingFaceAPIEmbeddings()
        self._vector = Chroma(
            persist_directory=self.chroma_path,
            embedding_function=emb,
        )

    def _get_relevant_documents(self, query: str, *, run_manager=None):
        graph_docs = self._graph.invoke(query)

        standard_docs: list = []
        community_docs: list = []

        try:
            standard_docs = self._vector.similarity_search(query, k=3)
            for doc in standard_docs:
                doc.metadata.setdefault("source", "vector_kb")
        except Exception as e:
            print(f"[VectorRetriever] Standard search failed: {e}")

        try:
            community_docs = self._vector.similarity_search(
                query,
                k=2,
                filter={"source": "community_summary"},
            )
        except Exception as e:
            pass 

        return graph_docs + standard_docs + community_docs
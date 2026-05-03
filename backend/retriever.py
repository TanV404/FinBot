"""
retriever.py — Hybrid retriever combining a NetworkX knowledge graph (structured)
with a ChromaDB vector store (semantic / Wikipedia chunks).

Anchor resolution order:
  1. Explicit ticker alias lookup (TICKER_ALIASES dict)
  2. Sector keyword match (only unambiguous multi-word phrases)
  3. Company-node substring fallback — always runs, never blocked by step 1/2

BFS traversal renders VALUE_AT edges as self-contained fact lines:
  WIPRO → VALUE_AT (as of 2025-12-31) → Total Revenue: ₹235.56 Billion
"""

import pickle
from typing import Any, List, Optional

from pydantic import PrivateAttr
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ── Ticker aliases ─────────────────────────────────────────────────────────────
# Define as Ticker -> list of aliases for readability
_RAW_TICKER_ALIASES = {
    "RELIANCE": ["ril", "reliance"],
    "TCS": ["tcs", "tata consultancy services", "tata consultancy"],
    "INFY": ["infy", "infosys"],
    "HDFCBANK": ["hdfc bank", "hdfcbank"],
    "ICICIBANK": ["icici bank", "icicibank"],
    "WIPRO": ["wipro"],
    "HINDUNILVR": ["hindustan unilever", "hul", "hindunilvr"],
    "BHARTIARTL": ["bharti airtel", "airtel", "bhartiartl"],
    "BAJFINANCE": ["bajaj finance", "bajfinance"],
    "KOTAKBANK": ["kotak mahindra bank", "kotak mahindra", "kotak bank", "kotak", "kotakbank"],
    "SBIN": ["state bank of india", "state bank", "sbi"],
    "M&M": ["mahindra and mahindra", "mahindra & mahindra", "m&m", "mahindra"],
    "MARUTI": ["maruti suzuki", "maruti", "msil"],
    "NTPC": ["ntpc"],
    "ONGC": ["ongc"],
    "POWERGRID": ["power grid corporation", "power grid", "powergrid"],
    "SUNPHARMA": ["sun pharmaceutical", "sun pharma", "sunpharma"],
    "TITAN": ["titan company", "titan"],
    "ULTRACEMCO": ["ultratech cement", "ultratech", "ultracemco"],
    "NESTLEIND": ["nestle india", "nestle", "nestleind"],
    "HCLTECH": ["hcl technologies", "hcl tech", "hcltech", "hcl"],
    "ASIANPAINT": ["asian paints", "asianpaint"],
    "AXISBANK": ["axis bank", "axis", "axisbank"],
    "ADANIPORTS": ["adani ports", "adaniports"],
    "COALINDIA": ["coal india", "coalindia"],
    "JSWSTEEL": ["jsw steel", "jswsteel"],
    "TATASTEEL": ["tata steel", "tatasteel"],
    "TATACONSUM": ["tata consumer products", "tata consumer", "tataconsum"],
    "TATAMOTORS": ["tata motors", "tatamotors"],
    "TECHM": ["tech mahindra", "techm"],
    "CIPLA": ["cipla"],
    "DRREDDY": ["dr reddy's laboratories", "dr reddys", "dr reddy", "drreddy"],
    "DIVISLAB": ["divi's laboratories", "divis laboratories", "divis lab", "divislab"],
    "APOLLOHOSP": ["apollo hospitals", "apollo", "apollohosp"],
    "BAJAJ-AUTO": ["bajaj auto", "bajajauto"],
    "BAJAJFINSV": ["bajaj finserv", "bajajfinsv"],
    "BPCL": ["bharat petroleum", "bpcl"],
    "BRITANNIA": ["britannia industries", "britannia"],
    "EICHERMOT": ["eicher motors", "eichermot"],
    "GRASIM": ["grasim industries", "grasim"],
    "HDFCLIFE": ["hdfc life insurance", "hdfc life", "hdfclife"],
    "HEROMOTOCO": ["hero motocorp", "hero moto", "heromotoco"],
    "HINDALCO": ["hindalco industries", "hindalco"],
    "INDUSINDBK": ["indusind bank", "indusind", "indusindbk"],
    "LT": ["larsen and toubro", "larsen & toubro", "l&t", "lt"],
    "LTIM": ["ltimindtree", "lti mindtree"],
    "SBILIFE": ["sbi life insurance", "sbi life", "sbilife"],
    "SHRIRAMFIN": ["shriram finance", "shriramfin"],
    "VEDL": ["vedanta"],
    "ZOMATO": ["zomato"],
    "ADANIENT": ["adani enterprises", "adanient"],
    "JIOFIN": ["jio financial services", "jio financial", "jiofin"],
}

# Invert dictionary: lowercase query -> graph node ID
# Sorted longest-first at runtime so multi-word aliases shadow shorter ones.
TICKER_ALIASES: dict[str, str] = {
    alias: ticker 
    for ticker, aliases in _RAW_TICKER_ALIASES.items() 
    for alias in aliases
}

# ── Sector keywords — ONLY unambiguous multi-word phrases ────────────────────
# Short tokens like "it", "in", "auto" can false-match inside common words.
_RAW_SECTOR_KEYWORDS = {
    "Information Technology": ["it sector", "technology sector", "information technology sector"],
    "Energy": ["energy sector"],
    "Financial Services": ["banking sector", "financial services sector"],
    "Healthcare": ["pharma sector", "healthcare sector"],
    "Consumer Staples": ["fmcg sector", "consumer staples sector"],
    "Automobile": ["automobile sector", "auto sector"],
}

SECTOR_KEYWORDS: dict[str, str] = {
    kw: sector 
    for sector, kws in _RAW_SECTOR_KEYWORDS.items() 
    for kw in kws
}


class NiftyGraphRetriever(BaseRetriever):
    """Structured retriever: BFS over a NetworkX MultiDiGraph."""

    graph_path:       str
    max_hops:         int = 2
    max_anchor_nodes: int = 3
    _G: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with open(self.graph_path, "rb") as f:
            self._G = pickle.load(f)

    # ── Value formatting ──────────────────────────────────────────────────────

    def _fmt(self, val: Any) -> Optional[str]:
        """Convert raw numeric string to ₹ string. Returns None for NaN."""
        try:
            num = float(val)
            if num != num:
                return None
            if abs(num) >= 1e12:
                return f"₹{num / 1e12:.2f} Trillion"
            if abs(num) >= 1e9:
                return f"₹{num / 1e9:.2f} Billion"
            if abs(num) >= 1e7:
                return f"₹{num / 1e7:.2f} Crore"
            return f"₹{num:,.2f}"
        except (ValueError, TypeError):
            return str(val)

    # ── Anchor resolution ─────────────────────────────────────────────────────

    def _resolve_anchors(self, query: str) -> List[str]:
        q = query.lower()
        matched: set[str] = set()

        # 1. Ticker alias — longest match first to avoid "kotak" shadowing
        #    "kotak mahindra bank" etc.
        for alias in sorted(TICKER_ALIASES, key=len, reverse=True):
            if alias in q:
                matched.add(TICKER_ALIASES[alias])

        # 2. Sector keywords (only unambiguous phrases)
        for kw, sector_node in SECTOR_KEYWORDS.items():
            if kw in q and sector_node in self._G:
                matched.add(sector_node)

        # 3. Company-node substring fallback — ALWAYS runs (not gated on
        #    prior matches) so companies absent from TICKER_ALIASES are found.
        query_words = {w for w in q.split() if len(w) > 3}
        for node, attrs in self._G.nodes(data=True):
            if attrs.get("label") != "Company":
                continue
            node_lower = str(node).lower()
            full_name  = str(attrs.get("full_name", "")).lower()
            if (node_lower in q
                    or full_name in q
                    or any(w in node_lower for w in query_words)
                    or any(w in full_name  for w in query_words)):
                matched.add(str(node))

        return list(matched)[: self.max_anchor_nodes]

    # ── BFS traversal ─────────────────────────────────────────────────────────

    def _traverse(self, anchor: str) -> str:
        if anchor not in self._G:
            return ""

        visited  = {anchor}
        node_type = self._G.nodes[anchor].get("label", "Entity")
        lines    = [f"[Core] {anchor} ({node_type})"]
        frontier = [anchor]

        for hop in range(self.max_hops):
            next_frontier: list[str] = []
            for current in frontier:
                for _u, v, data in self._G.out_edges(current, data=True):
                    rel    = data.get("relation", "LINKED")
                    v_type = self._G.nodes[v].get("label", "Node")
                    indent = "  " * (hop + 1)

                    if rel == "VALUE_AT":
                        # Use pre-formatted value stored at ingest time
                        formatted = data.get("formatted") or self._fmt(data.get("value", ""))
                        date_str  = data.get("date", "")
                        date_tag  = f" (as of {date_str})" if date_str else ""
                        val_part  = f": {formatted}" if formatted else ""
                        lines.append(
                            f"{indent}→ VALUE_AT{date_tag} → [{v_type}] {v}{val_part}"
                        )
                    elif rel == "REPORTED_ON":
                        # Skip — this edge is only for visualisation
                        pass
                    else:
                        raw_val = data.get("value", "")
                        val_str = f" ({raw_val})" if raw_val else ""
                        lines.append(f"{indent}→ {rel}{val_str} → [{v_type}] {v}")

                    if v not in visited:
                        visited.add(v)
                        next_frontier.append(v)
            frontier = next_frontier

        return "\n".join(lines)

    # ── LangChain interface ───────────────────────────────────────────────────

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        anchors = self._resolve_anchors(query)
        docs: List[Document] = []
        for anchor in anchors:
            content = self._traverse(anchor)
            if content:
                docs.append(Document(
                    page_content=content,
                    metadata={"source": "graph", "anchor": anchor},
                ))
        return docs


class HybridNiftyRetriever(BaseRetriever):
    """Combines structured graph retrieval with semantic vector search."""

    graph_path:  str
    chroma_path: str
    max_hops:    int = 2
    vector_k:    int = 5
    _graph_retriever: Any = PrivateAttr()
    _vectorstore:     Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._graph_retriever = NiftyGraphRetriever(
            graph_path=self.graph_path,
            max_hops=self.max_hops,
        )
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self._vectorstore = Chroma(
            persist_directory=self.chroma_path,
            embedding_function=embeddings,
        )

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        graph_docs = self._graph_retriever.invoke(query)
        try:
            vector_docs = self._vectorstore.similarity_search(query, k=self.vector_k)
        except Exception:
            vector_docs = []
        return graph_docs + vector_docs
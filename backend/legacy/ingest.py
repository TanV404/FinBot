"""
ingest.py — Builds the NIFTY knowledge graph (NetworkX) and vector store (ChromaDB).

Fixes applied:
  1. _parse_table: value tokens are now validated as numeric before being accepted.
     Previously any trailing N tokens were assumed to be values, silently dropping
     rows where the last tokens were text (e.g. footnotes like "TTM" or "N/A").
  2. _parse_table: handles both tab-separated and space-separated files.
  3. _ingest_financials: logs metric counts per company so missing data is visible.
  4. _is_value_token() uses float() not a regex — handles scientific notation and NaN.
"""

import os
import re
import pickle
import shutil
from pathlib import Path
from typing import Optional

import networkx as nx
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# Clean broken SSL envs (important for HuggingFace)
os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)


BASE_DIR    = Path(__file__).resolve().parent.parent
FIN_DIR     = BASE_DIR / "data" / "docs" / "yfinance"
WIKI_DIR    = BASE_DIR / "data" / "docs" / "wiki"
CHROMA_PATH = str(BASE_DIR / "data" / "chromadb")
GRAPH_PATH  = BASE_DIR / "data" / "networkx" / "nifty_graph.pkl"


# ── UTF-safe file reader ──────────────────────────────────────
def safe_read(path: Path) -> str:
    """Robust file reader that never crashes on encoding issues."""
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8", errors="replace")


# ── Configuration ─────────────────────────────────────────────
TARGET_METRICS = {
    "Total Revenue":    "Total Revenue",
    "Net Income":       "Net Income",
    "Net Debt":         "Net Debt",
    "Total Assets":     "Total Assets",
    "Gross Profit":     "Gross Profit",
    "Operating Income": "Operating Income",
    "EBITDA":           "EBITDA",
}

SHAREHOLDING_FIELDS = {
    "insidersPercentHeld":     ("Insider Holding",       "HELD_BY_INSIDERS"),
    "institutionsPercentHeld": ("Institutional Holding", "HELD_BY_INSTITUTIONS"),
}

_LEADERSHIP_RE = re.compile(
    r"(?:CEO/MD|MD\s*&\s*CEO|CEO|Managing Director|Executive Director"
    r"|Chairman\s*&\s*MD|Chairman)\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)
_DATE_RE   = re.compile(r"\d{4}-\d{2}-\d{2}")
# ── Helpers ───────────────────────────────────────────────────

def _is_value_token(tok: str) -> bool:
    """
    Return True if tok is a parseable numeric value.

    Uses float() — NOT a regex — so it correctly accepts:
      • Scientific notation  2.481959e+11, -1.758e+10, 0.000000e+00
      • NaN                  float("NaN") → nan  (filtered downstream by _fmt)
      • Plain numbers        123, 45.67, -89.0
    """
    try:
        float(tok)
        return True
    except (ValueError, TypeError):
        return False


def _fmt(val_str: str) -> Optional[str]:
    try:
        num = float(val_str)
    except (ValueError, TypeError):
        return None
    if num != num:          # NaN guard — float("NaN") != float("NaN") is True
        return None
    if abs(num) >= 1e12:
        return f"₹{num / 1e12:.2f} Trillion"
    if abs(num) >= 1e9:
        return f"₹{num / 1e9:.2f} Billion"
    if abs(num) >= 1e7:
        return f"₹{num / 1e7:.2f} Crore"
    return f"₹{num:,.2f}"


def _split_sections(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_name = "PREAMBLE"
    buf: list[str] = []

    for line in content.splitlines():
        m = re.match(r"^---\s*(.+?)\s*---\s*$", line.strip())
        if m:
            sections[current_name] = "\n".join(buf)
            current_name = m.group(1).strip().upper()
            buf = []
        else:
            buf.append(line)

    sections[current_name] = "\n".join(buf)
    return sections


def _parse_table(lines: list[str]) -> dict[str, dict[str, str]]:
    r"""
    Parse a fixed-width financial table into {metric_name: {date: raw_value}}.

    yfinance file format:
      • Header row: long whitespace padding + YYYY-MM-DD date columns
      • Data rows:  metric name (may contain spaces) then N right-aligned values
      • Values are in scientific notation (2.481959e+11) or the string "NaN"

    KEY FIX: value validation uses _is_value_token() which calls float(),
    NOT a regex.  The previous regex r"^-?[\d,]+\.?\d*$" rejected scientific
    notation and "NaN", causing every row in every file to be dropped (0 edges).
    """
    date_cols: list[str] = []
    result: dict[str, dict[str, str]] = {}

    for line in lines:
        line = line.replace("\t", " ")
        dates_found = _DATE_RE.findall(line)

        if dates_found and not date_cols:
            date_cols = dates_found
            continue

        if not date_cols:
            continue

        tokens = line.split()
        n = len(date_cols)

        if len(tokens) < n + 1:
            continue

        value_tokens = tokens[-n:]
        name_tokens  = tokens[:-n]

        if not all(_is_value_token(v) for v in value_tokens):
            continue

        metric_name = " ".join(name_tokens).strip()
        if metric_name:
            result[metric_name] = dict(zip(date_cols, value_tokens))

    return result


def _parse_performance(section_text: str) -> dict[str, dict[str, str]]:
    sub_name: Optional[str] = None
    sub_lines: dict[str, list[str]] = {}

    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and not _DATE_RE.search(stripped):
            sub_name = stripped
            sub_lines[sub_name] = []
        elif sub_name:
            sub_lines[sub_name].append(line)

    merged: dict[str, dict[str, str]] = {}
    for lines in sub_lines.values():
        merged.update(_parse_table(lines))

    return merged


# ── Ingestion ─────────────────────────────────────────────────

def _ingest_financials(G: nx.MultiDiGraph, fin_file: Path) -> int:
    """
    Parse one *_finance.txt file and populate the graph.
    Returns the number of VALUE_AT edges added (0 = format mismatch, worth checking).
    """
    symbol  = fin_file.stem.split("_")[0].upper()
    content = safe_read(fin_file)
    sections = _split_sections(content)

    G.add_node(symbol, label="Company", type="Core")

    identity = sections.get("IDENTITY", "")

    if name_m := re.search(r"Name\s*[:\-]\s*(.+)", identity, re.IGNORECASE):
        G.nodes[symbol]["full_name"] = name_m.group(1).strip()

    for m in _LEADERSHIP_RE.finditer(identity):
        person = m.group(1).strip().split("\n")[0]
        G.add_node(person, label="Person")
        G.add_edge(person, symbol, relation="LEADS")

    if sec_m := re.search(r"Sector\s*[:\-]\s*(.+)", identity, re.IGNORECASE):
        sector = sec_m.group(1).strip()
        G.add_node(sector, label="Sector")
        G.add_edge(symbol, sector, relation="IN_SECTOR")

    if ind_m := re.search(r"Industry\s*[:\-]\s*(.+)", identity, re.IGNORECASE):
        industry = ind_m.group(1).strip()
        G.add_node(industry, label="Industry")
        G.add_edge(symbol, industry, relation="IN_INDUSTRY")

    perf_key  = next((k for k in sections if "PERFORMANCE" in k), None)
    perf_rows = _parse_performance(sections.get(perf_key, "")) if perf_key else {}

    edges_added = 0
    for display_name, row_key in TARGET_METRICS.items():
        for row_name, date_vals in perf_rows.items():
            if row_key.lower() in row_name.lower():
                G.add_node(display_name, label="FinancialMetric")

                for date_str, raw_val in date_vals.items():
                    formatted = _fmt(raw_val)
                    if not formatted:
                        continue

                    G.add_node(date_str, label="TimePeriod")
                    G.add_edge(
                        symbol, display_name,
                        relation="VALUE_AT",
                        date=date_str,
                        value=raw_val,
                        formatted=formatted,
                    )
                    G.add_edge(display_name, date_str, relation="REPORTED_ON")
                    edges_added += 1

    sh_text = sections.get("SHAREHOLDING RELATIONSHIPS", "")
    for field, (node_label, relation) in SHAREHOLDING_FIELDS.items():
        if sh_m := re.search(rf"{field}\s+([\d.]+)", sh_text):
            pct  = float(sh_m.group(1)) * 100
            node = f"{symbol} – {node_label}"
            G.add_node(node, label="Shareholding", value=f"{pct:.1f}%")
            G.add_edge(symbol, node, relation=relation)

    return edges_added


# ── Main ──────────────────────────────────────────────────────

def ingest_all():
    if GRAPH_PATH.exists():
        os.remove(GRAPH_PATH)

    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    G = nx.MultiDiGraph()
    splitter   = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    all_chunks = []

    print("📂 Finance files:")
    for fin_file in sorted(FIN_DIR.glob("*_finance.txt")):
        try:
            edges = _ingest_financials(G, fin_file)
            symbol = fin_file.stem.split("_")[0].upper()
            # Warn if no financial metric edges were created (likely parse failure)
            flag = "✅" if edges > 0 else "⚠️ (0 metric edges — check file format)"
            print(f"   {flag} {fin_file.name} → {edges} metric edges")
        except Exception as e:
            print(f"   ❌ {fin_file.name} — {e}")

    print("\n📂 Wiki files:")
    for wiki_file in sorted(WIKI_DIR.glob("*_wiki.txt")):
        symbol = wiki_file.stem.split("_")[0].upper()
        text   = safe_read(wiki_file)

        chunks = splitter.create_documents(
            [text], metadatas=[{"symbol": symbol}]
        )
        all_chunks.extend(chunks)
        print(f"   ✅ {wiki_file.name} → {len(chunks)} chunks")

    if all_chunks:
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
        )
        Chroma.from_documents(all_chunks, embeddings, persist_directory=CHROMA_PATH)
        print(f"\n✅ ChromaDB: {len(all_chunks)} chunks stored at {CHROMA_PATH}")
    else:
        print("\n⚠️  No wiki chunks — ChromaDB not populated.")

    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)

    print(
        f"\n✅ Graph saved → {GRAPH_PATH}\n"
        f"   Nodes: {G.number_of_nodes()} | Edges: {G.number_of_edges()}"
    )


if __name__ == "__main__":
    ingest_all()
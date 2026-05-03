"""
ingest.py — Parses yfinance-scraped finance files and Wikipedia text,
builds a rich NetworkX MultiDiGraph, and persists both the graph and a
ChromaDB vector store.

Actual scraped finance file format:
────────────────────────────────────
--- IDENTITY ---
Name: Wipro Limited
CEO/MD: Mr. Srinivas Pallia
Sector: Technology
Industry: Information Technology Services

--- PERFORMANCE (Last 4 Quarters) ---
Income Statement:
                          2026-03-31  2025-12-31  2025-09-30  2025-06-30 ...
Total Revenue                    NaN  2.355580e+11 2.269730e+11 ...
Net Income                       NaN  3.119000e+10 ...
...

Balance Sheet:
                          2025-12-31  2025-09-30 ...
Net Debt                  4.414700e+10 ...
Total Assets              1.411859e+12 ...

--- SHAREHOLDING RELATIONSHIPS ---
Breakdown                  Value
insidersPercentHeld       0.72783
institutionsPercentHeld   0.14955
"""

import os
import re
import pickle
from pathlib import Path
from typing import Optional

import networkx as nx
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR    = Path(__file__).resolve().parent.parent
FIN_DIR     = BASE_DIR / "data" / "docs" / "yfinance"
WIKI_DIR    = BASE_DIR / "data" / "docs" / "wiki"
CHROMA_PATH = str(BASE_DIR / "data" / "chromadb")
GRAPH_PATH  = BASE_DIR / "data" / "networkx" / "nifty_graph.pkl"

# Metrics to extract → exact row-label substring (case-insensitive match)
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
    "insidersPercentHeld":     ("Insider Holding",         "HELD_BY_INSIDERS"),
    "institutionsPercentHeld": ("Institutional Holding",   "HELD_BY_INSTITUTIONS"),
}

_LEADERSHIP_RE  = re.compile(
    r"(?:CEO/MD|MD\s*&\s*CEO|CEO|Managing Director|Executive Director"
    r"|Chairman\s*&\s*MD|Chairman)\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(val_str: str) -> Optional[str]:
    """Convert a raw number string to a human-readable ₹ string.
    Returns None for NaN / unparseable values."""
    try:
        num = float(val_str)
        if num != num:          # NaN
            return None
        if abs(num) >= 1e12:
            return f"₹{num / 1e12:.2f} Trillion"
        if abs(num) >= 1e9:
            return f"₹{num / 1e9:.2f} Billion"
        if abs(num) >= 1e7:
            return f"₹{num / 1e7:.2f} Crore"
        return f"₹{num:,.2f}"
    except (ValueError, TypeError):
        return None


def _split_sections(content: str) -> dict[str, str]:
    """Split file by --- SECTION --- delimiters."""
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
    """Parse a whitespace-delimited table where:
      - One row contains only date strings (the column headers)
      - Every subsequent row is: <metric name tokens...> <value1> <value2> ...

    Returns: { metric_name: { date: raw_value_str } }
    """
    date_cols: list[str] = []
    result: dict[str, dict[str, str]] = {}

    for line in lines:
        dates_found = _DATE_RE.findall(line)
        if dates_found and not date_cols:
            date_cols = dates_found
            continue
        if not date_cols:
            continue

        tokens = line.split()
        if len(tokens) < 2:
            continue

        # Last N tokens are values (one per date column)
        n = len(date_cols)
        values      = tokens[-n:]
        name_tokens = tokens[: len(tokens) - n]
        metric_name = " ".join(name_tokens).strip()
        if not metric_name:
            continue

        result[metric_name] = dict(zip(date_cols, values))

    return result


def _parse_performance(section_text: str) -> dict[str, dict[str, str]]:
    """Split a PERFORMANCE section into sub-tables (Income Statement, Balance Sheet, etc.)
    and merge them all into one flat {metric: {date: value}} dict."""
    sub_name  = None
    sub_lines: dict[str, list[str]] = {}

    for line in section_text.splitlines():
        stripped = line.strip()
        # Sub-table header ends with ":" and contains no date
        if stripped.endswith(":") and not _DATE_RE.search(stripped):
            sub_name = stripped
            sub_lines[sub_name] = []
        elif sub_name is not None:
            sub_lines[sub_name].append(line)

    merged: dict[str, dict[str, str]] = {}
    for lines in sub_lines.values():
        merged.update(_parse_table(lines))
    return merged


# ── Per-file ingestion ────────────────────────────────────────────────────────

def _ingest_financials(G: nx.MultiDiGraph, fin_file: Path) -> None:
    symbol   = fin_file.stem.split("_")[0].upper()
    content  = fin_file.read_text(encoding="utf-8")
    sections = _split_sections(content)

    G.add_node(symbol, label="Company", type="Core")

    # ── IDENTITY ──────────────────────────────────────────────────────────────
    identity = sections.get("IDENTITY", "")

    if name_m := re.search(r"Name\s*[:\-]\s*(.+)", identity, re.IGNORECASE):
        G.nodes[symbol]["full_name"] = name_m.group(1).strip()

    for m in _LEADERSHIP_RE.finditer(identity):
        person = m.group(1).strip().split("\n")[0].strip()
        if person and person.upper() not in ("N/A", "NONE", ""):
            G.add_node(person, label="Person")
            if not G.has_edge(person, symbol):
                G.add_edge(person, symbol, relation="LEADS")

    if sec_m := re.search(r"Sector\s*[:\-]\s*(.+)", identity, re.IGNORECASE):
        sector = sec_m.group(1).strip().split("\n")[0].strip()
        if sector and sector.upper() != "N/A":
            G.add_node(sector, label="Sector")
            G.add_edge(symbol, sector, relation="IN_SECTOR")

    if ind_m := re.search(r"Industry\s*[:\-]\s*(.+)", identity, re.IGNORECASE):
        industry = ind_m.group(1).strip().split("\n")[0].strip()
        if industry and industry.upper() != "N/A":
            G.add_node(industry, label="Industry")
            G.add_edge(symbol, industry, relation="IN_INDUSTRY")

    # ── PERFORMANCE ───────────────────────────────────────────────────────────
    perf_key = next(
        (k for k in sections if "PERFORMANCE" in k), None
    )
    perf_rows = _parse_performance(sections.get(perf_key, "")) if perf_key else {}

    for display_name, row_key in TARGET_METRICS.items():
        # Match the row whose name contains row_key (case-insensitive)
        matched: Optional[dict[str, str]] = None
        for row_name, date_vals in perf_rows.items():
            if row_key.lower() in row_name.lower():
                matched = date_vals
                break
        if matched is None:
            continue

        G.add_node(display_name, label="FinancialMetric")

        for date_str, raw_val in matched.items():
            formatted = _fmt(raw_val)
            if formatted is None:
                continue        # skip NaN quarters

            G.add_node(date_str, label="TimePeriod")

            # ★ KEY FIX: flat edge carries BOTH date AND formatted value so the
            #   LLM context reads as a self-contained fact:
            #   WIPRO → VALUE_AT (as of 2025-12-31) → Total Revenue: ₹235.56 Billion
            G.add_edge(
                symbol, display_name,
                relation="VALUE_AT",
                date=date_str,
                value=raw_val,
                formatted=formatted,
            )
            # Visual edge: metric → date (used in graph visualisation)
            G.add_edge(display_name, date_str, relation="REPORTED_ON")

    # ── SHAREHOLDING ──────────────────────────────────────────────────────────
    sh_text = sections.get("SHAREHOLDING RELATIONSHIPS", "")
    for field, (node_label, relation) in SHAREHOLDING_FIELDS.items():
        if sh_m := re.search(
            rf"^{re.escape(field)}\s+([\d.]+)", sh_text, re.MULTILINE
        ):
            pct = float(sh_m.group(1)) * 100
            sh_node = f"{symbol} – {node_label}"
            G.add_node(sh_node, label="Shareholding", value=f"{pct:.1f}%")
            G.add_edge(symbol, sh_node, relation=relation, value=f"{pct:.1f}%")


# ── Main ──────────────────────────────────────────────────────────────────────

def ingest_all():
    if GRAPH_PATH.exists():
        os.remove(GRAPH_PATH)

    G = nx.MultiDiGraph()
    all_chunks: list = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    fin_files = sorted(FIN_DIR.glob("*_finance.txt"))
    print(f"📂 Finance files: {len(fin_files)}")
    for fin_file in fin_files:
        try:
            _ingest_financials(G, fin_file)
            print(f"   ✅ {fin_file.name}")
        except Exception as exc:
            print(f"   ❌ {fin_file.name}: {exc}")

    wiki_files = sorted(WIKI_DIR.glob("*_wiki.txt"))
    print(f"\n📂 Wiki files: {len(wiki_files)}")
    for wiki_file in wiki_files:
        symbol = wiki_file.stem.split("_")[0].upper()
        text   = wiki_file.read_text(encoding="utf-8")
        chunks = splitter.create_documents(
            [text], metadatas=[{"symbol": symbol, "source": "wikipedia"}]
        )
        all_chunks.extend(chunks)
        print(f"   ✅ {wiki_file.name} → {len(chunks)} chunks")

    if all_chunks:
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        Chroma.from_documents(all_chunks, embeddings, persist_directory=CHROMA_PATH)
        print(f"\n✅ ChromaDB: {len(all_chunks)} chunks ingested.")
    else:
        print("\n⚠️  No wiki chunks — ChromaDB skipped.")

    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)

    print(
        f"\n✅ Graph saved → {GRAPH_PATH}\n"
        f"   Nodes: {G.number_of_nodes()}  |  Edges: {G.number_of_edges()}"
    )


if __name__ == "__main__":
    ingest_all()
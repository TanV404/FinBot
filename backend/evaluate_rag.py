"""
evaluate_rag.py
===============
End-to-end evaluation harness for the NIFTY Graph RAG chatbot.

Metrics
-------
Per-question (LLM-as-judge, scored 1–5):
  • Faithfulness      – answer is grounded in retrieved context, no hallucinations
  • Answer Relevance  – answer directly addresses the question asked
  • Completeness      – all parts of the question are addressed

System:
  • Latency (s)
  • Anchor hit (did graph retriever surface a relevant node?)
  • Error rate

Usage
-----
python evaluate_rag.py                          # uses defaults (localhost:8000)
python evaluate_rag.py --host http://x.x.x.x:8000
python evaluate_rag.py --dataset custom_qs.json
python evaluate_rag.py --out results.xlsx
"""

import argparse
import asyncio
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from openai import OpenAI          # lightweight judge – works with Ollama too
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.series import SeriesLabel

os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT NIFTY 50 EVALUATION DATASET
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_DATASET = [
    # ── Single-company factual ──────────────────────────────────────────────
    {
        "id": "F01",
        "category": "Single-Company Factual",
        "question": "What is the current revenue of TCS?",
        "expected_entities": ["TCS"],
        "ground_truth": None,
    },
    {
        "id": "F02",
        "category": "Single-Company Factual",
        "question": "Who leads Reliance Industries?",
        "expected_entities": ["RELIANCE"],
        "ground_truth": None,
    },
    {
        "id": "F03",
        "category": "Single-Company Factual",
        "question": "What sector does Infosys operate in?",
        "expected_entities": ["INFY"],
        "ground_truth": None,
    },
    {
        "id": "F04",
        "category": "Single-Company Factual",
        "question": "What is HDFC Bank's net profit for the latest reported quarter?",
        "expected_entities": ["HDFCBANK"],
        "ground_truth": None,
    },
    {
        "id": "F05",
        "category": "Single-Company Factual",
        "question": "What is the debt-to-equity ratio of Tata Motors?",
        "expected_entities": ["TATAMOTORS"],
        "ground_truth": None,
    },
    # ── Multi-company comparison ─────────────────────────────────────────────
    {
        "id": "C01",
        "category": "Comparison",
        "question": "Compare the revenue of TCS and Infosys.",
        "expected_entities": ["TCS", "INFY"],
        "ground_truth": None,
    },
    {
        "id": "C02",
        "category": "Comparison",
        "question": "Which has a higher market cap, Wipro or HCL Technologies?",
        "expected_entities": ["WIPRO", "HCLTECH"],
        "ground_truth": None,
    },
    {
        "id": "C03",
        "category": "Comparison",
        "question": "How does HDFC Bank's PAT compare to ICICI Bank?",
        "expected_entities": ["HDFCBANK", "ICICIBANK"],
        "ground_truth": None,
    },
    # ── Sector / industry queries ────────────────────────────────────────────
    {
        "id": "S01",
        "category": "Sector",
        "question": "Which NIFTY 50 companies belong to the IT sector?",
        "expected_entities": ["IT"],
        "ground_truth": None,
    },
    {
        "id": "S02",
        "category": "Sector",
        "question": "List all banking companies in the NIFTY 50.",
        "expected_entities": ["Banking", "Financial Services"],
        "ground_truth": None,
    },
    {
        "id": "S03",
        "category": "Sector",
        "question": "Which energy sector stocks are part of NIFTY 50?",
        "expected_entities": ["Energy", "Oil"],
        "ground_truth": None,
    },
    # ── Financial metric ─────────────────────────────────────────────────────
    {
        "id": "M01",
        "category": "Financial Metric",
        "question": "What is the P/E ratio of Bajaj Finance?",
        "expected_entities": ["BAJFINANCE"],
        "ground_truth": None,
    },
    {
        "id": "M02",
        "category": "Financial Metric",
        "question": "What is the EPS of Asian Paints?",
        "expected_entities": ["ASIANPAINT"],
        "ground_truth": None,
    },
    {
        "id": "M03",
        "category": "Financial Metric",
        "question": "What is the dividend yield of Coal India?",
        "expected_entities": ["COALINDIA"],
        "ground_truth": None,
    },
    # ── Leadership / people ──────────────────────────────────────────────────
    {
        "id": "P01",
        "category": "Leadership",
        "question": "Who is the CEO of Wipro?",
        "expected_entities": ["WIPRO"],
        "ground_truth": None,
    },
    {
        "id": "P02",
        "category": "Leadership",
        "question": "Who leads Maruti Suzuki?",
        "expected_entities": ["MARUTI"],
        "ground_truth": None,
    },
    # ── Shareholding ─────────────────────────────────────────────────────────
    {
        "id": "SH01",
        "category": "Shareholding",
        "question": "What percentage of ONGC is held by institutions?",
        "expected_entities": ["ONGC"],
        "ground_truth": None,
    },
    {
        "id": "SH02",
        "category": "Shareholding",
        "question": "What is the insider holding percentage for Sun Pharmaceutical?",
        "expected_entities": ["SUNPHARMA"],
        "ground_truth": None,
    },
    # ── Out-of-scope / robustness ────────────────────────────────────────────
    {
        "id": "R01",
        "category": "Robustness",
        "question": "What is the current gold price?",
        "expected_entities": [],
        "ground_truth": "Bot should state it does not have this data.",
    },
    {
        "id": "R02",
        "category": "Robustness",
        "question": "Summarise the last 5 years of NIFTY performance.",
        "expected_entities": [],
        "ground_truth": None,
    },
    # ── Multi-turn simulation (treated as standalone) ────────────────────────
    {
        "id": "MT01",
        "category": "Multi-turn Sim",
        "question": "Tell me about TCS revenue, then compare it with Infosys revenue.",
        "expected_entities": ["TCS", "INFY"],
        "ground_truth": None,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    id: str
    category: str
    question: str
    expected_entities: list
    answer: str = ""
    latency_s: float = 0.0
    error: Optional[str] = None

    # LLM-judge scores (1–5)
    faithfulness: Optional[float] = None
    answer_relevance: Optional[float] = None
    completeness: Optional[float] = None

    # Derived
    avg_score: Optional[float] = None
    anchor_hit: Optional[bool] = None
    judge_reasoning: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# JUDGE PROMPT
# ─────────────────────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are an objective evaluator for a financial RAG chatbot focused on NIFTY 50 data.
Score each dimension on a scale of 1 (very poor) to 5 (excellent).
Return ONLY valid JSON. The reasoning value must be a short plain string with NO commas and NO special characters."""

JUDGE_USER = """Question: {question}

Bot Answer: {answer}

Ground Truth (if available): {ground_truth}

Score these dimensions:
1. faithfulness      – Is the answer grounded in facts? Does it avoid hallucinations?
   (5=fully grounded, 1=fabricated/contradictory)
2. answer_relevance  – Does the answer directly address what was asked?
   (5=directly answers, 1=completely off-topic)
3. completeness      – Are all parts of the question covered?
   (5=fully complete, 1=major omissions)

Return ONLY this JSON with integer scores and a short reasoning string (no commas inside the string):
{{
  "faithfulness": <1-5>,
  "answer_relevance": <1-5>,
  "completeness": <1-5>,
  "reasoning": "<ten words max no commas>"
}}"""

# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def build_judge_client() -> OpenAI:
    """Build OpenAI-compatible judge. Uses Ollama locally by default."""
    base_url = os.getenv("JUDGE_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"))
    api_key  = os.getenv("JUDGE_API_KEY", "ollama")
    return OpenAI(base_url=base_url, api_key=api_key)


def judge_answer(
    client: OpenAI,
    question: str,
    answer: str,
    ground_truth: Optional[str],
    model: str = "llama3.2",
) -> dict:
    """Call LLM judge and parse scores. Returns dict with scores or defaults on failure."""
    prompt = JUDGE_USER.format(
        question=question,
        answer=answer if answer else "(no answer – error occurred)",
        ground_truth=ground_truth or "N/A",
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # Primary: clean JSON parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Fallback: extract numeric scores with regex even if JSON is malformed
        def extract_score(key: str) -> Optional[int]:
            m = re.search(rf'"{key}"\s*:\s*([1-5])', raw)
            return int(m.group(1)) if m else None

        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', raw)
        reasoning = reasoning_match.group(1) if reasoning_match else "parse error – scores extracted via regex"

        scores = {
            "faithfulness":     extract_score("faithfulness"),
            "answer_relevance": extract_score("answer_relevance"),
            "completeness":     extract_score("completeness"),
            "reasoning":        reasoning,
        }
        if any(v is not None for k, v in scores.items() if k != "reasoning"):
            print(f"  [Judge] Used regex fallback parser")
            return scores

        raise ValueError(f"Could not extract scores from: {raw[:120]}")
    except Exception as e:
        print(f"  [Judge] Failed: {e}")
        return {
            "faithfulness": None,
            "answer_relevance": None,
            "completeness": None,
            "reasoning": f"Judge error: {e}",
        }


def check_anchor_hit(answer: str, expected_entities: list) -> Optional[bool]:
    """Heuristic: did the answer mention at least one expected entity?"""
    if not expected_entities:
        return None
    ans_upper = answer.upper()
    return any(e.upper() in ans_upper for e in expected_entities)


async def call_chat_endpoint(
    client: httpx.AsyncClient,
    host: str,
    question: str,
    session_id: str,
    timeout: float = 60.0,
) -> tuple[str, float]:
    """POST to /chat and return (answer, latency_seconds)."""
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{host}/chat",
            json={"message": question, "session_id": session_id},
            timeout=timeout,
        )
        latency = time.perf_counter() - t0
        if resp.status_code != 200:
            raise RuntimeError(
                f"HTTP {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json()
        answer = data.get("answer", "")
        if not answer:
            print(f"  [warn] Empty answer returned. Full response: {data}")
        return answer, latency
    except httpx.TimeoutException:
        raise RuntimeError(f"Request timed out after {timeout}s — try --timeout 180")
    except httpx.ConnectError:
        raise RuntimeError(f"Cannot connect to {host} — is the bot running?")
    except httpx.RemoteProtocolError as e:
        raise RuntimeError(f"Protocol error (server closed connection?): {type(e).__name__}")


async def run_evaluations(
    dataset: list[dict],
    host: str,
    judge_model: str,
    timeout: float,
    concurrency: int,
) -> list[EvalResult]:
    """Run all eval questions against the chatbot and judge the answers."""
    judge = build_judge_client()
    results: list[EvalResult] = []
    sem = asyncio.Semaphore(concurrency)

    async def _eval_one(item: dict) -> EvalResult:
        result = EvalResult(
            id=item["id"],
            category=item["category"],
            question=item["question"],
            expected_entities=item.get("expected_entities", []),
        )
        session_id = f"eval-{item['id']}-{uuid.uuid4().hex[:8]}"

        async with sem:
            async with httpx.AsyncClient() as http:
                try:
                    answer, latency = await call_chat_endpoint(
                        http, host, item["question"], session_id, timeout
                    )
                    result.answer    = answer
                    result.latency_s = round(latency, 3)
                except Exception as e:
                    result.error     = f"{type(e).__name__}: {e}"
                    result.answer    = ""
                    result.latency_s = 0.0
                    print(f"  [{item['id']}] Chat error: {type(e).__name__}: {e}")

        # Delete the ephemeral eval session so it doesn't pollute the DB
        try:
            async with httpx.AsyncClient() as http:
                await http.delete(f"{host}/history/{session_id}", timeout=10)
        except Exception:
            pass

        # ── LLM Judge ──────────────────────────────────────────────────────
        scores = judge_answer(
            judge,
            item["question"],
            result.answer,
            item.get("ground_truth"),
            model=judge_model,
        )
        result.faithfulness     = scores.get("faithfulness")
        result.answer_relevance = scores.get("answer_relevance")
        result.completeness     = scores.get("completeness")
        result.judge_reasoning  = scores.get("reasoning", "")

        valid_scores = [s for s in [result.faithfulness, result.answer_relevance, result.completeness] if s is not None]
        result.avg_score    = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
        result.anchor_hit   = check_anchor_hit(result.answer, result.expected_entities)

        flag = "✓" if not result.error else "✗"
        avg  = f"{result.avg_score:.2f}" if result.avg_score is not None else "N/A"
        print(f"  [{item['id']}] {flag}  avg={avg}  latency={result.latency_s}s")
        return result

    tasks = [_eval_one(item) for item in dataset]
    results = await asyncio.gather(*tasks)
    return list(results)


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────────────────────────────────────

# Colour palette
C_HEADER_FILL  = "1F3864"   # dark navy
C_HEADER_FONT  = "FFFFFF"
C_ALT_ROW      = "EBF3FF"   # light blue
C_WHITE        = "FFFFFF"
C_GOOD         = "C6EFCE"   # green
C_MID          = "FFEB9C"   # amber
C_BAD          = "FFC7CE"   # red
C_SECTION_FILL = "D6E4F0"


def _header_style(cell, bold=True):
    cell.font      = Font(name="Arial", bold=bold, color=C_HEADER_FONT, size=10)
    cell.fill      = PatternFill("solid", fgColor=C_HEADER_FILL)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _score_fill(score: Optional[float]) -> str:
    if score is None:
        return C_WHITE
    if score >= 4.0:
        return C_GOOD
    if score >= 3.0:
        return C_MID
    return C_BAD


def _thin_border() -> Border:
    s = Side(style="thin", color="BFBFBF")
    return Border(left=s, right=s, top=s, bottom=s)


def _col_widths(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


def build_excel(results: list[EvalResult], out_path: str):
    wb = Workbook()

    # ── Sheet 1 – Detailed Results ────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Detailed Results"

    headers = [
        "ID", "Category", "Question",
        "Answer",
        "Faithfulness\n(1–5)", "Answer Relevance\n(1–5)", "Completeness\n(1–5)",
        "Avg Score", "Anchor Hit",
        "Latency (s)", "Error", "Judge Reasoning",
    ]
    ws1.append(headers)
    ws1.row_dimensions[1].height = 36

    for cell in ws1[1]:
        _header_style(cell)

    border = _thin_border()
    for i, r in enumerate(results, start=2):
        row_fill = C_ALT_ROW if i % 2 == 0 else C_WHITE
        row_data = [
            r.id, r.category, r.question,
            r.answer,
            r.faithfulness, r.answer_relevance, r.completeness,
            r.avg_score,
            "Yes" if r.anchor_hit else ("No" if r.anchor_hit is False else "N/A"),
            r.latency_s, r.error or "", r.judge_reasoning,
        ]
        ws1.append(row_data)
        for j, cell in enumerate(ws1[i]):
            cell.border    = border
            cell.font      = Font(name="Arial", size=9)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            # Score columns get conditional colour
            if j in (4, 5, 6):   # faithfulness, relevance, completeness
                cell.fill = PatternFill("solid", fgColor=_score_fill(cell.value))
            elif j == 7:          # avg score
                cell.fill = PatternFill("solid", fgColor=_score_fill(cell.value))
            else:
                cell.fill = PatternFill("solid", fgColor=row_fill)
            # Error column in red text
            if j == 10 and cell.value:
                cell.font = Font(name="Arial", size=9, color="C00000")

    _col_widths(ws1, {
        "A": 8, "B": 18, "C": 38, "D": 55,
        "E": 14, "F": 14, "G": 14, "H": 12,
        "I": 12, "J": 12, "K": 22, "L": 45,
    })
    # Freeze pane
    ws1.freeze_panes = "D2"

    # ── Sheet 2 – Category Summary ────────────────────────────────────────
    ws2 = wb.create_sheet("Category Summary")

    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"count": 0, "faith": [], "relevance": [], "complete": [], "latencies": [], "errors": 0, "anchor_hits": 0, "anchor_total": 0}
        d = categories[cat]
        d["count"] += 1
        if r.faithfulness     is not None: d["faith"].append(r.faithfulness)
        if r.answer_relevance is not None: d["relevance"].append(r.answer_relevance)
        if r.completeness     is not None: d["complete"].append(r.completeness)
        if r.latency_s: d["latencies"].append(r.latency_s)
        if r.error: d["errors"] += 1
        if r.anchor_hit is not None:
            d["anchor_total"] += 1
            if r.anchor_hit: d["anchor_hits"] += 1

    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None

    cat_headers = [
        "Category", "# Questions",
        "Avg Faithfulness", "Avg Answer Relevance", "Avg Completeness",
        "Avg Score", "Avg Latency (s)", "Error Rate %", "Anchor Hit Rate %",
    ]
    ws2.append(cat_headers)
    for cell in ws2[1]: _header_style(cell)
    ws2.row_dimensions[1].height = 30

    for i, (cat, d) in enumerate(categories.items(), start=2):
        f   = avg(d["faith"])
        rel = avg(d["relevance"])
        com = avg(d["complete"])
        all_avgs = [x for x in [f, rel, com] if x is not None]
        overall = round(sum(all_avgs)/len(all_avgs), 2) if all_avgs else None
        lat = avg(d["latencies"])
        err_rate = round(d["errors"] / d["count"] * 100, 1) if d["count"] else 0
        anc_rate = round(d["anchor_hits"] / d["anchor_total"] * 100, 1) if d["anchor_total"] else None

        row_fill = C_ALT_ROW if i % 2 == 0 else C_WHITE
        ws2.append([cat, d["count"], f, rel, com, overall, lat, err_rate,
                    anc_rate if anc_rate is not None else "N/A"])
        for j, cell in enumerate(ws2[i]):
            cell.border    = border
            cell.font      = Font(name="Arial", size=9)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if j in (2, 3, 4, 5):
                cell.fill = PatternFill("solid", fgColor=_score_fill(cell.value))
            else:
                cell.fill = PatternFill("solid", fgColor=row_fill)

    _col_widths(ws2, {
        "A": 22, "B": 14, "C": 18, "D": 20, "E": 18,
        "F": 14, "G": 16, "H": 14, "I": 16,
    })

    # ── Sheet 3 – Overall KPIs ────────────────────────────────────────────
    ws3 = wb.create_sheet("Overall KPIs")
    ws3.sheet_view.showGridLines = False

    def kpi_row(ws, label, value, row, value_fmt=None, score=False):
        lc = ws.cell(row=row, column=2, value=label)
        vc = ws.cell(row=row, column=3, value=value)
        lc.font      = Font(name="Arial", size=10, bold=True)
        lc.alignment = Alignment(horizontal="left", vertical="center")
        lc.fill      = PatternFill("solid", fgColor=C_SECTION_FILL)
        vc.font      = Font(name="Arial", size=12, bold=True)
        vc.alignment = Alignment(horizontal="center", vertical="center")
        if score and isinstance(value, (int, float)):
            vc.fill = PatternFill("solid", fgColor=_score_fill(value))
        else:
            vc.fill = PatternFill("solid", fgColor=C_WHITE)
        lc.border = border; vc.border = border
        ws.row_dimensions[row].height = 22

    ws3.column_dimensions["A"].width = 3
    ws3.column_dimensions["B"].width = 35
    ws3.column_dimensions["C"].width = 20

    ws3.merge_cells("B1:C1")
    title_cell = ws3["B1"]
    title_cell.value     = "📊  NIFTY RAG Chatbot — Evaluation Summary"
    title_cell.font      = Font(name="Arial", size=14, bold=True, color=C_HEADER_FONT)
    title_cell.fill      = PatternFill("solid", fgColor=C_HEADER_FILL)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 32

    # Compute KPIs
    all_faith   = [r.faithfulness     for r in results if r.faithfulness     is not None]
    all_rel     = [r.answer_relevance for r in results if r.answer_relevance is not None]
    all_comp    = [r.completeness     for r in results if r.completeness     is not None]
    all_lat     = [r.latency_s        for r in results if r.latency_s]
    all_avgs    = [r.avg_score        for r in results if r.avg_score        is not None]
    errors      = [r for r in results if r.error]
    anchor_q    = [r for r in results if r.anchor_hit is not None]
    anchor_hit  = [r for r in anchor_q if r.anchor_hit]

    kpi_row(ws3, "Total Questions Evaluated",   len(results),                          row=3)
    kpi_row(ws3, "Questions With Errors",        len(errors),                           row=4)
    kpi_row(ws3, "Error Rate",                   f"{round(len(errors)/len(results)*100,1)}%", row=5)
    kpi_row(ws3, "─── Retrieval ───────────────", "", row=6)
    kpi_row(ws3, "Anchor Hit Rate",              f"{round(len(anchor_hit)/len(anchor_q)*100,1)}%" if anchor_q else "N/A", row=7)
    kpi_row(ws3, "Avg Latency (s)",              round(avg(all_lat) or 0, 2),           row=8)
    kpi_row(ws3, "P90 Latency (s)",              round(sorted(all_lat)[int(len(all_lat)*0.9)] if all_lat else 0, 2), row=9)
    kpi_row(ws3, "─── LLM-Judge Scores ────────", "", row=10)
    kpi_row(ws3, "Avg Faithfulness (1–5)",       round(avg(all_faith) or 0, 2),         row=11, score=True)
    kpi_row(ws3, "Avg Answer Relevance (1–5)",   round(avg(all_rel) or 0, 2),           row=12, score=True)
    kpi_row(ws3, "Avg Completeness (1–5)",       round(avg(all_comp) or 0, 2),          row=13, score=True)
    kpi_row(ws3, "Overall Avg Score (1–5)",      round(avg(all_avgs) or 0, 2),          row=14, score=True)

    ws3.row_dimensions[6].height  = 16
    ws3.row_dimensions[10].height = 16

    # ── Sheet 4 – Score Distribution chart data ───────────────────────────
    ws4 = wb.create_sheet("Charts Data")
    ws4.append(["Score Band", "Count", "% of Total"])
    bands = {"1 (Very Poor)": 0, "2 (Poor)": 0, "3 (Fair)": 0, "4 (Good)": 0, "5 (Excellent)": 0}
    for r in results:
        if r.avg_score is not None:
            band = min(5, max(1, round(r.avg_score)))
            key = {1: "1 (Very Poor)", 2: "2 (Poor)", 3: "3 (Fair)", 4: "4 (Good)", 5: "5 (Excellent)"}[band]
            bands[key] += 1
    total_scored = sum(bands.values())
    for band, cnt in bands.items():
        ws4.append([band, cnt, f"=B{ws4.max_row}/B{ws4.max_row - 4 + 1 + list(bands.keys()).index(band) + 1 - list(bands.keys()).index(band)}"])

    # Fix the percentage formula properly
    for i, (band, cnt) in enumerate(bands.items(), start=2):
        ws4[f"C{i}"] = f"=B{i}/{total_scored}" if total_scored else 0
        ws4[f"C{i}"].number_format = "0.0%"

    # Add bar chart
    chart = BarChart()
    chart.type        = "col"
    chart.title       = "Score Distribution (Avg Score)"
    chart.y_axis.title = "Number of Questions"
    chart.x_axis.title = "Score Band"
    chart.shape = 4
    chart.width  = 18
    chart.height = 12

    data_ref = Reference(ws4, min_col=2, min_row=1, max_row=6)
    cats_ref = Reference(ws4, min_col=1, min_row=2, max_row=6)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws4.add_chart(chart, "E2")

    wb.save(out_path)
    print(f"\n✅ Results exported to: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Evaluate NIFTY Graph RAG chatbot")
    p.add_argument("--host",        default="http://127.0.0.1:8000", help="Backend base URL")
    p.add_argument("--dataset",     default=None, help="Path to custom JSON dataset file")
    p.add_argument("--out",         default="rag_eval_results.xlsx", help="Output Excel file path")
    p.add_argument("--judge-model", default=os.getenv("OLLAMA_MODEL", "llama3.2"), help="LLM model for judge")
    p.add_argument("--timeout",     default=300.0, type=float, help="Per-question HTTP timeout (s)")
    p.add_argument("--concurrency", default=2, type=int, help="Number of parallel requests")
    return p.parse_args()


async def main():
    args = parse_args()

    # Load dataset
    if args.dataset:
        with open(args.dataset) as f:
            dataset = json.load(f)
        print(f"📂 Loaded {len(dataset)} questions from {args.dataset}")
    else:
        dataset = DEFAULT_DATASET
        print(f"📋 Using built-in dataset ({len(dataset)} questions)")

    # Health check
    print(f"\n🔍 Checking bot health at {args.host}...")
    try:
        async with httpx.AsyncClient() as c:
            resp = await c.get(f"{args.host}/health", timeout=10)
            health = resp.json()
        if not health.get("engine_ready"):
            print("⚠️  Warning: engine_ready=False. Bot may still be initialising.")
        else:
            print("✅ Bot is ready.\n")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print("   Proceeding anyway – individual questions may fail.\n")

    print(f"⚡ Running {len(dataset)} evaluations  (concurrency={args.concurrency})…\n")
    results = await run_evaluations(
        dataset     = dataset,
        host        = args.host,
        judge_model = args.judge_model,
        timeout     = args.timeout,
        concurrency = args.concurrency,
    )

    # Console summary
    scored = [r for r in results if r.avg_score is not None]
    errors = [r for r in results if r.error]
    print("\n" + "="*55)
    print(f"  Questions : {len(results)}")
    print(f"  Errors    : {len(errors)}")
    if scored:
        avgs = [r.avg_score for r in scored]
        print(f"  Avg Score : {round(sum(avgs)/len(avgs), 2)} / 5")
    print("="*55)

    build_excel(results, args.out)


if __name__ == "__main__":
    asyncio.run(main())
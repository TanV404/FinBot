"""
main.py — NIFTY FinBot v2.2

History awareness is implemented at two levels:
  1. LangChain level  — RunnableWithMessageHistory injects the full SQLite
     message log into every LLM call so the model always has prior context.
  2. API level        — /history/{id} lets the frontend reload a past session
     so the user can visually continue where they left off.

Both survive server restarts because SQLite is written to disk.

Endpoints
─────────
  POST   /chat                  { message, session_id } → { answer, session_id }
  GET    /health
  GET    /capabilities
  GET    /sessions              list all sessions with preview + count
  GET    /history/{session_id}  full message list for one session
  DELETE /history/{session_id}  wipe one session
  DELETE /history               wipe ALL sessions  ⚠️  irreversible
  GET    /eval/questions        sample evaluation questions with expected behaviour
"""

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from retriever import HybridNiftyRetriever

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE           = Path(__file__).resolve().parent
_DEFAULT_GRAPH  = str(_HERE.parent / "data" / "networkx" / "nifty_graph.pkl")
_DEFAULT_CHROMA = str(_HERE.parent / "data" / "chromadb")
_DEFAULT_DB     = str(_HERE / "nifty_chat_history.db")   # plain file path, NOT sqlite:// URI

nifty_bot: RunnableWithMessageHistory | None = None
_db_path: str = _DEFAULT_DB   # absolute path to the SQLite file


# ── Capabilities manifest ──────────────────────────────────────────────────────
CAPABILITIES = {
    "can_answer": [
        "Company profiles for all 50 NIFTY companies",
        "CEO / MD and key leadership for each company",
        "Sector and industry classification",
        "Quarterly financials: Revenue, Net Income, Net Debt, Total Assets",
        "Major shareholders and institutional holding percentages",
        "Headquarters location",
        "Company history and founding (Wikipedia)",
        "Cross-sector comparisons (e.g. top companies by revenue in a sector)",
        "Multi-hop relationships (e.g. 'Which companies does LIC invest in?')",
    ],
    "cannot_answer": [
        "Live stock prices or intraday / real-time data",
        "News published after the knowledge base was built",
        "Companies outside the NIFTY 50 index",
        "Analyst ratings or buy/sell recommendations",
        "Options, futures, or derivatives data",
        "Tax advice or investment advice of any kind",
    ],
}

_CAN    = "\n".join(f"✅ {c}" for c in CAPABILITIES["can_answer"])
_CANNOT = "\n".join(f"❌ {c}" for c in CAPABILITIES["cannot_answer"])


# ── Evaluation questions ───────────────────────────────────────────────────────
EVAL_QUESTIONS = [
    # ── Tier 1: factual / single-hop ──────────────────────────────────────────
    {
        "id": "F1", "tier": "factual",
        "question": "Who is the CEO of Reliance Industries?",
        "expected_contains": ["Mukesh Ambani"],
        "must_not_contain": ["I don't have", "not in graph"],
        "max_words": 60,
    },
    {
        "id": "F2", "tier": "factual",
        "question": "Which sector does TCS belong to?",
        "expected_contains": ["Information Technology", "IT"],
        "must_not_contain": [],
        "max_words": 60,
    },
    {
        "id": "F3", "tier": "factual",
        "question": "Where is HDFC Bank headquartered?",
        "expected_contains": ["Mumbai"],
        "must_not_contain": [],
        "max_words": 60,
    },
    {
        "id": "F4", "tier": "factual",
        "question": "What was TCS's net income in the most recent quarter?",
        "expected_contains": ["₹", "Bn", "Billion", "crore"],
        "must_not_contain": ["I don't have", "not available"],
        "max_words": 80,
    },

    # ── Tier 2: multi-hop / relational ────────────────────────────────────────
    {
        "id": "M1", "tier": "multi-hop",
        "question": "Which NIFTY 50 companies are in the Financial Services sector?",
        "expected_contains": ["HDFC", "ICICI", "Kotak", "SBI", "Axis"],
        "must_not_contain": [],
        "max_words": 150,
        "note": "Should return a bulleted list",
    },
    {
        "id": "M2", "tier": "multi-hop",
        "question": "Which companies does LIC invest in from the NIFTY 50?",
        "expected_contains": [],
        "must_not_contain": [],
        "max_words": 150,
        "note": "Tests INVESTS_IN graph edge traversal",
    },
    {
        "id": "M3", "tier": "multi-hop",
        "question": "Compare the revenue of Reliance and TCS.",
        "expected_contains": ["RELIANCE", "TCS", "₹"],
        "must_not_contain": ["I don't have"],
        "max_words": 120,
    },

    # ── Tier 3: history-aware (must be run in sequence) ───────────────────────
    {
        "id": "H1", "tier": "history",
        "question": "Tell me about Infosys.",
        "expected_contains": ["Infosys", "IT", "Bengaluru"],
        "must_not_contain": [],
        "max_words": 120,
        "note": "Ask this first in a session",
    },
    {
        "id": "H2", "tier": "history",
        "question": "Who founded it?",   # 'it' refers to Infosys from H1
        "expected_contains": ["Narayana Murthy", "Murthy"],
        "must_not_contain": ["I don't understand", "which company"],
        "max_words": 80,
        "note": "Depends on H1 being in history — tests pronoun resolution",
    },
    {
        "id": "H3", "tier": "history",
        "question": "How does its revenue compare to TCS?",   # 'its' = Infosys
        "expected_contains": ["Infosys", "TCS", "₹"],
        "must_not_contain": ["which company", "unclear"],
        "max_words": 120,
        "note": "Multi-hop + history in same question",
    },

    # ── Tier 4: out-of-scope (bot must decline gracefully) ────────────────────
    {
        "id": "O1", "tier": "out-of-scope",
        "question": "What is the current stock price of Reliance?",
        "expected_contains": ["real-time", "live", "NSE", "BSE", "Moneycontrol"],
        "must_not_contain": ["₹"],   # must NOT invent a price
        "max_words": 60,
    },
    {
        "id": "O2", "tier": "out-of-scope",
        "question": "Should I buy HDFC Bank stock?",
        "expected_contains": ["advice", "recommend", "financial advisor"],
        "must_not_contain": ["you should buy", "I recommend buying"],
        "max_words": 60,
    },
    {
        "id": "O3", "tier": "out-of-scope",
        "question": "Tell me about Apple Inc.",
        "expected_contains": ["NIFTY 50", "knowledge base", "not"],
        "must_not_contain": ["Tim Cook", "iPhone", "California"],
        "max_words": 60,
    },

    # ── Tier 5: formatting checks ─────────────────────────────────────────────
    {
        "id": "R1", "tier": "formatting",
        "question": "List all NIFTY 50 companies in the IT sector.",
        "expected_contains": ["•", "TCS", "Infosys", "Wipro"],
        "must_not_contain": [],
        "max_words": 200,
        "note": "Response must use bullet points (•)",
    },
    {
        "id": "R2", "tier": "formatting",
        "question": "What is Wipro's net debt?",
        "expected_contains": ["₹", "as of", "Bn"],
        "must_not_contain": [],
        "max_words": 60,
        "note": "Must include date and unit",
    },
]


# ── SQLite helper ──────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    return sqlite3.connect(_db_path)

def _init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id TEXT PRIMARY KEY,
                summary TEXT,
                msg_count INTEGER
            )
        """)
_init_db()


def _get_session_history(session_id: str) -> SQLChatMessageHistory:
    """
    Factory called by RunnableWithMessageHistory on every /chat request.

    Using connection_string (sqlite:// URI) so LangChain creates and manages
    the table automatically. The same DB file is used by our raw sqlite3 calls
    in the /sessions and /history endpoints.

    WHY THIS PERSISTS ACROSS RESTARTS:
      SQLite writes to disk immediately. When the server restarts, LangChain
      reads the same file and re-injects the full history into the next LLM
      call, so the model sees all prior turns from that session.
    """
    return SQLChatMessageHistory(
        session_id=session_id,
        connection_string=f"sqlite:///{_db_path}",
    )


# ── LLM factory ───────────────────────────────────────────────────────────────

def _build_llm():
    groq_key   = os.getenv("GROQ_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    # if groq_key:
    #     from langchain_groq import ChatGroq
    #     print("  LLM → Groq / llama-3.3-70b-versatile")
    #     return ChatGroq(model="openai/gpt-oss-20b", api_key=groq_key,
    #                     temperature=0, max_tokens=512)
    # if google_key:
    #     from langchain_google_genai import ChatGoogleGenerativeAI
    #     print("  LLM → Gemini 2.0 Flash")
    #     return ChatGoogleGenerativeAI(model="gemini-2.0-flash",
    #                                   google_api_key=google_key,
    #                                   temperature=0, max_output_tokens=1200)
    from langchain_ollama import ChatOllama
    print("  LLM → Ollama / llama3.2:3b  (local fallback — set GROQ_API_KEY for best results)")
    return ChatOllama(model="llama3.2:3b", base_url="http://localhost:11434",
                      temperature=0, num_predict=1200)


# ── Community retriever ────────────────────────────────────────────────────────

class CommunityRetriever(BaseRetriever):
    file_path: str

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        try:
            with open(self.file_path) as f:
                data = json.load(f)
        except Exception:
            return []
        q      = query.lower()
        scored = [(sum(1 for n in c.get("nodes", []) if str(n).lower() in q), c)
                  for c in data]
        scored = sorted([(s, c) for s, c in scored if s > 0], key=lambda x: x[0], reverse=True)
        return [Document(page_content=f"[Community Summary]\n{c.get('summary', '')}",
                         metadata={"source": "community"})
                for _, c in scored[:2]]


class CombinedRetriever(BaseRetriever):
    primary:   BaseRetriever
    secondary: BaseRetriever

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        return self.primary.invoke(query) + self.secondary.invoke(query)


# ── Chain ──────────────────────────────────────────────────────────────────────

def init_chain() -> RunnableWithMessageHistory:
    graph_path  = os.getenv("NETWORKX_GRAPH_PATH", _DEFAULT_GRAPH)
    chroma_path = os.getenv("CHROMA_PATH",          _DEFAULT_CHROMA)

    llm = _build_llm()

    retriever = CombinedRetriever(
        primary=HybridNiftyRetriever(graph_path=str(graph_path),
                                     chroma_path=str(chroma_path)),
        secondary=CommunityRetriever(
            file_path=str(_HERE.parent / "data" / "communities" / "community_summaries.json")
        ),
    )

    # ── Prompt 1: query rewriter ───────────────────────────────────────────────
    # This is the key to history awareness in retrieval.
    # Before hitting the retriever, the LLM rewrites the user's latest message
    # into a fully self-contained query using chat_history.
    # Example: "Who founded it?" + history → "Who founded Infosys?"
    contextualise_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a query rewriter for a NIFTY 50 financial knowledge base. "
         "Using the conversation history, rewrite the user's latest message as a "
         "fully self-contained, specific search query:\n"
         "• Resolve ALL pronouns (it, they, its, their, the company, etc.) to the "
         "actual company/sector name mentioned in history.\n"
         "• If the user asks about 'the most recent' or 'latest' data, add the phrase "
         "'most recent quarter' to the query.\n"
         "• If no history exists or the message is already self-contained, return it unchanged.\n"
         "Output ONLY the rewritten query — no explanation, no punctuation prefix.\n\n"
         "PREVIOUS CHAT SUMMARY:\n{chat_summary}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # ── Prompt 2: answer generator ────────────────────────────────────────────
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are FinBot, a focused NIFTY 50 equity research assistant.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE — HARD RULES (never break these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT YOU KNOW:
{_CAN}

WHAT YOU DO NOT KNOW (decline immediately — do NOT attempt an answer):
{_CANNOT}

OUT-OF-SCOPE COMPANIES: If the user asks about a company NOT in the NIFTY 50 index
(e.g. Apple, Google, Samsung, Tesla, Reliance Power, Paytm, Zomato*), respond ONLY:
"[Company] is not in my NIFTY 50 knowledge base. I can only answer questions about
the 50 companies listed on India's NIFTY 50 index. Want me to list them?"
Never provide any facts about out-of-scope companies from your training knowledge.

DECLINE FORMAT for out-of-scope data types (stock price, advice, derivatives):
"I don't have that data — [one sentence reason]. Check NSE / BSE / Moneycontrol."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECENCY RULE — CRITICAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Financial data spans multiple quarters. ALWAYS use the MOST RECENT non-NaN date
  from the context unless the user explicitly asks for a specific period.
• The most recent quarter is the one with the LARGEST (latest) date string, e.g.
  2025-12-31 is more recent than 2024-12-31.
• State the date explicitly: "as of Dec 2025" or "Q3 FY26 (Dec 2025)".
• If showing trend, list quarters newest-first: Dec 2025 → Sep 2025 → Jun 2025.
• NEVER report a 2022 or 2023 figure as "recent" — these are historical.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANSWER FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Simple facts (CEO, sector, HQ)   → 1–2 sentences. Include one interesting detail.
• Financial figures                 → Always state metric + value + date + unit.
  Example: "Total Revenue: ₹235.56 Bn as of Dec 2025 (up from ₹226.97 Bn in Sep 2025)."
• Trend / multi-quarter            → Bullet each quarter: "• Dec 2025: ₹235.56 Bn"
• Lists of 3+ items                → Bullet points with • prefix, one item per line.
• Comparisons                      → Parallel bullets or two-column layout.
• Multi-company / complex          → Short summary paragraph + bullets.
• Never pad with financial-advisor disclaimers.
• Never repeat the question back.
• Never invent figures, names, or dates not present in the context.
• If data is absent from context → "I don't have that specific data in my knowledge base."
• Complete every response fully — never trail off or cut short mid-sentence.
• Summarize the information in 100-150 words only
• Ask one follow-up question at the end of the response to keep the conversation going
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHAT SUMMARY (High-level context of the conversation so far)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{chat_summary}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT (graph facts + Wikipedia + community summaries):
{{context}}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    history_retriever = create_history_aware_retriever(llm, retriever, contextualise_prompt)
    rag_chain         = create_retrieval_chain(
                            history_retriever,
                            create_stuff_documents_chain(llm, qa_prompt))

    return RunnableWithMessageHistory(
        rag_chain,
        _get_session_history,          # reads/writes SQLite on every call
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )


# ── App ────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global nifty_bot
    print("⏳ Initialising FinBot …")
    try:
        nifty_bot = init_chain()
        print("✅ FinBot ready.")
    except Exception as exc:
        print(f"❌ Init failed: {exc}")
    yield
    print("👋 Shutting down.")


app = FastAPI(title="NIFTY FinBot API", version="2.2", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:    str
    session_id: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Main chat endpoint.  session_id is the key that ties messages together.
    LangChain automatically:
      1. Loads all prior messages for this session_id from SQLite.
      2. Passes them as chat_history to both prompts.
      3. Saves the new human + AI messages back to SQLite after the response.
    """
    if nifty_bot is None:
        raise HTTPException(503, "Bot not ready.")
    try:
        with _conn() as con:
            row = con.execute("SELECT summary FROM session_summaries WHERE session_id=?", (req.session_id,)).fetchone()
            summary = row[0] if row else "No previous summary available."

        result = nifty_bot.invoke(
            {"input": req.message, "chat_summary": summary},
            config={"configurable": {"session_id": req.session_id}},
        )
        return {"answer": result["answer"], "session_id": req.session_id}
    except Exception as exc:
        print(f"Chat error: {exc}")
        raise HTTPException(500, str(exc))


@app.get("/health")
async def health():
    return {"status": "ok", "engine_ready": nifty_bot is not None}


@app.get("/capabilities")
async def capabilities():
    """Returns what FinBot can and cannot answer. Use in the frontend hint panel."""
    return CAPABILITIES


@app.get("/eval/questions")
async def eval_questions():
    """
    Returns the full evaluation suite with tiers, expected outputs, and notes.
    Use this to drive automated or manual testing of the model.
    """
    return {
        "total": len(EVAL_QUESTIONS),
        "tiers": ["factual", "multi-hop", "history", "out-of-scope", "formatting"],
        "questions": EVAL_QUESTIONS,
    }


@app.get("/sessions")
async def list_sessions():
    """
    Lists all sessions ordered most-recent first.
    Returns a preview (first human message) and total message count per session.
    Frontend uses this to render the sidebar conversation list.
    """
    try:
        with _conn() as con:
            rows = con.execute("""
                SELECT   session_id,
                         COUNT(*)  AS total,
                         MIN(id)   AS first_id,
                         (SELECT message FROM message_store ms2 
                          WHERE ms2.session_id = message_store.session_id 
                            AND json_extract(ms2.message,'$.type')='human'
                          ORDER BY id ASC LIMIT 1) AS first_human
                FROM     message_store
                GROUP BY session_id
                ORDER BY first_id DESC
            """).fetchall()
    except sqlite3.OperationalError:
        return {"sessions": []}   # table not created yet

    sessions = []
    for session_id, total, _, raw in rows:
        try:
            preview = json.loads(raw or "{}").get("data", {}).get("content", "")[:80]
        except Exception:
            preview = "Conversation"
        sessions.append({"id": session_id, "preview": preview,
                          "message_count": total})
    return {"sessions": sessions}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    Returns the full ordered message list for a session.
    The frontend calls this when the user clicks a past session in the sidebar
    to restore the visual conversation before continuing.
    Role mapping: LangChain 'human' → 'user', everything else → 'ai'.
    """
    try:
        history = _get_session_history(session_id)
        
        with _conn() as con:
            row = con.execute("SELECT summary, msg_count FROM session_summaries WHERE session_id=?", (session_id,)).fetchone()
            current_count = len(history.messages)
            if (not row or row[1] < current_count) and current_count > 0:
                llm = _build_llm()
                text_history = "\n".join([f"{m.type}: {m.content}" for m in history.messages])
                summary = llm.invoke(f"Summarize the key topics and entities discussed in this conversation concisely:\n\n{text_history}").content
                con.execute("INSERT OR REPLACE INTO session_summaries (session_id, summary, msg_count) VALUES (?, ?, ?)", (session_id, summary, current_count))

        messages = [
            {
                "role": "user" if m.type == "human" else "ai",
                "content": m.content,
            }
            for m in history.messages
        ]
        return {"session_id": session_id, "messages": messages}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.delete("/history/{session_id}")
async def clear_session(session_id: str):
    """Delete all messages for one specific session."""
    try:
        _get_session_history(session_id).clear()
        return {"cleared": True, "session_id": session_id}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.delete("/history")
async def clear_all():
    """
    ⚠️  Deletes ALL sessions permanently.
    Add authentication middleware before exposing this in production.
    """
    try:
        with _conn() as con:
            n = con.execute(
                "SELECT COUNT(DISTINCT session_id) FROM message_store"
            ).fetchone()[0]
            con.execute("DELETE FROM message_store")
        return {"cleared_all": True, "sessions_deleted": n}
    except sqlite3.OperationalError:
        return {"cleared_all": True, "sessions_deleted": 0}
    except Exception as exc:
        raise HTTPException(500, str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
import json
import os
import sys
import sqlite3
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from asyncio import create_task

# Add backend directory to path so imports resolve correctly when run from repository root
sys.path.append(str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory


from langchain_openai import ChatOpenAI

from retriever import HybridNiftyRetriever

os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

load_dotenv()
print("HF_TOKEN loaded:", bool(os.getenv("HF_TOKEN")))

_HERE = Path(__file__).resolve().parent
_DEFAULT_GRAPH  = str(_HERE.parent / "data" / "networkx" / "nifty_graph.pkl")
_DEFAULT_CHROMA = str(_HERE.parent / "data" / "chromadb")

# ─────────────────────────────────────────────
# DB PATH RESOLUTION
# Read CHAT_DB_URL from .env (e.g. sqlite:///./nifty_chat_history.db)
# _db_url  → passed to SQLChatMessageHistory (needs full sqlite:/// URL)
# _db_path → passed to sqlite3.connect()     (needs a plain file path)
# ─────────────────────────────────────────────

_DEFAULT_DB_URL = f"sqlite:///{_HERE / 'nifty_chat_history.db'}"
_db_url: str = os.getenv("CHAT_DB_URL", _DEFAULT_DB_URL)

def _resolve_db_path(url: str) -> str:
    """
    Convert a sqlite:/// URL to a plain OS file path for sqlite3.connect().
    Handles both relative (sqlite:///./file.db) and absolute (sqlite:///C:/...) forms.
    """
    raw = url.replace("sqlite:///", "", 1)   # strip the scheme prefix once
    path = Path(raw)
    if not path.is_absolute():
        # relative paths are resolved from the backend directory
        path = (_HERE / path).resolve()
    return str(path)

_db_path: str = _resolve_db_path(_db_url)

nifty_bot = None
_llm_ref  = None   # kept for background summarization

# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────

def _ensure_db_tables():
    """Create the session_summaries and message_store tables if they don't exist."""
    with sqlite3.connect(_db_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id   TEXT PRIMARY KEY,
                summary      TEXT NOT NULL,
                updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS message_store (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT,
                message      TEXT
            )
        """)
        con.commit()



def _get_session_history(session_id: str) -> SQLChatMessageHistory:
    # SQLChatMessageHistory expects the full sqlite:/// URL
    return SQLChatMessageHistory(
        session_id=session_id,
        connection_string=_db_url,
    )


def _load_summary(session_id: str) -> str | None:
    """Return the stored summary for a session, or None."""
    try:
        with sqlite3.connect(_db_path) as con:
            row = con.execute(
                "SELECT summary FROM session_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _save_summary(session_id: str, summary: str):
    """Upsert a summary for a session."""
    with sqlite3.connect(_db_path) as con:
        con.execute(
            """
            INSERT INTO session_summaries (session_id, summary, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                summary    = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (session_id, summary),
        )
        con.commit()


# ─────────────────────────────────────────────
# BACKGROUND SUMMARIZATION
# ─────────────────────────────────────────────

SUMMARY_PROMPT = """You are a financial research assistant. Summarize the conversation below into a concise paragraph (max 120 words).
Focus on: companies discussed, key financial metrics mentioned, comparisons made, and any conclusions reached.
Write in third-person past tense. Output ONLY the summary text, nothing else.

Conversation:
{conversation}
"""

SUMMARIZE_EVERY_N_TURNS = 4   # summarize after every 4 user turns


async def _maybe_summarize(session_id: str):
    """
    Check if enough new turns have accumulated since last summary.
    If so, generate a fresh summary and persist it in SQLite.
    Runs as a fire-and-forget background task.
    """
    if _llm_ref is None:
        return
    try:
        history = _get_session_history(session_id)
        messages = history.messages
        user_turns = [m for m in messages if m.type == "human"]
        if len(user_turns) == 0 or len(user_turns) % SUMMARIZE_EVERY_N_TURNS != 0:
            return

        transcript = "\n".join(
            f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}"
            for m in messages
        )

        result = await _llm_ref.ainvoke(SUMMARY_PROMPT.format(conversation=transcript))
        summary_text = result.content.strip()

        if summary_text:
            _save_summary(session_id, summary_text)
            print(f"[Summarizer] Session '{session_id}' updated ({len(user_turns)} turns).")
    except Exception as e:
        print(f"[Summarizer] Failed for session '{session_id}': {e}")


# ─────────────────────────────────────────────
# CHAIN BUILDER
# ─────────────────────────────────────────────

def _build_llm():
    # 1. Groq Cloud LLM
    # groq_api_key = os.getenv("GROQ_API_KEY")
    # if groq_api_key:
    #     print("[LLM] Initializing Groq Chat Provider")
    #     from langchain_groq import ChatGroq
    #     return ChatGroq(
    #         api_key=groq_api_key,
    #         model="llama-3.3-70b-versatile",
    #         temperature=0,
    #         max_tokens=1200,
    #     )


    # 2. Gemini Cloud LLM
    # gemini_api_key = os.getenv("GEMINI_API_KEY")
    # if gemini_api_key:
    #     print("[LLM] Initializing Gemini Chat Provider")
    #     from langchain_google_genai import ChatGoogleGenAI
    #     return ChatGoogleGenAI(
    #         api_key=gemini_api_key,
    #         model="gemini-1.5-flash",
    #         temperature=0,
    #         max_output_tokens=1200,
    #     )

    # 3. HuggingFace Router Cloud LLM
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        print("[LLM] Initializing HuggingFace Router Chat Provider")
        return ChatOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=hf_token,
            model="Qwen/Qwen2.5-7B-Instruct:together",
            temperature=0,
            max_tokens=1200,
        )

    # 4. Local Ollama (Default Fallback)
    # print("[LLM] Initializing Local Ollama Chat Provider")
    # return ChatOpenAI(
    #     base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
    #     api_key="ollama",
    #     model=os.getenv("OLLAMA_MODEL", "llama3.2"),
    #     temperature=0,
    #     max_tokens=1200,
    # )


def init_chain():
    global _llm_ref
    graph_path  = os.getenv("NETWORKX_GRAPH_PATH", _DEFAULT_GRAPH)
    chroma_path = os.getenv("CHROMA_PATH", _DEFAULT_CHROMA)

    if not Path(graph_path).exists():
        raise FileNotFoundError(f"❌ Graph missing at {graph_path}")

    llm = _build_llm()
    _llm_ref = llm  # expose for background summarizer

    retriever = HybridNiftyRetriever(graph_path=graph_path, chroma_path=chroma_path)

    # STAGE 1 — Query rewriter: resolves pronouns / references using recent chat history
    contextualise_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Given a chat history and the latest user question, formulate a standalone "
            "query that can be understood without the chat history. Do NOT answer the question.",
        ),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # STAGE 2 — Grounded QA: injects session summary + retrieved context
    qa_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """### IDENTITY
You are FinBot, a high-precision NIFTY 50 analyst. Today's date is May 2026.

### SESSION SUMMARY (prior conversations)
{session_summary}

### STRICT GROUNDING RULES
1. **Context Only**: Use ONLY the provided context. If the answer isn't there, say: "I do not have that data in my records."
2. **Priority**:
   - Use 'Source: Financial Graph' for hard numbers (Revenue, PAT, Debt).
   - Use 'Knowledge Base' for general facts or definitions.
3. **Currency**: Always use '₹' prefix. Format numbers as Cr (Crore) or Bn (Billion).
4. **Recency**: Always prioritize the most recent date found in the context.

### CONTEXT:
{context}
""",
        ),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    history_retriever = create_history_aware_retriever(llm, retriever, contextualise_prompt)

    rag_chain = create_retrieval_chain(
        history_retriever,
        create_stuff_documents_chain(llm, qa_prompt),
    )

    return RunnableWithMessageHistory(
        rag_chain,
        _get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )


# ─────────────────────────────────────────────
# APP LIFECYCLE
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global nifty_bot
    print(f"[DB] Using database at: {_db_path}")
    _ensure_db_tables()
    try:
        nifty_bot = init_chain()
        print("✅ FinBot Ready")
    except Exception as e:
        print(f"❌ Init Failed: {e}")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str


@app.post("/chat")
async def chat(req: ChatRequest):
    if nifty_bot is None:
        raise HTTPException(503, "Bot not ready")
    try:
        summary = _load_summary(req.session_id) or "No prior summary available."

        result = nifty_bot.invoke(
            {"input": req.message, "session_summary": summary},
            config={"configurable": {"session_id": req.session_id}},
        )

        # Fire-and-forget: update summary in background without blocking the response
        create_task(_maybe_summarize(req.session_id))

        return {"answer": result["answer"]}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "engine_ready": nifty_bot is not None}


@app.get("/sessions")
async def list_sessions():
    try:
        with sqlite3.connect(_db_path) as con:
            rows = con.execute("""
                SELECT 
                    s.session_id,
                    COUNT(*) as message_count,
                    (
                        SELECT json_extract(m2.message, '$.data.content')
                        FROM message_store m2
                        WHERE m2.session_id = s.session_id 
                          AND json_extract(m2.message, '$.type') = 'human'
                        ORDER BY m2.id ASC
                        LIMIT 1
                    ) as preview
                FROM message_store s
                GROUP BY s.session_id
                ORDER BY MAX(s.id) DESC
            """).fetchall()

        return {
            "sessions": [
                {
                    "id": r[0],
                    "message_count": r[1],
                    "preview": (r[2] or "New Chat")
                }
                for r in rows
            ]
        }

    except Exception as e:
        print("Error:", e)
        return {"sessions": []}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    history = _get_session_history(session_id)
    return {
        "session_id": session_id,
        "messages": [
            {"role": "user" if m.type == "human" else "ai", "content": m.content}
            for m in history.messages
        ],
    }


@app.get("/summary/{session_id}")
async def get_summary(session_id: str):
    """Return the stored summary for a session."""
    summary = _load_summary(session_id)
    if summary is None:
        raise HTTPException(404, f"No summary found for session '{session_id}'")
    return {"session_id": session_id, "summary": summary}


@app.delete("/history/{session_id}")
async def delete_history(session_id: str):
    """Delete all messages AND the summary for a session."""
    try:
        with sqlite3.connect(_db_path) as con:
            msg_cursor = con.execute(
                "DELETE FROM message_store WHERE session_id = ?", (session_id,)
            )
            con.execute(
                "DELETE FROM session_summaries WHERE session_id = ?", (session_id,)
            )
            con.commit()
            if msg_cursor.rowcount == 0:
                return {
                    "status": "not_found",
                    "message": f"No history found for session {session_id}",
                }
        return {"status": "success", "message": f"History and summary for session {session_id} deleted"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))

@app.delete("/sessions")
async def delete_all_sessions():
    """Delete ALL chat sessions and summaries."""
    try:
        with sqlite3.connect(_db_path) as con:
            con.execute("DELETE FROM message_store")
            con.execute("DELETE FROM session_summaries")
            con.commit()

        return {
            "status": "success",
            "message": "All chats and summaries deleted"
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
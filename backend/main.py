import json
import os
import sys
import traceback
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from asyncio import create_task

# Add backend directory to path so imports resolve correctly when run from repository root
sys.path.append(str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI

from retriever import HybridNiftyRetriever
from auth import verify_token, verify_admin, supabase

os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

load_dotenv()
print("HF_TOKEN loaded:", bool(os.getenv("HF_TOKEN")))

_HERE = Path(__file__).resolve().parent
_DEFAULT_GRAPH  = str(_HERE.parent / "data" / "networkx" / "nifty_graph.pkl")
_DEFAULT_CHROMA = str(_HERE.parent / "data" / "chromadb")

nifty_bot = None
_llm_ref  = None   # kept for background summarization

# ─────────────────────────────────────────────
# LEGACY SQLITE DATABASE HELPER CODE (COMMENTED OUT)
# ─────────────────────────────────────────────
# _DEFAULT_DB_URL = f"sqlite:///{_HERE / 'nifty_chat_history.db'}"
# _db_url: str = os.getenv("CHAT_DB_URL", _DEFAULT_DB_URL)
# def _resolve_db_path(url: str) -> str:
#     raw = url.replace("sqlite:///", "", 1)
#     path = Path(raw)
#     if not path.is_absolute():
#         path = (_HERE / path).resolve()
#     return str(path)
# _db_path: str = _resolve_db_path(_db_url)
# def _ensure_db_tables():
#     with sqlite3.connect(_db_path) as con:
#         con.execute("CREATE TABLE IF NOT EXISTS session_summaries ...")
#         con.execute("CREATE TABLE IF NOT EXISTS message_store ...")
#         con.commit()
# def _get_session_history(session_id: str) -> SQLChatMessageHistory:
#     return SQLChatMessageHistory(session_id=session_id, connection_string=_db_url)
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# SUPABASE DATABASE HELPERS
# ─────────────────────────────────────────────

def _load_summary(session_id: str, user_id: str) -> str | None:
    """Return the stored summary for a session from Supabase, or None."""
    try:
        res = supabase.table("session_summaries") \
            .select("summary") \
            .eq("session_id", session_id) \
            .eq("user_id", user_id) \
            .execute()
        return res.data[0]["summary"] if res.data else None
    except Exception as e:
        print(f"[Supabase DB] Summary load failed: {e}")
        return None


def _save_summary(session_id: str, summary: str, user_id: str):
    """Upsert a summary for a session in Supabase."""
    try:
        supabase.table("session_summaries").upsert({
            "session_id": session_id,
            "summary": summary,
            "user_id": user_id,
            "updated_at": "now()"
        }).execute()
    except Exception as e:
        print(f"[Supabase DB] Summary save failed: {e}")


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


async def _maybe_summarize(session_id: str, user_id: str):
    """
    Check if enough new turns have accumulated since last summary.
    If so, generate a fresh summary and persist it in Supabase.
    Runs as a fire-and-forget background task.
    """
    if _llm_ref is None:
        return
    try:
        # Load message log from Supabase
        res = supabase.table("messages") \
            .select("role", "content") \
            .eq("session_id", session_id) \
            .eq("user_id", user_id) \
            .order("created_at", desc=False) \
            .execute()

        messages = res.data
        user_turns = [m for m in messages if m["role"] == "user"]
        if len(user_turns) == 0 or len(user_turns) % SUMMARIZE_EVERY_N_TURNS != 0:
            return

        transcript = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in messages
        )

        result = await _llm_ref.ainvoke(SUMMARY_PROMPT.format(conversation=transcript))
        summary_text = result.content.strip()

        if summary_text:
            _save_summary(session_id, summary_text, user_id)
            print(f"[Summarizer] Session '{session_id}' updated ({len(user_turns)} turns).")
    except Exception as e:
        print(f"[Summarizer] Failed for session '{session_id}': {e}")


# ─────────────────────────────────────────────
# DYNAMIC FALLBACK CHAT MODEL WRAPPER
# ─────────────────────────────────────────────
from typing import List, Any
from langchain_core.outputs import ChatResult, ChatGeneration

class FallbackChatModel(BaseChatModel):
    models: List[Any]
    timeout: float = 15.0

    @property
    def _llm_type(self) -> str:
        return "fallback-chat-model"

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        last_err = None
        for model in self.models:
            try:
                res = model.invoke(messages, stop=stop, config=run_manager.get_child() if run_manager else None, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=res)])
            except Exception as e:
                print(f"[FallbackLLM] Sync fallback step failed for {model}: {e}")
                last_err = e
        raise last_err or RuntimeError("All models in fallback chain failed")

    async def _agenerate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        last_err = None
        for model in self.models:
            try:
                print(f"[FallbackLLM] Attempting async invoke on {model} (timeout={self.timeout}s)...")
                res = await asyncio.wait_for(
                    model.ainvoke(messages, stop=stop, config=run_manager.get_child() if run_manager else None, **kwargs),
                    timeout=self.timeout
                )
                return ChatResult(generations=[ChatGeneration(message=res)])
            except Exception as e:
                print(f"[FallbackLLM] Async fallback step failed for {model}: {e}")
                last_err = e
        raise last_err or RuntimeError("All models in fallback chain failed")


# ─────────────────────────────────────────────
# MODEL BUILDERS
# ─────────────────────────────────────────────

def _build_fallback_llm(model_id_groq: str, model_id_gemini: str, model_id_ollama: str) -> FallbackChatModel:
    models = []
    
    # 1. Groq Cloud LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        print(f"[LLM Builder] Adding Groq model {model_id_groq} to fallback list")
        from langchain_groq import ChatGroq
        models.append(ChatGroq(
            api_key=groq_api_key,
            model=model_id_groq,
            temperature=0,
        ))

    # 2. Gemini Cloud LLM
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        print(f"[LLM Builder] Adding Gemini model {model_id_gemini} to fallback list")
        from langchain_google_genai import ChatGoogleGenerativeAI
        models.append(ChatGoogleGenerativeAI(
            api_key=gemini_api_key,
            model=model_id_gemini,
            temperature=0,
        ))

    # 3. Local Ollama (Default Fallback)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    print(f"[LLM Builder] Adding local Ollama model {model_id_ollama} to fallback list")
    models.append(ChatOpenAI(
        base_url=ollama_base_url,
        api_key="ollama",
        model=model_id_ollama,
        temperature=0,
    ))

    return FallbackChatModel(models=models, timeout=15.0)


def init_chain():
    global _llm_ref
    graph_path  = os.getenv("NETWORKX_GRAPH_PATH", _DEFAULT_GRAPH)
    chroma_path = os.getenv("CHROMA_PATH", _DEFAULT_CHROMA)

    if not Path(graph_path).exists():
        raise FileNotFoundError(f"❌ Graph missing at {graph_path}")

    # Build fallback models
    fast_llm = _build_fallback_llm(
        model_id_groq="openai/gpt-oss-20b",
        model_id_gemini="gemini-1.5-flash",
        model_id_ollama=os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    )
    
    qa_llm = _build_fallback_llm(
        model_id_groq="qwen/qwen3.6-27b",
        model_id_gemini="gemini-1.5-flash",
        model_id_ollama=os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    )
    
    _llm_ref = qa_llm  # expose for background summarizer

    # Hybrid retriever
    retriever = HybridNiftyRetriever(graph_path=graph_path, chroma_path=chroma_path, llm=fast_llm)

    # STAGE 1 — Query rewriter: uses fast_llm
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

    history_retriever = create_history_aware_retriever(fast_llm, retriever, contextualise_prompt)

    rag_chain = create_retrieval_chain(
        history_retriever,
        create_stuff_documents_chain(qa_llm, qa_prompt),
    )

    return rag_chain


# ─────────────────────────────────────────────
# APP LIFECYCLE
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global nifty_bot
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
async def chat(req: ChatRequest, user: dict = Depends(verify_token)):
    if nifty_bot is None:
        raise HTTPException(503, "Bot not ready")
    try:
        user_id = user["id"]
        summary = _load_summary(req.session_id, user_id) or "No prior summary available."

        # Fetch history from Supabase
        hist_res = supabase.table("messages") \
            .select("role", "content") \
            .eq("session_id", req.session_id) \
            .eq("user_id", user_id) \
            .order("created_at", desc=False) \
            .execute()

        chat_history = []
        for m in hist_res.data:
            if m["role"] == "user":
                chat_history.append(HumanMessage(content=m["content"]))
            else:
                chat_history.append(AIMessage(content=m["content"]))

        # Invoke the RAG chain
        result = nifty_bot.invoke(
            {
                "input": req.message,
                "session_summary": summary,
                "chat_history": chat_history
            }
        )
        answer = result["answer"]

        # Insert new messages to Supabase
        supabase.table("messages").insert([
            {"session_id": req.session_id, "role": "user", "content": req.message, "user_id": user_id},
            {"session_id": req.session_id, "role": "assistant", "content": answer, "user_id": user_id}
        ]).execute()

        # Fire-and-forget: update summary in background without blocking the response
        create_task(_maybe_summarize(req.session_id, user_id))

        return {"answer": answer}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "engine_ready": nifty_bot is not None}


@app.get("/sessions")
async def list_sessions(user: dict = Depends(verify_token)):
    try:
        # Load user messages
        res = supabase.table("messages") \
            .select("id, session_id, role, content") \
            .eq("user_id", user["id"]) \
            .execute()
        
        # Group sessions in Python
        sessions_map = {}
        for m in res.data:
            sid = m["session_id"]
            if sid not in sessions_map:
                sessions_map[sid] = {
                    "id": sid,
                    "messages": [],
                    "max_id": 0
                }
            sessions_map[sid]["messages"].append(m)
            if m["id"] > sessions_map[sid]["max_id"]:
                sessions_map[sid]["max_id"] = m["id"]

        sessions_list = []
        for sid, data in sessions_map.items():
            preview = "New Chat"
            human_messages = [m for m in data["messages"] if m["role"] == "user"]
            if human_messages:
                human_messages.sort(key=lambda x: x["id"])
                preview = human_messages[0]["content"]

            sessions_list.append({
                "id": sid,
                "message_count": len(data["messages"]),
                "preview": preview,
                "max_id": data["max_id"]
            })

        # Sort sessions: most recent first
        sessions_list.sort(key=lambda x: x["max_id"], reverse=True)

        return {
            "sessions": [
                {"id": s["id"], "message_count": s["message_count"], "preview": s["preview"]}
                for s in sessions_list
            ]
        }
    except Exception as e:
        print("Error listing sessions:", e)
        return {"sessions": []}


@app.get("/history/{session_id}")
async def get_history(session_id: str, user: dict = Depends(verify_token)):
    try:
        res = supabase.table("messages") \
            .select("role", "content") \
            .eq("session_id", session_id) \
            .eq("user_id", user["id"]) \
            .order("created_at", desc=False) \
            .execute()

        return {
            "session_id": session_id,
            "messages": [
                {"role": "user" if m["role"] == "user" else "ai", "content": m["content"]}
                for m in res.data
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/summary/{session_id}")
async def get_summary(session_id: str, user: dict = Depends(verify_token)):
    """Return the stored summary for a session."""
    summary = _load_summary(session_id, user["id"])
    if summary is None:
        raise HTTPException(404, f"No summary found for session '{session_id}'")
    return {"session_id": session_id, "summary": summary}


@app.delete("/history/{session_id}")
async def delete_history(session_id: str, user: dict = Depends(verify_token)):
    """Delete all messages AND the summary for a session."""
    try:
        user_id = user["id"]
        # Delete messages and summaries
        supabase.table("messages").delete().eq("session_id", session_id).eq("user_id", user_id).execute()
        supabase.table("session_summaries").delete().eq("session_id", session_id).eq("user_id", user_id).execute()
        return {"status": "success", "message": f"History and summary for session {session_id} deleted"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.delete("/sessions")
async def delete_all_sessions(admin: dict = Depends(verify_admin)):
    """Delete ALL chat sessions and summaries (Requires Admin Claim)."""
    try:
        # Bypass table wiping prevention in postgrest by filtering on session_id unequal to a dummy value
        supabase.table("messages").delete().neq("session_id", "_dummy_session_id_wipe_").execute()
        supabase.table("session_summaries").delete().neq("session_id", "_dummy_session_id_wipe_").execute()

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
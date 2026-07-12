import os
import json
import glob
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

BASE_DIR = Path(__file__).resolve().parent.parent
WIKI_DIR = BASE_DIR / "data" / "docs" / "wiki"
COMMUNITIES_FILE = BASE_DIR / "data" / "communities" / "community_summaries.json"

def safe_read(path: Path) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8", errors="replace")

def ingest_all():
    print("🧹 Clearing existing documents from Supabase...")
    try:
        supabase.table("documents").delete().neq("id", -1).execute()
        print("✅ Documents table cleared.")
    except Exception as e:
        print(f"⚠️ Error clearing table (make sure it exists): {e}")

    # Build local embedding client (same as ingest.py)
    print("🧠 Initializing BAAI/bge-small-en-v1.5 embeddings locally...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
    )

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    all_rows = []

    # 1. Process Wiki Chunks
    print("📂 Processing Wikipedia Files...")
    wiki_files = sorted(WIKI_DIR.glob("*_wiki.txt"))
    for wiki_file in wiki_files:
        symbol = wiki_file.stem.split("_")[0].upper()
        text = safe_read(wiki_file)
        chunks = splitter.split_text(text)
        
        print(f"   Splitting {wiki_file.name} into {len(chunks)} chunks...")
        
        # Embed chunks in batch
        chunk_embeddings = embeddings.embed_documents(chunks)
        
        for i, (chunk, emb) in enumerate(zip(chunks, chunk_embeddings)):
            all_rows.append({
                "content": chunk,
                "embedding": emb,
                "metadata": {
                    "source": "vector_kb",
                    "symbol": symbol
                }
            })

    # 2. Process Community Summaries
    if COMMUNITIES_FILE.exists():
        print("📂 Processing Community Summaries...")
        with open(COMMUNITIES_FILE, "r", encoding="utf-8") as f:
            summaries = json.load(f)
            
        summary_texts = []
        summary_metadatas = []
        for summary in summaries:
            content = (
                f"Community {summary['community_id']} Summary: {summary['summary']}\n\n"
                f"Nodes in community: {', '.join(str(n) for n in summary['nodes'])}"
            )
            metadata = {
                "source": "community_summary",
                "community_id": summary["community_id"],
                "node_count": len(summary["nodes"])
            }
            summary_texts.append(content)
            summary_metadatas.append(metadata)
            
        if summary_texts:
            print(f"   Embedding {len(summary_texts)} community summaries...")
            summary_embeddings = embeddings.embed_documents(summary_texts)
            for chunk, emb, meta in zip(summary_texts, summary_embeddings, summary_metadatas):
                all_rows.append({
                    "content": chunk,
                    "embedding": emb,
                    "metadata": meta
                })

    # 3. Bulk Upload to Supabase in batches of 100
    if all_rows:
        batch_size = 100
        print(f"📤 Bulk uploading {len(all_rows)} documents to Supabase pgvector in batches of {batch_size}...")
        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i + batch_size]
            supabase.table("documents").insert(batch).execute()
            print(f"   Uploaded batch {i // batch_size + 1}/{((len(all_rows) - 1) // batch_size) + 1}...")
        print("✅ Ingestion Complete!")
    else:
        print("⚠️ No documents to ingest.")

if __name__ == "__main__":
    ingest_all()

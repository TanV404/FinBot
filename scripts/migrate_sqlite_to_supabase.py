import os
import sqlite3
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Path to SQLite DB
BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB = BASE_DIR / "backend" / "nifty_chat_history.db"

# Default migration user UUID
DEFAULT_USER_ID = os.getenv("MIGRATION_USER_ID", "00000000-0000-0000-0000-000000000000")

def migrate():
    if not SQLITE_DB.exists():
        print(f"❌ SQLite database not found at {SQLITE_DB}")
        return

    con = sqlite3.connect(str(SQLITE_DB))
    con.row_factory = sqlite3.Row

    # 1. Migrate Session Summaries
    print("⏳ Migrating session summaries...")
    try:
        summaries = con.execute("SELECT session_id, summary, updated_at FROM session_summaries").fetchall()
        print(f"   Found {len(summaries)} summaries in SQLite.")
        
        for row in summaries:
            data = {
                "session_id": row["session_id"],
                "summary": row["summary"],
                "updated_at": row["updated_at"],
                "user_id": DEFAULT_USER_ID
            }
            supabase.table("session_summaries").upsert(data).execute()
        print("✅ Session summaries migrated successfully.")
    except Exception as e:
        print(f"⚠️ Error migrating summaries: {e}")

    # 2. Migrate Messages
    print("⏳ Migrating messages...")
    try:
        messages = con.execute("SELECT id, session_id, message FROM message_store").fetchall()
        print(f"   Found {len(messages)} messages in SQLite.")
        
        batch = []
        for row in messages:
            try:
                msg_data = json.loads(row["message"])
                role_type = msg_data.get("type")
                role = "user" if role_type == "human" else "assistant"
                content = msg_data.get("data", {}).get("content", "")
                
                batch.append({
                    "session_id": row["session_id"],
                    "role": role,
                    "content": content,
                    "user_id": DEFAULT_USER_ID
                })
            except Exception as parse_err:
                print(f"   ⚠️ Error parsing message row ID {row['id']}: {parse_err}")

            # Batch insert in chunks of 100
            if len(batch) >= 100:
                supabase.table("messages").insert(batch).execute()
                batch = []
                
        if batch:
            supabase.table("messages").insert(batch).execute()
            
        print("✅ Messages migrated successfully.")
    except Exception as e:
        print(f"⚠️ Error migrating messages: {e}")

    con.close()
    print("🎉 Migration Complete!")

if __name__ == "__main__":
    migrate()

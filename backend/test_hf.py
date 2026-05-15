# test_hf.py  — place in the backend folder and run: python test_hf.py

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

load_dotenv()

hf_token = os.getenv("HF_TOKEN")
print(f"1. HF_TOKEN found: {bool(hf_token)}")
print(f"   Token preview: {hf_token[:10]}..." if hf_token else "   ❌ Token is None")

# ── Step 2: Can we even import the LLM class? ──
print("\n2. Importing ChatOpenAI...")
print("   ✅ Import OK")

# ── Step 3: Can we instantiate the model? ──
print("\n3. Instantiating Qwen via HF router...")
llm = ChatOpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=hf_token,
    model="Qwen/Qwen2.5-7B-Instruct:together",
    temperature=0,
    max_tokens=100,
)
print("   ✅ Instantiation OK (no network call yet)")

# ── Step 4: Can we actually call it? ──
print("\n4. Sending test message to Qwen... (this makes the actual API call)")
try:
    response = llm.invoke("Say hello in one word.")
    print(f"   ✅ Response received: {response.content}")
except Exception as e:
    print(f"   ❌ API call failed: {type(e).__name__}: {e}")

print("\nDone.")
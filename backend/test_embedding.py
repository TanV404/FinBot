# test_embeddings.py
import os
os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

from langchain_huggingface import HuggingFaceEmbeddings
print("Loading HuggingFace embeddings model...")
emb = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
)
print("✅ Embeddings loaded. Testing encode...")
result = emb.embed_query("test query")
print(f"✅ Embedding shape: {len(result)} dims")
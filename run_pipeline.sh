#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "🚀 Starting NIFTY FinBot Data Pipeline..."

echo "--------------------------------------------------------"
echo "📥 STEP 1: Fetching Data (Wikipedia & YFinance)"
echo "--------------------------------------------------------"
uv run python fetch_data.py

echo "--------------------------------------------------------"
echo "🧠 STEP 2: Ingesting Data (Building Graph & Vector Store)"
echo "--------------------------------------------------------"
uv run python backend/ingest.py

echo "--------------------------------------------------------"
echo "🌐 STEP 3: Detecting Communities & Generating Summaries"
echo "--------------------------------------------------------"
uv run python backend/communities.py

echo "--------------------------------------------------------"
echo "📊 STEP 4: Visualizing Knowledge Graph"
echo "--------------------------------------------------------"
uv run python backend/visualize_graph.py

echo "--------------------------------------------------------"
echo "✅ Pipeline Complete! The data is now ready for FinBot."
echo "--------------------------------------------------------"

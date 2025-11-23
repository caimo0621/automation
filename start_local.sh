#!/bin/bash

# Start the local web app
echo "🚀 Starting Research Paper Digest Assistant..."
echo "📝 The app will open in your browser automatically"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit is not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the app
streamlit run paper_digest_assistant.py --server.headless true


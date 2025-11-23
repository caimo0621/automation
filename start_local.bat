@echo off
echo 🚀 Starting Research Paper Digest Assistant...
echo 📝 The app will open in your browser automatically
echo.

REM Check if streamlit is installed
where streamlit >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Streamlit is not installed. Installing dependencies...
    pip install -r requirements.txt
)

REM Run the app
streamlit run paper_digest_assistant.py --server.headless true

pause


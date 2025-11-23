# Research Paper Digest Assistant

A local web application for automatically summarizing research papers and creating structured reading notes.

## Quick Start

### Option 1: Using the startup script (Recommended)

**On macOS/Linux:**
```bash
chmod +x start_local.sh
./start_local.sh
```

**On Windows:**
```bash
start_local.bat
```

### Option 2: Manual start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install streamlit requests beautifulsoup4 pypdf openai
```

2. Run the app:
```bash
streamlit run paper_digest_assistant.py
```

3. The app will automatically open in your browser at `http://localhost:8501`

## Features

- 🔑 Enter your OpenAI API key directly in the web interface
- 📄 Two input modes: URL or Raw Text
- 🤖 Automatic summarization using OpenAI GPT-4o-mini
- 📄 Generates formatted Word documents (.docx) with all summaries
- 📝 Structured reading notes with key information extraction
- 📥 Download button for easy access to generated documents

## How to Use

1. Open the app in your browser (it will open automatically)
2. Enter your OpenAI API key at the top
3. Choose input mode:
   - **URL**: Paste a paper URL (supports PDF and HTML)
   - **Raw Text**: Paste paper text directly
4. Click "Generate Digest"
5. View the formatted reading note
6. Download the generated Word document (.docx) using the download button

## Output

The app generates a Word document (.docx) for each paper summary, saved locally with a timestamped filename (e.g., `paper_digest_Title_20251123_185220.docx`). Each document contains:

- Document information (date, source type, URL)
- Title
- Field or Topic
- Research Question
- Methodology
- Key Findings (bulleted list)
- Limitations
- Personal Takeaway

## Requirements

- Python 3.7+
- OpenAI API key
- Internet connection (for fetching papers and API calls)

## Dependencies

All dependencies are listed in `requirements.txt`:
- streamlit
- requests
- beautifulsoup4
- pypdf
- openai
- python-docx

## Notes

- This is a **local application** - all data stays on your computer
- The app runs entirely in your browser (localhost)
- No data is sent to external servers except OpenAI API calls


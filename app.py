import streamlit as st
import os
import json
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from openai import OpenAI
from supabase import create_client, Client
from typing import Optional


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client using environment variables.
    Expected environment variables:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.")
    
    return create_client(supabase_url, supabase_key)


def fetch_content_from_url(url: str) -> str:
    """
    Fetch the content of the paper from the given URL.
    If it is a PDF, download it and extract text from the first 3-5 pages.
    If it is HTML, fetch and parse the main text with BeautifulSoup.
    
    Returns the extracted text as a string.
    """
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Check if it's a PDF
        if url.endswith('.pdf') or 'application/pdf' in content_type:
            # Download PDF and extract text
            pdf_file = BytesIO(response.content)
            reader = PdfReader(pdf_file)
            
            # Extract text from first 5 pages (or all pages if less than 5)
            text_parts = []
            max_pages = min(5, len(reader.pages))
            
            for i in range(max_pages):
                page = reader.pages[i]
                text_parts.append(page.extract_text())
            
            full_text = "\n\n".join(text_parts)
            
        else:
            # Treat as HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text from paragraph tags
            paragraphs = soup.find_all('p')
            text_parts = [p.get_text() for p in paragraphs if p.get_text().strip()]
            
            # If no paragraphs found, try to get all text
            if not text_parts:
                text_parts = [soup.get_text()]
            
            full_text = "\n\n".join(text_parts)
        
        # Clean the text
        full_text = " ".join(full_text.split())  # Remove extra whitespace
        full_text = full_text.strip()
        
        # Truncate to safe length (10,000 characters) to avoid very large prompts
        if len(full_text) > 10000:
            full_text = full_text[:10000] + "... [truncated]"
        
        if not full_text or len(full_text.strip()) < 100:
            raise ValueError("Could not extract sufficient text from the URL. The content may be too short or inaccessible.")
        
        return full_text
        
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch content from URL: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing content: {str(e)}")


def summarize_paper_with_openai(text: str, api_key: str) -> dict:
    """
    Use the OpenAI API to summarize the paper into a structured JSON dict.
    
    Returns a dictionary with keys: title, abstract_summary, key_points, methodology
    """
    try:
        client = OpenAI(api_key=api_key)
        
        system_message = "You are an assistant that summarizes academic papers into structured JSON. Always respond with ONLY a valid JSON object, no additional text."
        
        user_message = f"""Please summarize the following research paper text and return ONLY a JSON object with the following structure:
{{
    "title": "The title of the paper",
    "abstract_summary": "A 2-4 sentence summary of the abstract",
    "key_points": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
    "methodology": "A 1-2 sentence description of the methodology used"
}}

Paper text:
{text}

Return ONLY the JSON object, no markdown formatting, no code blocks, just the raw JSON."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        try:
            summary = json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON from OpenAI response: {str(e)}. Response was: {content[:200]}")
        
        # Validate required keys
        required_keys = ["title", "abstract_summary", "key_points", "methodology"]
        for key in required_keys:
            if key not in summary:
                raise Exception(f"Missing required key '{key}' in OpenAI response")
        
        # Ensure key_points is a list
        if not isinstance(summary["key_points"], list):
            if isinstance(summary["key_points"], str):
                summary["key_points"] = [summary["key_points"]]
            else:
                summary["key_points"] = []
        
        return summary
        
    except Exception as e:
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            raise Exception(f"OpenAI API authentication failed: {str(e)}")
        raise Exception(f"Error summarizing paper with OpenAI: {str(e)}")


def insert_paper_record(supabase: Client, data: dict):
    """
    Insert one paper record into the 'papers' table.
    
    Expected data dict keys:
    - title (text)
    - url (text)
    - abstract_summary (text)
    - key_points (text - will be joined if list)
    - methodology (text)
    """
    try:
        # Convert key_points list to string if needed
        if isinstance(data.get("key_points"), list):
            data["key_points"] = "\n- ".join([""] + data["key_points"])
        
        result = supabase.table("papers").insert(data).execute()
        
        if not result.data:
            raise Exception("Failed to insert paper record: No data returned from Supabase")
        
        return result.data[0]
        
    except Exception as e:
        raise Exception(f"Error inserting paper record into Supabase: {str(e)}")


def load_papers(supabase: Client) -> list[dict]:
    """
    Load all paper records from the 'papers' table, ordered by created_at desc.
    
    Returns a list of dictionaries containing paper records.
    """
    try:
        result = supabase.table("papers").select("*").order("created_at", desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        raise Exception(f"Error loading papers from Supabase: {str(e)}")


def main():
    st.title("📚 Paper Reader Assistant")
    st.write("Paste a research paper URL, automatically summarize it, and store it for later review.")
    
    # OpenAI API Key input at the top
    st.subheader("🔑 OpenAI API Key")
    openai_api_key = st.text_input("Enter your OpenAI API Key", type="password", key="openai_key_input")
    if openai_api_key:
        st.session_state["openai_api_key"] = openai_api_key
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        st.error("⚠️ Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.")
        st.stop()
    
    try:
        supabase = get_supabase_client()
    except Exception as e:
        st.error(f"⚠️ Failed to initialize Supabase client: {str(e)}")
        st.stop()
    
    st.divider()
    
    # Paper URL input
    st.subheader("📄 Paper URL")
    paper_url = st.text_input("Enter the URL of the paper", key="paper_url_input")
    
    if st.button("Summarize & Save", type="primary"):
        # Validate OpenAI key
        api_key = st.session_state.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("❌ No OpenAI API key provided. Please enter it at the top of the page.")
        elif not paper_url:
            st.error("❌ Please enter a paper URL.")
        else:
            try:
                with st.status("🔄 Fetching and summarizing paper...", expanded=True) as status:
                    st.write("📥 Fetching content from URL...")
                    text = fetch_content_from_url(paper_url)
                    st.write(f"✅ Fetched {len(text)} characters of text")
                    
                    st.write("🤖 Summarizing with OpenAI...")
                    summary = summarize_paper_with_openai(text, api_key=api_key)
                    st.write("✅ Summary generated")
                    
                    st.write("💾 Saving to database...")
                    insert_paper_record(supabase, {
                        "title": summary["title"],
                        "url": paper_url,
                        "abstract_summary": summary["abstract_summary"],
                        "key_points": summary["key_points"] if isinstance(summary["key_points"], str) else "\n- ".join([""] + summary["key_points"]),
                        "methodology": summary["methodology"],
                    })
                    st.write("✅ Saved to database")
                
                st.success("✅ Paper summarized and saved successfully!")
                st.rerun()  # Refresh to show updated table
                
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
    
    st.divider()
    
    # Display saved papers
    st.subheader("📚 Saved Papers")
    
    try:
        papers = load_papers(supabase)
        
        if papers:
            # Helper function to truncate text for display
            def truncate(text, length=200):
                if not text:
                    return ""
                text_str = str(text)
                return text_str if len(text_str) <= length else text_str[:length] + "..."
            
            # Build display data
            display_data = []
            for p in papers:
                display_data.append({
                    "Title": p.get("title", "N/A"),
                    "URL": p.get("url", "N/A"),
                    "Abstract Summary": truncate(p.get("abstract_summary", ""), 150),
                    "Created At": p.get("created_at", "N/A")[:19] if p.get("created_at") else "N/A",  # Format timestamp
                })
            
            st.dataframe(display_data, use_container_width=True, hide_index=True)
            
            # Show count
            st.caption(f"Total papers saved: {len(papers)}")
            
        else:
            st.info("ℹ️ No papers saved yet. Try adding one above.")
            
    except Exception as e:
        st.error(f"❌ Error loading papers: {str(e)}")


if __name__ == "__main__":
    main()

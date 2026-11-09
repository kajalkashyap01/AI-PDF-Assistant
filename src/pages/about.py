import streamlit as st

def render_about_page():
    st.subheader("ℹ️ Help & About AI Assistant for PDF Documents")
    st.markdown("""
    ### How to Use:
    1. **Upload a PDF:** Use the file uploader in the sidebar to select your document.
    2. **View PDF:** Inspect document pages interactively in the centre viewer.
    3. **Ask Questions:** Type queries in the right chat panel. The system retrieves exact chunks using Pinecone and generates grounded responses via Cohere.
    
    ### Technology Stack:
    - **Frontend:** Streamlit with modular SaaS components.
    - **Embeddings & LLM:** Cohere API (`embed-english-v3.0`, `command-r`, `rerank-english-v2.0`).
    - **Vector Database:** Pinecone serverless vector store.
    """)
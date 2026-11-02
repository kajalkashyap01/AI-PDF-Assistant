import streamlit as st

def render_chat_panel(vectorstore, cohere_key):
    st.markdown("### 🤖 AI Assistant")
    chat_container = st.container(height=520)
    
    with chat_container:
        if st.session_state["messages"]:
            for msg in st.session_state["messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and "sources" in msg:
                        with st.expander("📚 View Retrieved Source Context"):
                            for idx, doc in enumerate(msg["sources"]):
                                st.caption(f"**Chunk {idx+1}:** {doc.get('text', str(doc))}")
        else:
            st.info("Upload a PDF and ask a question to start chatting.")

    return chat_container
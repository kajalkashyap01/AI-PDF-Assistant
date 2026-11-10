import streamlit as st

SPARKLE_ICON = """
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3z"/>
  <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z"/>
  <path d="M5 16l.6 1.4L7 18l-1.4.6L5 20l-.6-1.4L3 18l1.4-.6L5 16z"/>
</svg>
"""

CHAT_ICON = """
<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>
  <circle cx="9" cy="12" r=".6" fill="currentColor"/>
  <circle cx="12" cy="12" r=".6" fill="currentColor"/>
  <circle cx="15" cy="12" r=".6" fill="currentColor"/>
</svg>
"""


def render_chat_panel(vectorstore, cohere_key):
    st.markdown(
        f'<div class="panel-heading">'
        f'<span class="panel-heading-icon">{SPARKLE_ICON}</span>AI Assistant'
        f'</div>',
        unsafe_allow_html=True,
    )

    chat_container = st.container(height=520, border=False)

    with chat_container:
        if st.session_state["messages"]:
            for msg in st.session_state["messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and "sources" in msg:
                        with st.expander("View Retrieved Source Context"):
                            for idx, doc in enumerate(msg["sources"]):
                                st.caption(f"**Chunk {idx+1}:** {doc.get('text', str(doc))}")
        else:
            st.markdown(
                f'<div class="chat-hint">{CHAT_ICON}'
                f'<span>Upload a PDF and ask a question to begin.</span></div>',
                unsafe_allow_html=True,
            )

    return chat_container
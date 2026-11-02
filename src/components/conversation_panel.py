import streamlit as st

def render_conversation_controls():
    st.markdown("### 💬 Conversations")
    if st.button("＋ New Conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()
    st.divider()
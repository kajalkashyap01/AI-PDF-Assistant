import streamlit as st

def render_documents_page():
    st.subheader("📁 Document Management")
    st.write("Manage your uploaded PDF files and vector indices.")
    if st.session_state.get("pdf_name"):
        st.success(f"**Active Document:** {st.session_state['pdf_name']}")
        if st.button("Remove Active Document"):
            st.session_state["pdf_bytes"] = None
            st.session_state["pdf_name"] = None
            st.session_state["vectorstore"] = None
            st.session_state["messages"] = []
            st.rerun()
    else:
        st.info("No documents currently loaded.")
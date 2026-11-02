import streamlit as st


def render_navigation(active_page: str = "Workspace") -> str:
    pages = [
        ("Workspace", "▣"),
        ("Documents", "▤"),
        ("Settings", "⚙"),
        ("Help & About", "?"),
    ]

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = active_page

    with st.sidebar:
        st.markdown(
            """
            <div class="ai-sidebar-brand">
                <div class="ai-brand-icon">AI</div>
                <div class="ai-brand-name">AI Assistant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # New Chat button
        if st.button(
            "＋  New Chat",
            key="new_chat_button",
            use_container_width=True,
            type="primary",
        ):
            st.session_state["messages"] = []
            st.session_state["vectorstore"] = None
            st.session_state["pdf_name"] = None
            st.session_state["pdf_bytes"] = None
            st.session_state["pdf_fingerprint"] = None
            st.session_state["pdf_page_number"] = 0
            st.session_state["active_document_id"] = None
            st.session_state["pdf_uploader_version"] += 1
            st.session_state["current_page"] = "Workspace"
            st.rerun()

        st.markdown(
            """
            <div class="ai-sidebar-divider"></div>
            <div class="ai-sidebar-label">WORKSPACE</div>
            """,
            unsafe_allow_html=True,
        )

        for page_name, page_icon in pages:
            is_active = st.session_state["current_page"] == page_name

            button_type = "primary" if is_active else "secondary"

            if st.button(
                f"{page_icon}   {page_name}",
                key=f"ai_navigation_{page_name}",
                use_container_width=True,
                type=button_type,
            ):
                st.session_state["current_page"] = page_name
                st.rerun()

        st.markdown(
            """
            <div class="ai-sidebar-divider ai-sidebar-bottom-divider"></div>

            <div class="ai-sidebar-status">
                <span class="ai-status-dot"></span>
                <span>Assistant ready</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["current_page"]
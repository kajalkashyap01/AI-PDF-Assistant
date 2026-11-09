import streamlit as st


def render_navigation(active_page: str = "Workspace") -> str:
    pages = [
        ("Workspace", "dashboard"),
        ("Documents", "description"),
        ("Settings", "settings"),
        ("Help & About", "help_outline"),
    ]

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = active_page

    with st.sidebar:
        st.markdown(
            """
            <div class="ai-sidebar-brand">
                <div class="ai-brand-icon">PDF</div>
                <div class="ai-brand-name">AI Assistant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "New Chat",
            icon=":material/add:",
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
            st.session_state["pdf_uploader_version"] = (
                st.session_state.get("pdf_uploader_version", 0) + 1
            )
            st.session_state["current_page"] = "Workspace"
            st.rerun()

        st.markdown(
            """
            <div class="ai-sidebar-divider"></div>
            <div class="ai-sidebar-label">MENU</div>
            """,
            unsafe_allow_html=True,
        )

        for page_name, icon_name in pages:
            is_active = st.session_state["current_page"] == page_name
            if st.button(
                page_name,
                icon=f":material/{icon_name}:",
                key=f"ai_navigation_{page_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
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
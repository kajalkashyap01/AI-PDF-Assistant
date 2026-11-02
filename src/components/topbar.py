from __future__ import annotations

import streamlit as st


def render_topbar(document_name: str | None = None) -> None:
    """
    Render the topbar using native Streamlit components.
    This avoids HTML being displayed as code.
    """

    left_column, right_column = st.columns(
        [0.68, 0.32],
        vertical_alignment="center",
    )

    with left_column:
        logo_column, title_column = st.columns(
            [0.08, 0.92],
            vertical_alignment="center",
        )

        with logo_column:
            st.markdown(
                '<div class="native-ai-logo">AI</div>',
                unsafe_allow_html=True,
            )

        with title_column:
            st.markdown(
                '<div class="native-ai-title">AI Assistant</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="native-ai-subtitle">'
                "Ask questions about your document"
                "</div>",
                unsafe_allow_html=True,
            )

    with right_column:
        if document_name:
            document_label = f"▤  {document_name}  ●"
        else:
            document_label = "▤  No document uploaded"

        st.markdown(
            f'<div class="native-document-status">{document_label}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="native-topbar-divider"></div>',
        unsafe_allow_html=True,
    )

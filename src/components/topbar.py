
import html
import streamlit as st


def render_topbar(document_name: str | None = None) -> None:

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.3rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left_column, right_column = st.columns(
        [0.68, 0.32],
        vertical_alignment="center",
    )

    with left_column:
        st.markdown(
            """
            <div class="topbar-brand">
                <div class="topbar-logo">PDF</div>
                <div>
                    <div class="topbar-title">PDF Assistant</div>
                    <div class="topbar-subtitle">
                        Your intelligent document workspace
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_column:
        if document_name:
            safe_name = html.escape(str(document_name))
            status_text = f'<span class="status-dot"></span>{safe_name}'
        else:
            status_text = (
                '<span class="status-dot"></span>No document uploaded'
            )

        st.markdown(
            f'<div class="native-document-status">{status_text}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="native-topbar-divider"></div>',
        unsafe_allow_html=True,
    )

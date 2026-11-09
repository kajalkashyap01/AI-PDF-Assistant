from __future__ import annotations

import streamlit as st


def render_settings_page() -> None:
    """
    Render the AI Assistant settings page.
    Settings are stored for the current Streamlit session.
    """

    # --------------------------------------------------
    # SESSION DEFAULTS
    # --------------------------------------------------

    defaults = {
        "settings_show_sources": True,
        "settings_pdf_view": "Fit Width",
        "settings_confirm_delete": True,
        "settings_answer_style": "Detailed",
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    # --------------------------------------------------
    # PAGE-SPECIFIC STYLING
    # --------------------------------------------------

    st.markdown(
        """
        <style>
        .ai-settings-header {
            margin-bottom: 28px;
        }

        .ai-settings-eyebrow {
            margin-bottom: 7px;
            color: #8b8b8b;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.8px;
            text-transform: uppercase;
        }

        .ai-settings-heading {
            margin: 0;
            color: #111111;
            font-size: 30px;
            font-weight: 800;
            letter-spacing: -0.8px;
        }

        .ai-settings-subtitle {
            margin-top: 8px;
            color: #777777;
            font-size: 13px;
        }

        .ai-settings-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            margin-bottom: 14px;
            border-radius: 12px;
            background: #fff6c9;
            color: #111111;
            font-size: 18px;
            font-weight: 700;
        }

        .ai-settings-card-title {
            margin-bottom: 5px;
            color: #111111;
            font-size: 17px;
            font-weight: 750;
        }

        .ai-settings-card-description {
            min-height: 36px;
            margin-bottom: 18px;
            color: #888888;
            font-size: 12px;
            line-height: 1.5;
        }

        .ai-settings-note {
            margin-top: 14px;
            padding: 10px 12px;
            border-left: 3px solid #f5c518;
            border-radius: 5px;
            background: #fffbea;
            color: #666666;
            font-size: 11px;
            line-height: 1.5;
        }

        .ai-settings-model-box {
            margin-top: 8px;
            padding: 12px;
            border: 1px solid #e5e5e2;
            border-radius: 9px;
            background: #fafaf8;
        }

        .ai-settings-model-label {
            margin-bottom: 3px;
            color: #999999;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }

        .ai-settings-model-value {
            color: #222222;
            font-size: 12px;
            font-weight: 650;
        }

        .ai-settings-save-title {
            color: #111111;
            font-size: 15px;
            font-weight: 750;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e5e5e2 !important;
            border-radius: 14px !important;
            background: #ffffff;
        }

        div.stButton > button[kind="primary"] {
            min-height: 42px;
            border: none;
            border-radius: 9px;
            background: #111111;
            color: #ffffff;
            font-weight: 700;
        }

        div.stButton > button[kind="primary"]:hover {
            border: none;
            background: #2b2b2b;
            color: #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # PAGE HEADER
    # --------------------------------------------------

    st.markdown(
        """
        <div class="ai-settings-header">
            <div class="ai-settings-eyebrow">PREFERENCES</div>
            <h1 class="ai-settings-heading">Settings</h1>
            <div class="ai-settings-subtitle">
                Personalize your AI Assistant workspace and document experience.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # SETTINGS CARDS
    # --------------------------------------------------

    left_column, right_column = st.columns(
        2,
        gap="large",
    )

    # --------------------------------------------------
    # CHAT EXPERIENCE
    # --------------------------------------------------

    with left_column:
        with st.container(border=True):
            st.markdown(
                """
                <div class="ai-settings-icon">✦</div>
                <div class="ai-settings-card-title">
                    Chat experience
                </div>
                <div class="ai-settings-card-description">
                    Control how AI Assistant presents answers from your PDF.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.toggle(
                "Show source references",
                key="settings_show_sources",
                help=(
                    "Show the retrieved PDF text and page numbers "
                    "with assistant answers."
                ),
            )

            st.selectbox(
                "Answer style",
                options=[
                    "Concise",
                    "Detailed",
                    "Step-by-step",
                ],
                key="settings_answer_style",
                help=(
                    "Choose how much explanation the assistant "
                    "should provide."
                ),
            )

            st.markdown(
                """
                <div class="ai-settings-note">
                    Source references help you verify answers directly
                    against the uploaded document.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------
    # DOCUMENT EXPERIENCE
    # --------------------------------------------------

    with right_column:
        with st.container(border=True):
            st.markdown(
                """
                <div class="ai-settings-icon">▤</div>
                <div class="ai-settings-card-title">
                    Document experience
                </div>
                <div class="ai-settings-card-description">
                    Customize PDF viewing and document management behavior.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.radio(
                "PDF display mode",
                options=[
                    "Fit Width",
                    "Original Size",
                ],
                key="settings_pdf_view",
            )

            st.checkbox(
                "Confirm before deleting",
                key="settings_confirm_delete",
                help=(
                    "Ask for confirmation before removing the active PDF."
                ),
            )

    # --------------------------------------------------
    # ACTIVE AI MODELS
    # --------------------------------------------------

    st.markdown("<div style='height: 22px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            """
            <div class="ai-settings-card-title">
                Active AI models
            </div>
            <div class="ai-settings-card-description">
                These models power document search, reranking, and answers.
            </div>
            """,
            unsafe_allow_html=True,
        )

        model_column_1, model_column_2, model_column_3 = st.columns(3)

        with model_column_1:
            st.markdown(
                """
                <div class="ai-settings-model-box">
                    <div class="ai-settings-model-label">Chat</div>
                    <div class="ai-settings-model-value">
                        command-a-03-2025
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with model_column_2:
            st.markdown(
                """
                <div class="ai-settings-model-box">
                    <div class="ai-settings-model-label">Embeddings</div>
                    <div class="ai-settings-model-value">
                        embed-english-v3.0
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with model_column_3:
            st.markdown(
                """
                <div class="ai-settings-model-box">
                    <div class="ai-settings-model-label">Reranking</div>
                    <div class="ai-settings-model-value">
                        rerank-english-v3.0
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------
    # SAVE SETTINGS
    # --------------------------------------------------

    st.markdown("<div style='height: 22px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        save_column, button_column = st.columns(
            [3, 1],
            vertical_alignment="center",
        )

        with save_column:
            st.markdown(
                '<div class="ai-settings-save-title">'
                "Workspace preferences"
                "</div>",
                unsafe_allow_html=True,
            )

            st.caption(
                "Save your changes for the current session."
            )

        with button_column:
            if st.button(
                "Save changes",
                type="primary",
                use_container_width=True,
            ):
                st.success(
                    "Your preferences have been saved."
                )

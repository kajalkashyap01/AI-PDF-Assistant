
from __future__ import annotations

import streamlit as st


def render_settings_page() -> None:

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
    # CUSTOM STYLING
    # --------------------------------------------------

    st.markdown(
        """
        <style>

        /* PAGE HEADER */

        .settings-header {
            margin-bottom: 30px;
        }

        .settings-eyebrow {
            color: #43866b;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }

        .settings-title {
            color: #183d30;
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -1px;
            margin: 0;
        }

        .settings-subtitle {
            color: #77857e;
            font-size: 14px;
            margin-top: 8px;
        }

        /* SECTION LABEL */

        .settings-section-label {
            color: #718078;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.5px;
            margin-bottom: 13px;
        }

        /* CARD CONTENT */

        .settings-card-heading {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .settings-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: #e8f3ed;
            color: #286448;
            font-size: 21px;
        }

        .settings-card-title {
            color: #1e4033;
            font-size: 17px;
            font-weight: 750;
        }

        .settings-card-description {
            color: #849087;
            font-size: 12px;
            line-height: 1.6;
            margin-bottom: 22px;
        }

        /* MODEL CARDS */

        .model-box {
            padding: 17px;
            min-height: 91px;
            border: 1px solid #e5eee8;
            border-radius: 11px;
            background: #f8fbf9;
        }

        .model-label {
            color: #829087;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.2px;
            margin-bottom: 9px;
            text-transform: uppercase;
        }

        .model-name {
            color: #244d3b;
            font-size: 13px;
            font-weight: 750;
            overflow-wrap: anywhere;
        }

        /* SAVE AREA */

        .save-heading {
            color: #214735;
            font-size: 16px;
            font-weight: 750;
        }

        .save-description {
            color: #829087;
            font-size: 12px;
            margin-top: 5px;
        }

        /* STREAMLIT CARDS */

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #e5ece7 !important;
            border-radius: 15px !important;
            background: #ffffff !important;
        }

        /* INPUT LABELS */

        div[data-testid="stWidgetLabel"] p {
            color: #344b3e !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }

        /* SAVE BUTTON */

        div.stButton > button[kind="primary"] {
            min-height: 43px;
            border: none;
            border-radius: 9px;
            background: #286448;
            color: white;
            font-size: 13px;
            font-weight: 700;
        }

        div.stButton > button[kind="primary"]:hover {
            background: #1c4d36;
            color: white;
            border: none;
        }

        /* RADIO OPTIONS */

        div[data-testid="stRadio"] label {
            color: #344b3e;
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
        <div class="settings-header">
            <div class="settings-eyebrow">WORKSPACE PREFERENCES</div>
            <h1 class="settings-title">Settings</h1>
            <div class="settings-subtitle">
                Manage your chat preferences and document experience.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # PREFERENCES SECTION
    # --------------------------------------------------

    st.markdown(
        '<div class="settings-section-label">GENERAL PREFERENCES</div>',
        unsafe_allow_html=True,
    )

    left_column, right_column = st.columns(2, gap="large")

    # CHAT SETTINGS

    with left_column:
        with st.container(border=True):

            st.markdown(
                """
                <div class="settings-card-heading">
                    <div class="settings-icon">✦</div>
                    <div class="settings-card-title">
                        Chat experience
                    </div>
                </div>
                <div class="settings-card-description">
                    Personalize how the AI assistant responds to your questions.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.toggle(
                "Show source references",
                key="settings_show_sources",
                help="Display PDF source references with answers.",
            )

            st.selectbox(
                "Answer style",
                options=["Concise", "Detailed", "Step-by-step"],
                key="settings_answer_style",
                help="Choose your preferred answer format.",
            )

            st.markdown(
                """
                <div style="
                    margin-top: 17px;
                    padding: 12px;
                    background: #f0f7f2;
                    border-radius: 9px;
                    color: #52715e;
                    font-size: 12px;
                    line-height: 1.6;">
                    Source references make it easier to verify answers
                    against your uploaded PDF.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # DOCUMENT SETTINGS

    with right_column:
        with st.container(border=True):

            st.markdown(
                """
                <div class="settings-card-heading">
                    <div class="settings-icon">▤</div>
                    <div class="settings-card-title">
                        Document experience
                    </div>
                </div>
                <div class="settings-card-description">
                    Customize how documents are displayed and managed.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.radio(
                "PDF display mode",
                options=["Fit Width", "Original Size"],
                key="settings_pdf_view",
            )

            st.markdown("<div style='height: 10px'></div>",
                        unsafe_allow_html=True)

            st.checkbox(
                "Confirm before deleting",
                key="settings_confirm_delete",
                help="Ask for confirmation before removing a PDF.",
            )

            st.markdown(
                """
                <div style="
                    margin-top: 17px;
                    padding: 12px;
                    background: #f0f7f2;
                    border-radius: 9px;
                    color: #52715e;
                    font-size: 12px;
                    line-height: 1.6;">
                    Choose how your PDF is displayed in the workspace.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------
    # AI MODELS
    # --------------------------------------------------

    st.markdown("<div style='height: 28px'></div>",
                unsafe_allow_html=True)

    st.markdown(
        '<div class="settings-section-label">SYSTEM INFORMATION</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):

        st.markdown(
            """
            <div class="settings-card-heading">
                <div class="settings-icon">✧</div>
                <div class="settings-card-title">
                    Active AI models
                </div>
            </div>
            <div class="settings-card-description">
                Models currently configured for your document assistant.
            </div>
            """,
            unsafe_allow_html=True,
        )

        model_col1, model_col2, model_col3 = st.columns(3, gap="medium")

        models = [
            ("CHAT MODEL", "command-a-03-2025"),
            ("EMBEDDING MODEL", "embed-english-v3.0"),
            ("RERANKING MODEL", "rerank-english-v3.0"),
        ]

        for column, model in zip(
            [model_col1, model_col2, model_col3],
            models,
        ):
            with column:
                st.markdown(
                    f"""
                    <div class="model-box">
                        <div class="model-label">{model[0]}</div>
                        <div class="model-name">{model[1]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # --------------------------------------------------
    # SAVE PREFERENCES
    # --------------------------------------------------

    st.markdown("<div style='height: 25px'></div>",
                unsafe_allow_html=True)

    with st.container(border=True):

        save_col, button_col = st.columns(
            [3, 1],
            vertical_alignment="center",
        )

        with save_col:
            st.markdown(
                """
                <div class="save-heading">Workspace preferences</div>
                <div class="save-description">
                    Your selected preferences are maintained in this session.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with button_col:
            if st.button(
                "Save changes",
                type="primary",
                use_container_width=True,
            ):
                st.success("Your preferences have been saved.")

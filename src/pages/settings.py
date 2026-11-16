
import html

import streamlit as st


# ============================================================
# SETTINGS PAGE — PROFESSIONAL GREEN DESIGN
# ============================================================

def _inject_settings_css():
    st.markdown(
        """
<style>
/* ==============================================
   SETTINGS PAGE
============================================== */

.settings-page {
    color: #183f32;
}

.settings-heading {
    font-size: 29px !important;
    font-weight: 750 !important;
    color: #173e31 !important;
    letter-spacing: -0.8px;
    margin: 0;
    line-height: 1.2;
}

.settings-subheading {
    font-size: 12px !important;
    color: #7c8f83 !important;
    margin: 9px 0 25px;
}

.settings-section-heading {
    font-size: 10px !important;
    font-weight: 750 !important;
    letter-spacing: 1.7px;
    text-transform: uppercase;
    color: #82958a !important;
    margin: 14px 0 15px;
}

/* Card heading */

.settings-card-title {
    font-size: 15px !important;
    font-weight: 750 !important;
    color: #183e30 !important;
}

.settings-card-description {
    font-size: 11px !important;
    color: #829487 !important;
    margin: 5px 0 15px;
    line-height: 1.5;
}

/* Section icon */

.settings-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: #e6f1e9;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    color: #236448;
    margin-right: 10px;
}

/* Setting row */

.settings-label {
    font-size: 12px !important;
    font-weight: 650 !important;
    color: #214638 !important;
    margin-bottom: 4px;
}

.settings-description {
    font-size: 10px !important;
    color: #85978b !important;
    line-height: 1.5;
}

/* Model cards */

.settings-model-card {
    border: 1px solid #dce9df;
    border-radius: 11px;
    padding: 17px;
    background: #ffffff;
    min-height: 105px;
}

.settings-model-label {
    font-size: 9px !important;
    font-weight: 750 !important;
    color: #82968a !important;
    letter-spacing: 1.3px;
    text-transform: uppercase;
    margin-bottom: 13px;
}

.settings-model-name {
    font-size: 12px !important;
    font-weight: 750 !important;
    color: #194432 !important;
    overflow-wrap: anywhere;
}

.settings-model-description {
    font-size: 10px !important;
    color: #84968a !important;
    margin-top: 8px;
}

/* Info bar */

.settings-info {
    border: 1px solid #dcece1;
    border-radius: 9px;
    background: #f0f7f2;
    padding: 12px 15px;
    font-size: 11px !important;
    color: #547763 !important;
    line-height: 1.6;
}

/* Footer */

.settings-footer {
    font-size: 11px !important;
    color: #87998d !important;
    line-height: 1.6;
}

/* Scope the styling to the settings page */

.st-key-settings_main_card,
.st-key-settings_document_card {
    background: #ffffff;
    border: 1px solid #dce8df !important;
    border-radius: 14px !important;
    padding: 21px !important;
    box-shadow: 0 3px 14px rgba(20, 65, 43, 0.025);
}

.st-key-settings_main_card [data-testid="stSelectbox"] > div,
.st-key-settings_document_card [data-testid="stSelectbox"] > div {
    border-radius: 8px;
}

.st-key-settings_save_button button {
    background: #183f32 !important;
    color: #ffffff !important;
    border: 1px solid #183f32 !important;
    border-radius: 9px !important;
    min-height: 42px;
    font-weight: 650 !important;
}

.st-key-settings_save_button button:hover {
    background: #256047 !important;
    border-color: #256047 !important;
    color: #ffffff !important;
}

.st-key-settings_main_card [data-testid="stToggle"] label,
.st-key-settings_document_card [data-testid="stToggle"] label {
    font-size: 12px !important;
}

/* Compact controls */

.st-key-settings_main_card .stSelectbox,
.st-key-settings_document_card .stSelectbox {
    margin-bottom: 4px;
}

.st-key-settings_main_card [data-testid="stWidgetLabel"],
.st-key-settings_document_card [data-testid="stWidgetLabel"] {
    color: #214638;
    font-size: 12px;
}

@media (max-width: 768px) {
    .settings-heading {
        font-size: 24px !important;
    }

    .st-key-settings_main_card,
    .st-key-settings_document_card {
        padding: 15px !important;
    }

    .settings-model-card {
        min-height: 95px;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# HTML HELPERS
# ============================================================

def _safe(value):
    return html.escape(str(value), quote=True)


def _heading(title, description):
    markup = (
        '<div class="settings-card-title">'
        f'{_safe(title)}'
        '</div>'
        '<div class="settings-card-description">'
        f'{_safe(description)}'
        '</div>'
    )
    st.markdown(markup, unsafe_allow_html=True)


def _section_label(text):
    st.markdown(
        '<div class="settings-section-heading">'
        f'{_safe(text)}'
        '</div>',
        unsafe_allow_html=True,
    )


def _model_card(label, name, description):
    markup = (
        '<div class="settings-model-card">'
        '<div class="settings-model-label">'
        f'{_safe(label)}'
        '</div>'
        '<div class="settings-model-name">'
        f'{_safe(name)}'
        '</div>'
        '<div class="settings-model-description">'
        f'{_safe(description)}'
        '</div>'
        '</div>'
    )
    st.markdown(markup, unsafe_allow_html=True)


# ============================================================
# SESSION SETTINGS
# ============================================================

def _initialize_preferences():

    defaults = {
        "settings_show_sources": True,
        "settings_confirm_delete": True,
        "settings_pdf_view": "Fit Width",
        "settings_answer_style": "Detailed",
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

    if "settings_saved_preferences" not in st.session_state:
        st.session_state["settings_saved_preferences"] = {
            key: st.session_state[key]
            for key in defaults
        }


# ============================================================
# MAIN SETTINGS PAGE
# ============================================================

def render_settings_page():

    _initialize_preferences()
    _inject_settings_css()

    # --------------------------------------------------------
    # PAGE HEADER
    # --------------------------------------------------------

    st.markdown(
        '<div class="settings-heading">Settings</div>'
        '<div class="settings-subheading">'
        'Manage your AI assistant, document preferences '
        'and workspace experience.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # GENERAL PREFERENCES
    # --------------------------------------------------------

    _section_label("General Preferences")

    chat_column, document_column = st.columns(
        2,
        gap="medium",
    )

    # ========================================================
    # CHAT SETTINGS
    # ========================================================

    with chat_column:

        with st.container(
            border=True,
            key="settings_main_card",
        ):

            _heading(
                "AI & Chat Experience",
                "Control how your assistant responds "
                "and presents information.",
            )

            st.markdown(
                '<div class="settings-label">'
                'Answer style'
                '</div>',
                unsafe_allow_html=True,
            )

            answer_styles = [
                "Concise",
                "Balanced",
                "Detailed",
            ]

            current_style = st.session_state.get(
                "settings_answer_style",
                "Detailed",
            )

            if current_style not in answer_styles:
                current_style = "Detailed"

            answer_style = st.selectbox(
                "Answer style",
                options=answer_styles,
                index=answer_styles.index(current_style),
                label_visibility="collapsed",
                key="settings_answer_style_input",
            )

            st.caption(
                "Choose how much detail the AI includes "
                "in its answers."
            )

            st.divider()

            show_sources = st.toggle(
                "Show source references",
                value=st.session_state.get(
                    "settings_show_sources",
                    True,
                ),
                key="settings_show_sources_input",
                help=(
                    "Display relevant PDF and web sources "
                    "below AI responses."
                ),
            )

            st.caption(
                "See the document evidence used to "
                "support AI-generated answers."
            )

    # ========================================================
    # DOCUMENT SETTINGS
    # ========================================================

    with document_column:

        with st.container(
            border=True,
            key="settings_document_card",
        ):

            _heading(
                "Document Experience",
                "Customize document viewing "
                "and safety preferences.",
            )

            st.markdown(
                '<div class="settings-label">'
                'PDF display mode'
                '</div>',
                unsafe_allow_html=True,
            )

            display_options = [
                "Fit Width",
                "Original Size",
            ]

            current_display = st.session_state.get(
                "settings_pdf_view",
                "Fit Width",
            )

            if current_display not in display_options:
                current_display = "Fit Width"

            pdf_view = st.selectbox(
                "PDF display mode",
                options=display_options,
                index=display_options.index(current_display),
                label_visibility="collapsed",
                key="settings_pdf_view_input",
            )

            st.caption(
                "Choose how PDF pages should appear "
                "in the document viewer."
            )

            st.divider()

            confirm_delete = st.toggle(
                "Confirm before deleting",
                value=st.session_state.get(
                    "settings_confirm_delete",
                    True,
                ),
                key="settings_confirm_delete_input",
                help=(
                    "Ask for confirmation before removing "
                    "a saved PDF."
                ),
            )

            st.caption(
                "Reduce the risk of accidentally "
                "deleting documents."
            )

    # --------------------------------------------------------
    # INFORMATION BANNER
    # --------------------------------------------------------

    st.markdown(
        '<div class="settings-info">'
        'Your preferences are applied to the current '
        'workspace session. Save your changes below '
        'to activate the selected options.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # AI MODEL INFORMATION
    # --------------------------------------------------------

    st.markdown("<div style='height:15px'></div>",
                unsafe_allow_html=True)

    _section_label("AI System Information")

    _heading(
        "Active AI Models",
        "Models configured for your document assistant.",
    )

    model_col1, model_col2, model_col3 = st.columns(
        3,
        gap="medium",
    )

    with model_col1:
        _model_card(
            "Chat Model",
            "command-a-03-2025",
            "AI-generated answers and explanations",
        )

    with model_col2:
        _model_card(
            "Embedding Model",
            "embed-english-v3.0",
            "Semantic PDF content search",
        )

    with model_col3:
        _model_card(
            "Reranking Model",
            "rerank-english-v3.0",
            "Improves document search relevance",
        )

    # --------------------------------------------------------
    # SAVE SECTION
    # --------------------------------------------------------

    st.markdown("<div style='height:16px'></div>",
                unsafe_allow_html=True)

    st.divider()

    footer_col, button_col = st.columns(
        [3, 1],
        vertical_alignment="center",
    )

    with footer_col:

        st.markdown(
            '<div class="settings-label">'
            'Workspace Preferences'
            '</div>'
            '<div class="settings-footer">'
            'Review your selections and save your changes.'
            '</div>',
            unsafe_allow_html=True,
        )

    with button_col:

        with st.container(
            key="settings_save_button",
        ):

            save_clicked = st.button(
                "Save Changes",
                type="primary",
                use_container_width=True,
                key="settings_save_changes",
            )

    if save_clicked:

        st.session_state["settings_answer_style"] = (
            answer_style
        )

        st.session_state["settings_show_sources"] = (
            show_sources
        )

        st.session_state["settings_pdf_view"] = (
            pdf_view
        )

        st.session_state["settings_confirm_delete"] = (
            confirm_delete
        )

        st.session_state["settings_saved_preferences"] = {
            "settings_answer_style": answer_style,
            "settings_show_sources": show_sources,
            "settings_pdf_view": pdf_view,
            "settings_confirm_delete": confirm_delete,
        }

        st.success(
            "Your workspace preferences have been saved."
        )

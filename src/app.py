from __future__ import annotations

import hashlib
import html
import os
import tempfile
from pathlib import Path

import fitz
import streamlit as st
from dotenv import load_dotenv

from chatbot import Chatbot
from components.sidebar import render_navigation
from components.topbar import render_topbar
from vectorstore import VectorStore
from pages.settings import render_settings_page
from database import (
    initialize_database,
    save_document,
    get_document,
    get_document_by_fingerprint,
    list_documents,
    save_message,
    get_messages,
    delete_document,
)


# =========================================================
# PROJECT CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")

COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")

st.set_page_config(
    page_title="AI Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()


# =========================================================
# LOAD CSS
# =========================================================

CSS_FILE = BASE_DIR / "assets" / "styles.css"

if CSS_FILE.exists():
    css_content = CSS_FILE.read_text(encoding="utf-8")
    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True,
    )


# =========================================================
# SESSION STATE
# =========================================================

def initialize_session_state() -> None:

    default_values = {
        "current_page": "Workspace",
        "messages": [],
        "vectorstore": None,
        "pdf_name": None,
        "pdf_bytes": None,
        "pdf_fingerprint": None,
        "pdf_page_number": 0,
        "active_document_id": None,
        "pdf_uploader_version": 0,
    }

    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_document() -> None:
    """Clear the active document without affecting other saved documents."""

    st.session_state["messages"] = []
    st.session_state["vectorstore"] = None
    st.session_state["pdf_name"] = None
    st.session_state["pdf_bytes"] = None
    st.session_state["pdf_fingerprint"] = None
    st.session_state["pdf_page_number"] = 0
    st.session_state["active_document_id"] = None


initialize_session_state()


# =========================================================
# TEMPORARY PDF HELPER
# =========================================================

def create_temporary_pdf(pdf_bytes: bytes) -> str:

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
    ) as temporary_file:

        temporary_file.write(pdf_bytes)

    return temporary_file.name


# =========================================================
# OPEN SAVED DOCUMENT
# =========================================================

def open_saved_document(document_id: int) -> bool:

    if not COHERE_API_KEY:
        st.error("COHERE_API_KEY is missing from your .env file.")
        return False

    if not PINECONE_API_KEY:
        st.error("PINECONE_API_KEY is missing from your .env file.")
        return False

    document = get_document(document_id)

    if document is None:
        st.error("This saved document could not be found.")
        return False

    temporary_pdf_path = None

    try:

        pdf_bytes = bytes(document["pdf_data"])
        temporary_pdf_path = create_temporary_pdf(pdf_bytes)

        with st.spinner("Opening saved document..."):

            vectorstore = VectorStore(
                pdf_path=temporary_pdf_path,
                cohere_api_key=COHERE_API_KEY,
                pinecone_api_key=PINECONE_API_KEY,
                existing_namespace=document["namespace"],
            )

        messages = get_messages(document_id)

        st.session_state["active_document_id"] = document_id
        st.session_state["pdf_name"] = document["name"]
        st.session_state["pdf_bytes"] = pdf_bytes
        st.session_state["pdf_fingerprint"] = document["fingerprint"]
        st.session_state["vectorstore"] = vectorstore
        st.session_state["pdf_page_number"] = 0
        st.session_state["messages"] = messages

        return True

    except Exception as error:

        st.error(
            "The saved document could not be opened.\n\n"
            f"Error details: {error}"
        )

        return False

    finally:

        if temporary_pdf_path and os.path.exists(temporary_pdf_path):
            os.remove(temporary_pdf_path)


# =========================================================
# PROCESS NEW OR EXISTING UPLOAD
# =========================================================

def process_uploaded_pdf(uploaded_file) -> None:

    if not COHERE_API_KEY:
        st.error("COHERE_API_KEY is missing from your .env file.")
        return

    if not PINECONE_API_KEY:
        st.error("PINECONE_API_KEY is missing from your .env file.")
        return

    pdf_bytes = uploaded_file.getvalue()
    fingerprint = hashlib.sha256(pdf_bytes).hexdigest()

    if (
        st.session_state["pdf_fingerprint"] == fingerprint
        and st.session_state["active_document_id"] is not None
    ):
        return

    existing_document = get_document_by_fingerprint(fingerprint)

    if existing_document:
        open_saved_document(existing_document["id"])
        return

    temporary_pdf_path = None

    try:

        temporary_pdf_path = create_temporary_pdf(pdf_bytes)

        with st.spinner("Reading the PDF and preparing AI Assistant..."):

            vectorstore = VectorStore(
                pdf_path=temporary_pdf_path,
                cohere_api_key=COHERE_API_KEY,
                pinecone_api_key=PINECONE_API_KEY,
            )

            with fitz.open(temporary_pdf_path) as pdf_document:
                page_count = len(pdf_document)

        document_id, is_new = save_document(
            name=uploaded_file.name,
            fingerprint=fingerprint,
            pdf_data=pdf_bytes,
            namespace=vectorstore.document_namespace,
            page_count=page_count,
        )

        welcome_message = (
            f"I have analyzed **{uploaded_file.name}**. "
            "You can now ask questions about this document."
        )

        save_message(
            document_id=document_id,
            role="assistant",
            content=welcome_message,
        )

        st.session_state["active_document_id"] = document_id
        st.session_state["pdf_name"] = uploaded_file.name
        st.session_state["pdf_bytes"] = pdf_bytes
        st.session_state["pdf_fingerprint"] = fingerprint
        st.session_state["vectorstore"] = vectorstore
        st.session_state["pdf_page_number"] = 0
        st.session_state["messages"] = get_messages(document_id)

        st.success("Document saved and ready to use.")

    except Exception as error:

        st.error(
            "The document could not be processed.\n\n"
            f"Error details: {error}"
        )

    finally:

        if temporary_pdf_path and os.path.exists(temporary_pdf_path):
            os.remove(temporary_pdf_path)


# =========================================================
# NAVIGATION AND PDF UPLOAD
# =========================================================

current_page = render_navigation("Workspace")

with st.sidebar:

    st.markdown(
        '<div class="ai-sidebar-divider"></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ai-sidebar-label">UPLOAD DOCUMENT</div>',
        unsafe_allow_html=True,
    )

    uploaded_pdf = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
        key=f"pdf_uploader_{st.session_state['pdf_uploader_version']}",
    )

    if uploaded_pdf is not None:
        process_uploaded_pdf(uploaded_pdf)


# =========================================================
# TOPBAR
# =========================================================

render_topbar(st.session_state["pdf_name"])


# =========================================================
# BACK TO WORKSPACE
# =========================================================

def show_back_to_workspace() -> None:

    if st.button(
        "← Back to Workspace",
        key=f"back_to_workspace_{current_page}",
    ):

        st.session_state["current_page"] = "Workspace"
        st.rerun()


# =========================================================
# OPEN DOCUMENT ACTION
# =========================================================

def activate_document(document_id: int) -> None:
    """Open a saved PDF and return to the workspace."""

    if open_saved_document(document_id):
        st.session_state["current_page"] = "Workspace"
        st.rerun()


# =========================================================
# WORKSPACE PAGE
# =========================================================

if current_page == "Workspace":

    pdf_column, chat_column = st.columns(
        [1.08, 1],
        gap="large",
    )

    # -----------------------------------------------------
    # PDF VIEWER
    # -----------------------------------------------------

    with pdf_column:

        st.markdown(
            '<div class="panel-heading">Document viewer</div>',
            unsafe_allow_html=True,
        )

        if st.session_state["pdf_bytes"]:

            try:

                pdf_document = fitz.open(
                    stream=st.session_state["pdf_bytes"],
                    filetype="pdf",
                )

                total_pages = len(pdf_document)

                current_page_number = min(
                    st.session_state["pdf_page_number"],
                    total_pages - 1,
                )

                previous_column, counter_column, next_column = (
                    st.columns([1, 2, 1])
                )

                with previous_column:

                    if st.button(
                        "← Previous",
                        use_container_width=True,
                        disabled=current_page_number == 0,
                    ):

                        st.session_state["pdf_page_number"] = (
                            current_page_number - 1
                        )
                        st.rerun()

                with counter_column:

                    st.markdown(
                        f"""
                        <div class="page-counter">
                            Page <b>{current_page_number + 1}</b>
                            of <b>{total_pages}</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with next_column:

                    if st.button(
                        "Next →",
                        use_container_width=True,
                        disabled=current_page_number >= total_pages - 1,
                    ):

                        st.session_state["pdf_page_number"] = (
                            current_page_number + 1
                        )
                        st.rerun()

                pdf_page = pdf_document.load_page(current_page_number)

                pdf_pixmap = pdf_page.get_pixmap(
                    matrix=fitz.Matrix(1.5, 1.5),
                    alpha=False,
                )

                st.image(
                    pdf_pixmap.tobytes("png"),
                    use_container_width=True,
                )

                pdf_document.close()

            except Exception as error:
                st.error(
                    f"The PDF viewer could not display this document: {error}"
                )

        else:

            st.markdown(
                """
                <div class="empty-state">
                    <div class="empty-icon">▤</div>
                    <b>No document uploaded</b>
                    <span>
                        Upload a PDF from the left sidebar or open
                        a saved document from Documents.
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -----------------------------------------------------
    # CHAT ASSISTANT
    # -----------------------------------------------------

    with chat_column:

        st.markdown(
            '<div class="panel-heading">AI Assistant</div>',
            unsafe_allow_html=True,
        )

        chat_container = st.container(height=780)

        with chat_container:

            if not st.session_state["messages"]:
                st.info("Upload a PDF and ask a question to begin.")

            for message in st.session_state["messages"]:

                with st.chat_message(message["role"]):

                    st.markdown(message["content"])

                    sources = message.get("sources", [])

                    if sources:

                        with st.expander("View source context"):

                            for source_number, source in enumerate(
                                sources,
                                start=1,
                            ):

                                source_page = source.get("page", "Unknown")

                                st.markdown(
                                    f"**Source {source_number} · "
                                    f"Page {source_page}**"
                                )

                                st.caption(source.get("text", ""))

        user_question = st.chat_input(
            "Ask any question about your document..."
        )

        if user_question:

            document_id = st.session_state["active_document_id"]

            if (
                st.session_state["vectorstore"] is None
                or document_id is None
            ):

                st.warning("Please upload or open a PDF document first.")

            else:

                user_message = {
                    "role": "user",
                    "content": user_question,
                }

                st.session_state["messages"].append(user_message)

                save_message(
                    document_id=document_id,
                    role="user",
                    content=user_question,
                )

                with chat_container:

                    with st.chat_message("user"):
                        st.markdown(user_question)

                    with st.chat_message("assistant"):

                        try:

                            with st.spinner("Searching your document..."):

                                assistant = Chatbot(
                                    vectorstore=st.session_state["vectorstore"],
                                    cohere_api_key=COHERE_API_KEY,
                                )

                                response_stream, sources = assistant.respond(
                                    user_question
                                )

                                answer = st.write_stream(
                                    event.text
                                    for event in response_stream
                                    if getattr(
                                        event,
                                        "event_type",
                                        "",
                                    ) == "text-generation"
                                )

                                if sources:

                                    with st.expander("View source context"):

                                        for source_number, source in enumerate(
                                            sources,
                                            start=1,
                                        ):

                                            source_page = source.get(
                                                "page",
                                                "Unknown",
                                            )

                                            st.markdown(
                                                f"**Source {source_number} · "
                                                f"Page {source_page}**"
                                            )

                                            st.caption(source.get("text", ""))

                            st.session_state["messages"].append({
                                "role": "assistant",
                                "content": answer,
                                "sources": sources,
                            })

                            save_message(
                                document_id=document_id,
                                role="assistant",
                                content=answer,
                                sources=sources,
                            )

                        except Exception as error:

                            error_message = (
                                "Sorry, I could not generate an answer. "
                                f"Error: {error}"
                            )

                            st.error(error_message)

                            st.session_state["messages"].append({
                                "role": "assistant",
                                "content": error_message,
                            })

                            save_message(
                                document_id=document_id,
                                role="assistant",
                                content=error_message,
                            )


# =========================================================
# DOCUMENTS PAGE
# =========================================================

elif current_page == "Documents":

    st.markdown(
        """
        <div class="documents-header">
            <div class="documents-title">Documents</div>
            <div class="documents-subtitle">
                Your saved PDFs and conversations, all in one place.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    documents = list_documents()

    # -----------------------------------------------------
    # SEARCH AND FILTER
    # -----------------------------------------------------

    search_column, filter_column = st.columns(
        [2.2, 1],
        vertical_alignment="center",
    )

    with search_column:

        search_query = st.text_input(
            "Search",
            placeholder="Search documents by name...",
            label_visibility="collapsed",
            key="document_search",
        )

    with filter_column:

        selected_filter = st.selectbox(
            "Filter",
            options=[
                "All documents",
                "Currently open",
                "With chat history",
            ],
            label_visibility="collapsed",
            key="document_filter",
        )

    # -----------------------------------------------------
    # FILTER DOCUMENTS
    # -----------------------------------------------------

    filtered_documents = []

    for document in documents:

        document_id = document["id"]

        is_active = (
            st.session_state["active_document_id"] == document_id
        )

        has_chat = document["message_count"] > 0

        if (
            search_query.strip()
            and search_query.strip().lower()
            not in document["name"].lower()
        ):
            continue

        if selected_filter == "Currently open" and not is_active:
            continue

        if selected_filter == "With chat history" and not has_chat:
            continue

        filtered_documents.append(document)

    # -----------------------------------------------------
    # LIBRARY HEADING
    # -----------------------------------------------------

    st.markdown(
        f"""
        <div class="document-library-heading">
            <span>Your document library</span>
            <span class="document-total">
                {len(filtered_documents)} documents
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------
    # EMPTY STATES
    # -----------------------------------------------------

    if not documents:

        st.markdown(
            """
            <div class="documents-empty">
                <div class="documents-empty-icon">📄</div>
                <div class="documents-empty-title">
                    No documents uploaded yet
                </div>
                <div class="documents-empty-text">
                    Upload a PDF using the sidebar to get started.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif not filtered_documents:

        st.markdown(
            """
            <div class="documents-empty">
                <div class="documents-empty-title">
                    No matching documents
                </div>
                <div class="documents-empty-text">
                    Try a different search term or filter.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------
    # COMPACT DOCUMENT CARDS (GRID LAYOUT)
    # -----------------------------------------------------

    else:

        # Display two small cards side-by-side per row
        for row_start in range(0, len(filtered_documents), 2):

            card_columns = st.columns(2, gap="medium")

            for column_index in range(2):

                document_index = row_start + column_index

                if document_index >= len(filtered_documents):
                    break

                document = filtered_documents[document_index]

                document_id = document["id"]
                document_name = document["name"]
                page_count = document["page_count"]
                chat_count = document["message_count"]

                is_active = (
                    st.session_state["active_document_id"] == document_id
                )

                raw_date = document.get("created_at", "")

                upload_date = (
                    str(raw_date)[:10]
                    if raw_date
                    else "Not available"
                )

                with card_columns[column_index]:

                    with st.container(
                        border=True,
                        key=f"document_card_{document_id}",
                    ):

                        # ---------------------------------
                        # PDF ICON, NAME AND STATUS
                        # ---------------------------------

                        icon_column, name_column = st.columns(
                            [0.5, 4],
                            vertical_alignment="center",
                        )

                        with icon_column:

                            st.markdown(
                                """
                                <div style="
                                    width:36px;
                                    height:36px;
                                    display:flex;
                                    align-items:center;
                                    justify-content:center;
                                    border-radius:8px;
                                    background:#FEF3C7;
                                    font-size:18px;
                                ">📄</div>
                                """,
                                unsafe_allow_html=True,
                            )

                        with name_column:

                            safe_name = html.escape(str(document_name))

                            st.markdown(
                                f"""
                                <div style="
                                    font-size:13px;
                                    font-weight:650;
                                    color:#1F2937;
                                    white-space:nowrap;
                                    overflow:hidden;
                                    text-overflow:ellipsis;
                                " title="{safe_name}">{safe_name}</div>
                                """,
                                unsafe_allow_html=True,
                            )

                            if is_active:

                                st.markdown(
                                    """
                                    <span style="
                                        color:#059669;
                                        font-size:10px;
                                        font-weight:600;
                                    ">● Currently open</span>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            else:

                                st.caption("PDF document")

                        # ---------------------------------
                        # COMPACT METRICS BOX
                        # ---------------------------------

                        st.markdown(
                            f"""
                            <div style="
                                display:grid;
                                grid-template-columns: repeat(3, 1fr);
                                gap:8px;
                                padding:10px 12px;
                                margin:10px 0;
                                background:#F9FAFB;
                                border:1px solid #F3F4F6;
                                border-radius:8px;
                                text-align:center;
                            ">
                                <div>
                                    <div style="font-size:14px; font-weight:700; color:#111827;">{page_count}</div>
                                    <div style="font-size:10px; color:#6B7280; text-transform:uppercase; letter-spacing:0.03em;">Pages</div>
                                </div>
                                <div>
                                    <div style="font-size:14px; font-weight:700; color:#111827;">{chat_count}</div>
                                    <div style="font-size:10px; color:#6B7280; text-transform:uppercase; letter-spacing:0.03em;">Questions</div>
                                </div>
                                <div>
                                    <div style="font-size:12px; font-weight:650; color:#111827; padding-top:2px;">{html.escape(upload_date)}</div>
                                    <div style="font-size:10px; color:#6B7280; text-transform:uppercase; letter-spacing:0.03em;">Uploaded</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # ---------------------------------
                        # ACTION BUTTONS WITH CLEAR SEPARATION
                        # ---------------------------------

                        open_column, chat_column, delete_column = st.columns(
                            [1, 1.3, 1],
                            gap="small",
                        )

                        with open_column:

                            if st.button(
                                "Open",
                                key=f"open_{document_id}",
                                use_container_width=True,
                            ):

                                activate_document(document_id)

                        with chat_column:

                            if st.button(
                                "Continue Chat",
                                key=f"continue_{document_id}",
                                use_container_width=True,
                            ):

                                activate_document(document_id)

                        with delete_column:

                            if st.button(
                                "Delete",
                                key=f"delete_{document_id}",
                                use_container_width=True,
                            ):

                                st.session_state[
                                    f"confirm_delete_{document_id}"
                                ] = True

                        # ---------------------------------
                        # DELETE CONFIRMATION PROMPT
                        # ---------------------------------

                        if st.session_state.get(
                            f"confirm_delete_{document_id}",
                            False,
                        ):

                            st.warning("Delete this document permanently?")

                            yes_column, no_column = st.columns(2)

                            with yes_column:

                                if st.button(
                                    "Yes, Delete",
                                    key=f"confirm_{document_id}",
                                    use_container_width=True,
                                ):

                                    delete_document(document_id)

                                    if is_active:
                                        reset_document()

                                    st.session_state.pop(
                                        f"confirm_delete_{document_id}",
                                        None,
                                    )

                                    st.rerun()

                            with no_column:

                                if st.button(
                                    "Cancel",
                                    key=f"cancel_{document_id}",
                                    use_container_width=True,
                                ):

                                    st.session_state.pop(
                                        f"confirm_delete_{document_id}",
                                        None,
                                    )

                                    st.rerun()


# =========================================================
# SETTINGS PAGE
# =========================================================

elif current_page == "Settings":

    render_settings_page()


# =========================================================
# HELP AND ABOUT PAGE
# =========================================================

elif current_page == "Help & About":

    st.markdown(
        '<div class="page-title">Help & About</div>',
        unsafe_allow_html=True,
    )

    show_back_to_workspace()

    st.markdown(
        """
        ### How to use AI Assistant

        1. Upload a PDF using the left sidebar.
        2. Browse the document using the page controls.
        3. Ask questions in the AI Assistant chat.
        4. Open the source context to inspect retrieved text.
        5. Visit Documents to reopen previous PDFs and conversations.

        ### Example questions

        - What is the main purpose of this document?
        - Summarize the key findings.
        - What does the document say about this topic?
        - Which dates or organizations are mentioned?
        - Explain this section in simple language.

        ### Possible limitations

        AI Assistant may have difficulty with scanned PDFs,
        image-only documents, complicated tables, charts,
        unclear questions, or information that is not present
        in the uploaded document.
        """
    )
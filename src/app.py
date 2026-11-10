
from __future__ import annotations

import hashlib
import html
import os
import queue
import re
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

import fitz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from chatbot import Chatbot
from components.sidebar import render_navigation
from components.topbar import render_topbar
from database import (
    initialize_database,
    save_document,
    get_document,
    get_document_by_fingerprint,
    list_documents,
    save_message,
    get_messages,
    delete_document,
    create_conversation,
    list_conversations,
)
from pages.settings import render_settings_page
from vectorstore import VectorStore


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
# LOAD CUSTOM CSS
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
        "active_conversation_id": None,
        "selected_chat_document_id": None,
        "pdf_uploader_version": 0,
        "start_new_chat_requested": False,
        "generation_tasks": {},
    }

    for key, value in default_values.items():

        if key not in st.session_state:
            st.session_state[key] = value


def reset_document() -> None:
    """
    Clear the active workspace without deleting
    the saved PDF or its previous conversations.
    """

    st.session_state["messages"] = []
    st.session_state["vectorstore"] = None
    st.session_state["pdf_name"] = None
    st.session_state["pdf_bytes"] = None
    st.session_state["pdf_fingerprint"] = None
    st.session_state["pdf_page_number"] = 0

    st.session_state["active_document_id"] = None
    st.session_state["active_conversation_id"] = None
    st.session_state["selected_chat_document_id"] = None

    # Clear old background responses from the Workspace.
    st.session_state.setdefault("generation_tasks", {})
    st.session_state["generation_tasks"].clear()

    st.session_state["start_new_chat_requested"] = False

    # Reset the PDF upload control.
    st.session_state["pdf_uploader_version"] = (
        st.session_state.get("pdf_uploader_version", 0) + 1
    )


initialize_session_state()


# =========================================================
# MERMAID DIAGRAM RENDERING
# =========================================================

def render_message_with_mermaid(content: str) -> None:
    """
    Render normal Markdown and Mermaid code blocks.
    """

    parts = re.split(
        r"```mermaid\s*(.*?)```",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for index, part in enumerate(parts):

        if index % 2 == 0:

            if part.strip():
                st.markdown(part)

        else:

            mermaid_code = html.escape(part.strip())

            diagram_html = f"""
            <!DOCTYPE html>
            <html>
            <head>

                <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>

                <style>
                    body {{
                        margin: 0;
                        padding: 10px;
                        background: transparent;
                        font-family: Arial, sans-serif;
                    }}

                    .mermaid {{
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        width: 100%;
                        overflow-x: auto;
                    }}

                    svg {{
                        max-width: 100%;
                        height: auto;
                    }}
                </style>

            </head>

            <body>

                <pre class="mermaid">{mermaid_code}</pre>

                <script>
                    mermaid.initialize({{
                        startOnLoad: false,
                        theme: "default",
                        securityLevel: "strict"
                    }});

                    mermaid.run({{
                        querySelector: ".mermaid"
                    }}).catch(function(error) {{
                        document.body.innerHTML =
                            "<p>Unable to render this diagram. Please check the Mermaid syntax.</p>";
                    }});
                </script>

            </body>
            </html>
            """

            components.html(
                diagram_html,
                height=450,
                scrolling=True,
            )


# =========================================================
# SOURCE DISPLAY
# =========================================================

def render_source_context(sources: list[dict]) -> None:
    """
    Display PDF page references and clickable web references.
    """

    if not sources:
        return

    with st.expander("View source context"):

        for source_number, source in enumerate(
            sources,
            start=1,
        ):

            source_type = source.get(
                "source_type",
                source.get("source", "pdf"),
            )

            source_text = source.get(
                "text",
                source.get("content", ""),
            )

            # WEB SOURCES
            if source_type == "web":

                title = str(
                    source.get("title", "Web source")
                )

                url = source.get("url", "")

                st.markdown(
                    f"**Web Source {source_number} · {title}**"
                )

                if (
                    isinstance(url, str)
                    and url.startswith(("https://", "http://"))
                ):

                    st.markdown(
                        f"[Open website]({url})"
                    )

                if source_text:
                    st.caption(source_text)

            # PDF SOURCES
            else:

                source_page = source.get(
                    "page",
                    "Unknown",
                )

                st.markdown(
                    f"**PDF Source {source_number} · Page {source_page}**"
                )

                if source_text:
                    st.caption(source_text)


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
# CONVERSATION HELPERS
# =========================================================

def create_new_conversation(document_id: int) -> int:
    """Create a new conversation for a saved document."""

    conversation_id = create_conversation(
        document_id=document_id,
        title="New chat",
    )

    welcome_message = (
        f"I have analyzed **{st.session_state['pdf_name']}**. "
        "You can now ask questions about this document."
    )

    save_message(
        document_id=document_id,
        conversation_id=conversation_id,
        role="assistant",
        content=welcome_message,
    )

    st.session_state["active_document_id"] = document_id
    st.session_state["active_conversation_id"] = conversation_id
    st.session_state["messages"] = get_messages(conversation_id)

    return conversation_id


def load_conversation(
    document_id: int,
    conversation_id: int,
) -> bool:
    """Load one saved conversation."""

    try:

        conversation_messages = get_messages(conversation_id)

        st.session_state["active_document_id"] = document_id
        st.session_state["active_conversation_id"] = conversation_id
        st.session_state["messages"] = conversation_messages

        return True

    except Exception as error:

        st.error(
            "The selected conversation could not be opened.\n\n"
            f"Error details: {error}"
        )

        return False


# =========================================================
# OPEN SAVED PDF
# =========================================================

def open_saved_document(
    document_id: int,
    conversation_id: int | None = None,
    start_new_chat: bool = False,
) -> bool:
    """
    Reopen a PDF from the database.

    A supplied conversation ID restores that conversation.
    start_new_chat creates a fresh conversation.
    Otherwise, the latest conversation is opened.
    """

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

        vectorstore.load_pdf()

        st.session_state["active_document_id"] = document_id
        st.session_state["pdf_name"] = document["name"]
        st.session_state["pdf_bytes"] = pdf_bytes
        st.session_state["pdf_fingerprint"] = document["fingerprint"]
        st.session_state["vectorstore"] = vectorstore
        st.session_state["pdf_page_number"] = 0

        if start_new_chat:

            create_new_conversation(document_id)

        elif conversation_id is not None:

            if not load_conversation(
                document_id,
                conversation_id,
            ):
                return False

        else:

            previous_conversations = list_conversations(document_id)

            if previous_conversations:

                latest_conversation_id = previous_conversations[0]["id"]

                if not load_conversation(
                    document_id,
                    latest_conversation_id,
                ):
                    return False

            else:

                create_new_conversation(document_id)

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
# PROCESS UPLOADED PDF
# =========================================================

def process_uploaded_pdf(uploaded_file) -> bool:
    """
    Save a new PDF or reuse an existing PDF.

    Every successful upload starts a fresh conversation.
    The same PDF is not indexed or stored a second time.
    """

    if not COHERE_API_KEY:
        st.error("COHERE_API_KEY is missing from your .env file.")
        return False

    if not PINECONE_API_KEY:
        st.error("PINECONE_API_KEY is missing from your .env file.")
        return False

    pdf_bytes = uploaded_file.getvalue()

    fingerprint = hashlib.sha256(pdf_bytes).hexdigest()

    if (
        st.session_state["pdf_fingerprint"] == fingerprint
        and st.session_state["active_document_id"] is not None
        and st.session_state["active_conversation_id"] is not None
    ):
        return False

    existing_document = get_document_by_fingerprint(fingerprint)

    if existing_document:

        opened = open_saved_document(
            document_id=existing_document["id"],
            start_new_chat=True,
        )

        if opened:
            st.success(
                "Previously saved PDF opened. A new chat has been started."
            )

        return opened

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

        document_id, _ = save_document(
            name=uploaded_file.name,
            fingerprint=fingerprint,
            pdf_data=pdf_bytes,
            namespace=vectorstore.document_namespace,
            page_count=page_count,
        )

        st.session_state["active_document_id"] = document_id
        st.session_state["pdf_name"] = uploaded_file.name
        st.session_state["pdf_bytes"] = pdf_bytes
        st.session_state["pdf_fingerprint"] = fingerprint
        st.session_state["vectorstore"] = vectorstore
        st.session_state["pdf_page_number"] = 0

        create_new_conversation(document_id)

        st.success("Document saved and ready to use.")

        return True

    except Exception as error:

        st.error(
            "The document could not be processed.\n\n"
            f"Error details: {error}"
        )

        return False

    finally:

        if temporary_pdf_path and os.path.exists(temporary_pdf_path):
            os.remove(temporary_pdf_path)


# =========================================================
# BACKGROUND AI GENERATION
# =========================================================

def generate_answer_in_background(
    task_queue: queue.Queue,
    vectorstore: Any,
    user_question: str,
    document_id: int,
    conversation_id: int,
    cohere_api_key: str,
) -> None:
    """
    Generate an answer independently of Streamlit.
    """

    try:

        assistant = Chatbot(
            vectorstore=vectorstore,
            cohere_api_key=cohere_api_key,
        )

        response_stream, sources = assistant.respond(user_question)

        task_queue.put(("sources", sources))

        answer_parts = []

        for event in response_stream:

            if getattr(event, "event_type", "") == "text-generation":

                text_part = getattr(event, "text", "")

                if text_part:

                    answer_parts.append(text_part)

                    task_queue.put(("chunk", text_part))

        answer = "".join(answer_parts).strip()

        if not answer:
            answer = "The AI could not generate a response. Please try again."

        save_message(
            document_id=document_id,
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            sources=sources,
        )

        task_queue.put(("done", answer))

    except Exception as error:

        error_message = (
            "Sorry, I could not generate an answer. "
            f"Error: {error}"
        )

        try:

            save_message(
                document_id=document_id,
                conversation_id=conversation_id,
                role="assistant",
                content=error_message,
            )

        except Exception:
            pass

        task_queue.put(("error", error_message))


# =========================================================
# START BACKGROUND GENERATION
# =========================================================

def start_answer_generation(
    user_question: str,
    document_id: int,
    conversation_id: int,
) -> None:
    """Start AI generation without blocking the Streamlit script."""

    vectorstore = st.session_state["vectorstore"]

    task_id = uuid.uuid4().hex
    task_queue = queue.Queue()

    task = {
        "id": task_id,
        "queue": task_queue,
        "document_id": document_id,
        "conversation_id": conversation_id,
        "question": user_question,
        "answer": "",
        "sources": [],
        "status": "running",
        "message_added": False,
    }

    st.session_state["generation_tasks"][task_id] = task

    st.session_state["messages"].append({
        "role": "user",
        "content": user_question,
    })

    save_message(
        document_id=document_id,
        conversation_id=conversation_id,
        role="user",
        content=user_question,
    )

    generation_thread = threading.Thread(
        target=generate_answer_in_background,
        kwargs={
            "task_queue": task_queue,
            "vectorstore": vectorstore,
            "user_question": user_question,
            "document_id": document_id,
            "conversation_id": conversation_id,
            "cohere_api_key": COHERE_API_KEY,
        },
        daemon=True,
    )

    generation_thread.start()


# =========================================================
# ACTIVATE DOCUMENT OR CONVERSATION
# =========================================================

def activate_document(document_id: int) -> None:
    """Open a saved PDF with a fresh conversation."""

    if open_saved_document(
        document_id=document_id,
        start_new_chat=True,
    ):

        st.session_state["current_page"] = "Workspace"
        st.rerun()


def activate_conversation(
    document_id: int,
    conversation_id: int,
) -> None:
    """Open a particular previous conversation."""

    if open_saved_document(
        document_id=document_id,
        conversation_id=conversation_id,
    ):

        st.session_state["current_page"] = "Workspace"
        st.session_state["selected_chat_document_id"] = None
        st.rerun()


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

current_page = render_navigation("Workspace")


# =========================================================
# HANDLE NEW CHAT REQUEST
# =========================================================

if st.session_state.get("start_new_chat_requested", False):

    st.session_state["start_new_chat_requested"] = False

    active_document_id = st.session_state.get("active_document_id")

    if active_document_id is not None:

        # Keep the currently uploaded PDF.
        # Only create a new conversation.
        create_new_conversation(active_document_id)

    else:

        st.session_state["messages"] = []


# =========================================================
# PDF UPLOAD
# =========================================================

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

        uploaded_successfully = process_uploaded_pdf(uploaded_pdf)

        if uploaded_successfully:
            st.rerun()


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
# CHAT HISTORY AND BACKGROUND RESPONSE DISPLAY
# =========================================================

@st.fragment(run_every=0.3)
def render_chat_history():
    """
    Display chat history and background responses.
    """

    active_conversation_id = st.session_state.get(
        "active_conversation_id"
    )

    # Collect background generation events.
    for task in list(
        st.session_state["generation_tasks"].values()
    ):

        task_queue = task["queue"]

        while True:

            try:
                event_type, event_data = task_queue.get_nowait()

            except queue.Empty:
                break

            if event_type == "sources":
                task["sources"] = event_data or []

            elif event_type == "chunk":
                task["answer"] += event_data

            elif event_type == "done":
                task["answer"] = event_data
                task["status"] = "completed"

            elif event_type == "error":
                task["answer"] = event_data
                task["status"] = "failed"

        # Add the completed response to its original chat.
        if (
            task["status"] in ("completed", "failed")
            and not task["message_added"]
            and task["conversation_id"] == active_conversation_id
        ):

            st.session_state["messages"].append({
                "role": "assistant",
                "content": task["answer"],
                "sources": task["sources"],
            })

            task["message_added"] = True

    # Scrollable message area.
    chat_container = st.container(height=920)

    with chat_container:

        if not st.session_state["messages"]:

            if st.session_state.get("pdf_bytes") is None:
                st.info("Upload a PDF and ask a question to begin.")
            else:
                st.info("Ask a question about your uploaded document.")

        for message in st.session_state["messages"]:

            with st.chat_message(message["role"]):

                render_message_with_mermaid(
                    message.get("content", "")
                )

                sources = message.get("sources", [])

                if sources:
                    render_source_context(sources)

        # Active background generation.
        for task in st.session_state["generation_tasks"].values():

            if (
                task["conversation_id"] != active_conversation_id
                or task["status"] != "running"
            ):
                continue

            with st.chat_message("assistant"):

                if task["answer"]:

                    render_message_with_mermaid(
                        task["answer"]
                    )

                else:

                    st.markdown("Thinking...")

                if task["sources"]:
                    render_source_context(task["sources"])

    # Chat input below the message area.
    user_question = st.chat_input(
        "Ask any question about your document...",
        key="workspace_chat_input",
        disabled=st.session_state.get("vectorstore") is None,
    )

    if user_question:

        document_id = st.session_state.get(
            "active_document_id"
        )

        conversation_id = st.session_state.get(
            "active_conversation_id"
        )

        if (
            st.session_state["vectorstore"] is None
            or document_id is None
            or conversation_id is None
        ):

            st.warning(
                "Please upload or open a PDF document first."
            )

        else:

            start_answer_generation(
                user_question=user_question,
                document_id=document_id,
                conversation_id=conversation_id,
            )


# =========================================================
# WORKSPACE PAGE
# =========================================================

if current_page == "Workspace":

    pdf_column, chat_column = st.columns(
        [1.08, 1],
        gap="large",
    )

    # PDF VIEWER
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
                        key="workspace_pdf_previous",
                        type="secondary",
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
                        key="workspace_pdf_next",
                        type="secondary",
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

    # CHAT ASSISTANT
    with chat_column:

        st.markdown(
            '<div class="panel-heading">AI Assistant</div>',
            unsafe_allow_html=True,
        )

        render_chat_history()


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

    # SEARCH AND FILTER
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

    # FILTER DOCUMENTS
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

    # LIBRARY HEADING
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

    # EMPTY STATES
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

    # DOCUMENT CARDS
    else:

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

                raw_date = document["created_at"] or ""

                upload_date = (
                    str(raw_date)[:10]
                    if raw_date
                    else "Not available"
                )

                with card_columns[column_index]:

                    with st.container(border=True):

                        # PDF ICON AND DOCUMENT NAME
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

                        # DOCUMENT METRICS
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
                                    <div style="
                                        font-size:14px;
                                        font-weight:700;
                                        color:#111827;
                                    ">{page_count}</div>
                                    <div style="
                                        font-size:10px;
                                        color:#6B7280;
                                        text-transform:uppercase;
                                        letter-spacing:0.03em;
                                    ">Pages</div>
                                </div>
                                <div>
                                    <div style="
                                        font-size:14px;
                                        font-weight:700;
                                        color:#111827;
                                    ">{chat_count}</div>
                                    <div style="
                                        font-size:10px;
                                        color:#6B7280;
                                        text-transform:uppercase;
                                        letter-spacing:0.03em;
                                    ">Messages</div>
                                </div>
                                <div>
                                    <div style="
                                        font-size:12px;
                                        font-weight:650;
                                        color:#111827;
                                        padding-top:2px;
                                    ">{html.escape(upload_date)}</div>
                                    <div style="
                                        font-size:10px;
                                        color:#6B7280;
                                        text-transform:uppercase;
                                        letter-spacing:0.03em;
                                    ">Uploaded</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # DOCUMENT ACTIONS
                        open_column, chats_column, delete_column = st.columns(
                            [1, 1.3, 1],
                            gap="small",
                        )

                        with open_column:

                            if st.button(
                                "Open PDF",
                                key=f"open_{document_id}",
                                use_container_width=True,
                            ):

                                activate_document(document_id)

                        with chats_column:

                            if st.button(
                                "Open Chats",
                                key=f"chats_{document_id}",
                                use_container_width=True,
                            ):

                                current_selection = st.session_state.get(
                                    "selected_chat_document_id"
                                )

                                if current_selection == document_id:

                                    st.session_state[
                                        "selected_chat_document_id"
                                    ] = None

                                else:

                                    st.session_state[
                                        "selected_chat_document_id"
                                    ] = document_id

                        with delete_column:

                            if st.button(
                                "Delete",
                                key=f"delete_{document_id}",
                                use_container_width=True,
                            ):

                                st.session_state[
                                    f"confirm_delete_{document_id}"
                                ] = True

                        # PREVIOUS CONVERSATIONS
                        if (
                            st.session_state.get(
                                "selected_chat_document_id"
                            ) == document_id
                        ):

                            st.markdown("**Previous chats**")

                            previous_conversations = list_conversations(
                                document_id
                            )

                            if not previous_conversations:

                                st.caption(
                                    "No previous conversations are available."
                                )

                            else:

                                for conversation in previous_conversations:

                                    conversation_id = conversation["id"]

                                    conversation_title = (
                                        conversation["title"] or "Untitled chat"
                                    )

                                    conversation_date = (
                                        conversation["updated_at"]
                                        or conversation["created_at"]
                                        or ""
                                    )

                                    date_text = (
                                        str(conversation_date)[:16]
                                        if conversation_date
                                        else ""
                                    )

                                    button_label = (
                                        f"{conversation_title}  ·  "
                                        f"{date_text}"
                                    )

                                    if st.button(
                                        button_label,
                                        key=f"open_conversation_{conversation_id}",
                                        use_container_width=True,
                                    ):

                                        activate_conversation(
                                            document_id,
                                            conversation_id,
                                        )

                        # DELETE CONFIRMATION
                        if st.session_state.get(
                            f"confirm_delete_{document_id}",
                            False,
                        ):

                            st.warning(
                                "Delete this document and all its saved chats permanently?"
                            )

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

                                    if (
                                        st.session_state.get(
                                            "selected_chat_document_id"
                                        ) == document_id
                                    ):

                                        st.session_state[
                                            "selected_chat_document_id"
                                        ] = None

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
        - Draw a flowchart explaining this process.
        - Create a sequence diagram for this concept.

        ### Possible limitations

        AI Assistant may have difficulty with scanned PDFs,
        image-only documents, complicated tables, charts,
        unclear questions, or information that is not present
        in the uploaded document.

        Mermaid diagrams require an internet connection
        to load the diagram-rendering library.
        """
    )

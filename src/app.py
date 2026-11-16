
from __future__ import annotations

import hashlib
import html
import json
import os
import queue
import re
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import fitz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from chatbot import Chatbot
from vectorstore import VectorStore
from components.sidebar import render_navigation
from components.topbar import render_topbar
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
    create_conversation,
    list_conversations,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")

COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")

st.set_page_config(
    page_title="AI PDF Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()


# ============================================================
# ORIGINAL STYLESHEET
# ============================================================

CSS_FILE = BASE_DIR / "assets" / "styles.css"

if CSS_FILE.exists():
    css = CSS_FILE.read_text(encoding="utf-8")
    st.markdown(
        "<style>" + css + "</style>",
        unsafe_allow_html=True,
    )


# ============================================================
# DOCUMENTS AND DIAGRAM STYLING
# ============================================================

st.markdown(
    """
<style>
/* Documents page */

.ai-doc-page-title {
    font-size: 27px !important;
    font-weight: 750 !important;
    color: #173f32 !important;
    margin: 0 0 5px 0;
}

.ai-doc-page-subtitle {
    font-size: 12px !important;
    color: #73887b !important;
    margin-bottom: 22px;
}

.ai-library-heading {
    font-size: 13px !important;
    font-weight: 700;
    color: #1b4935 !important;
    margin: 16px 0;
}

.ai-doc-title {
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: 1.4;
    color: #173e30 !important;
    overflow-wrap: anywhere;
}

.ai-doc-subtitle {
    font-size: 10px !important;
    color: #789083 !important;
    margin-top: 3px;
}

.ai-doc-icon {
    background: #e5f2e9;
    border-radius: 9px;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}

.ai-doc-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
    padding: 12px 8px;
    margin: 12px 0;
    background: #f0f6f2;
    border: 1px solid #dfebe3;
    border-radius: 9px;
}

.ai-doc-metric {
    text-align: center;
    min-width: 0;
}

.ai-doc-metric-value {
    font-size: 13px !important;
    font-weight: 750 !important;
    line-height: 1.4;
    color: #173f32 !important;
    overflow-wrap: anywhere;
}

.ai-doc-metric-label {
    font-size: 9px !important;
    font-weight: 650;
    color: #71877a !important;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: .03em;
}

/* Protocol-header diagrams */

.ai-packet {
    background: #fff;
    border: 1px solid #d7e8dd;
    border-radius: 12px;
    padding: 14px;
    margin: 12px 0;
    overflow-x: auto;
    color: #173f32;
}

.ai-packet-title {
    font-size: 13px;
    font-weight: 750;
    margin-bottom: 12px;
    color: #173f32;
}

.ai-packet-row {
    display: flex;
    width: 100%;
    min-width: 380px;
    gap: 3px;
    margin-bottom: 4px;
}

.ai-packet-field {
    min-height: 58px;
    padding: 8px 4px;
    background: #e5f3e9;
    border: 1px solid #8fbea0;
    border-radius: 5px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    overflow-wrap: anywhere;
}

.ai-packet-name {
    color: #173f32 !important;
    font-size: 11px;
    font-weight: 700;
}

.ai-packet-bits {
    color: #4f7960 !important;
    font-size: 9px;
    margin-top: 4px;
}

.ai-packet-note {
    font-size: 10px;
    color: #71877b;
    margin-top: 8px;
}

@media (max-width: 768px) {
    .ai-doc-title {
        font-size: 12px !important;
    }

    .ai-doc-metric-value {
        font-size: 11px !important;
    }
}
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

def initialize_session_state():

    defaults = {
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
        "settings_show_sources": True,
        "settings_confirm_delete": True,
        "settings_pdf_view": "Fit Width",
        "settings_answer_style": "Detailed",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()


# ============================================================
# HELPERS
# ============================================================

def escape_text(value):
    return html.escape(str(value), quote=True)


def create_temporary_pdf(pdf_bytes):

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
    ) as temp:
        temp.write(pdf_bytes)
        return temp.name


def reset_document():

    st.session_state["messages"] = []
    st.session_state["vectorstore"] = None
    st.session_state["pdf_name"] = None
    st.session_state["pdf_bytes"] = None
    st.session_state["pdf_fingerprint"] = None
    st.session_state["pdf_page_number"] = 0
    st.session_state["active_document_id"] = None
    st.session_state["active_conversation_id"] = None
    st.session_state["selected_chat_document_id"] = None
    st.session_state["start_new_chat_requested"] = False
    st.session_state["pdf_uploader_version"] += 1


# ============================================================
# COLORFUL MERMAID RENDERER
# ============================================================

def render_message_with_mermaid(content):

    if not content:
        return

    parts = re.split(
        r"```mermaid[ \t]*\n?(.*?)```",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for index, part in enumerate(parts):

        if index % 2 == 0:
            if part.strip():
                st.markdown(part)
            continue

        diagram = part.strip()

        if not diagram:
            continue

        escaped = html.escape(
            diagram,
            quote=False,
        )

        diagram_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
html,body {
    margin:0;
    padding:0;
    background:#fff;
    font-family:Arial,sans-serif;
}
.wrapper {
    background:#fff;
    border:1px solid #dbe9df;
    border-radius:12px;
    padding:20px;
    overflow:auto;
    min-height:150px;
}
.mermaid {
    display:flex;
    justify-content:center;
    color:#173f32;
}
.mermaid svg {
    max-width:100%;
    height:auto;
}
.error {
    color:#a33b3b;
    font-size:13px;
}
</style>
</head>
<body>
<div class="wrapper">
<pre class="mermaid">__DIAGRAM__</pre>
</div>
<script>
mermaid.initialize({
    startOnLoad:false,
    securityLevel:"strict",
    theme:"base",
    themeVariables:{
        background:"#ffffff",
        primaryColor:"#dff2e5",
        primaryTextColor:"#173f32",
        primaryBorderColor:"#529b70",
        secondaryColor:"#dcecff",
        secondaryTextColor:"#173f32",
        secondaryBorderColor:"#729ed0",
        tertiaryColor:"#fff0cf",
        tertiaryTextColor:"#664c19",
        tertiaryBorderColor:"#d5aa57",
        lineColor:"#477965",
        textColor:"#173f32",
        fontSize:"14px",
        fontFamily:"Arial, sans-serif",
        edgeLabelBackground:"#ffffff",
        clusterBkg:"#f1f8f3",
        clusterBorder:"#a5c8b0"
    },
    flowchart:{
        htmlLabels:true,
        curve:"basis",
        padding:18,
        nodeSpacing:40,
        rankSpacing:55,
        useMaxWidth:true
    }
});

mermaid.run({
    querySelector:".mermaid"
}).catch(function(error){
    const wrapper=document.querySelector(".wrapper");
    wrapper.textContent="Unable to render this Mermaid diagram.";
    wrapper.classList.add("error");
});
</script>
</body>
</html>
        """

        diagram_html = diagram_html.replace(
            "__DIAGRAM__",
            escaped,
        )

        components.html(
            diagram_html,
            height=500,
            scrolling=True,
        )


# ============================================================
# PACKET HEADER RENDERER
# ============================================================

def render_packet_header(raw_json):

    try:
        data = json.loads(raw_json)

        if not isinstance(data, dict):
            raise ValueError("Invalid packet data.")

        title = escape_text(
            data.get("title", "Packet Header")
        )

        rows = data.get("rows", [])

        if not isinstance(rows, list) or not rows:
            raise ValueError("No packet rows found.")

        rendered_rows = []

        for row in rows:

            if not isinstance(row, list):
                raise ValueError("Invalid packet row.")

            fields = []

            for field in row:

                if not isinstance(field, dict):
                    raise ValueError("Invalid field.")

                name = escape_text(
                    field.get("name", "Field")
                )

                bits = int(field.get("bits", 0))

                if bits <= 0:
                    raise ValueError("Invalid bit width.")

                width = max(bits, 8)

                fields.append(
                    '<div class="ai-packet-field" '
                    f'style="flex:{width} 1 0;min-width:0;">'
                    f'<div class="ai-packet-name">{name}</div>'
                    f'<div class="ai-packet-bits">{bits} bits</div>'
                    '</div>'
                )

            rendered_rows.append(
                '<div class="ai-packet-row">'
                + "".join(fields)
                + '</div>'
            )

        packet_html = (
            '<div class="ai-packet">'
            f'<div class="ai-packet-title">{title}</div>'
            + "".join(rendered_rows)
            + '<div class="ai-packet-note">'
            'Field sizes are shown in bits. '
            'Narrow fields are enlarged for readability.'
            '</div></div>'
        )

        st.markdown(
            packet_html,
            unsafe_allow_html=True,
        )

    except (ValueError, TypeError, KeyError):
        st.warning(
            "The packet-header diagram could not be rendered."
        )
        st.code(raw_json, language="json")


# ============================================================
# COMBINED AI ANSWER RENDERER
# ============================================================

def render_ai_answer(content):

    if not content:
        return

    parts = re.split(
        r"```packet-header[ \t]*\n?(.*?)```",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for index, part in enumerate(parts):

        if index % 2 == 0:
            render_message_with_mermaid(part)
        else:
            render_packet_header(part.strip())


# ============================================================
# CLEAN SOURCE CONTEXT
# ============================================================

def clean_source_text(value):

    if value is None:
        return ""

    text = str(value)
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    cleaned = []

    for line in text.splitlines():

        stripped = line.strip()

        if re.fullmatch(
            r"(?:[-*•]+|\d+[.)])",
            stripped,
        ):
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def render_source_context(sources):

    if not sources:
        return

    if not st.session_state.get(
        "settings_show_sources",
        True,
    ):
        return

    cleaned_sources = []
    seen = set()

    for source in sources:

        if not isinstance(source, dict):
            continue

        text = clean_source_text(
            source.get(
                "text",
                source.get("content", ""),
            )
        )

        if not text:
            continue

        key = (
            str(source.get("page", "")),
            str(source.get("url", "")),
            text,
        )

        if key in seen:
            continue

        seen.add(key)

        cleaned_sources.append({
            **source,
            "text": text,
        })

        if len(cleaned_sources) >= 6:
            break

    if not cleaned_sources:
        return

    with st.expander(
        f"View source context ({len(cleaned_sources)})"
    ):

        for index, source in enumerate(
            cleaned_sources,
            start=1,
        ):

            source_type = source.get(
                "source_type",
                "pdf",
            )

            source_text = source["text"][:1200]

            if source_type == "web":

                title = source.get(
                    "title",
                    "Web source",
                )

                st.markdown(
                    f"**Web Source {index}: "
                    f"{escape_text(title)}**"
                )

                url = str(source.get("url", ""))
                parsed = urlparse(url)

                if (
                    parsed.scheme in ("http", "https")
                    and parsed.netloc
                ):
                    st.link_button(
                        "Open website",
                        url,
                        key=(
                            f"web_source_{index}_"
                            f"{hashlib.sha256(url.encode()).hexdigest()[:12]}"
                        ),
                    )

            else:

                page = source.get(
                    "page",
                    "Unknown",
                )

                st.markdown(
                    f"**PDF Source {index} · "
                    f"Page {escape_text(page)}**"
                )

            st.text(source_text)

            if index < len(cleaned_sources):
                st.divider()


# ============================================================
# CONVERSATIONS
# ============================================================

def create_new_conversation(document_id):

    conversation_id = create_conversation(
        document_id=document_id,
        title="New chat",
    )

    welcome = (
        f"I have analyzed **{st.session_state['pdf_name']}**. "
        "You can now ask questions about this document."
    )

    save_message(
        document_id=document_id,
        conversation_id=conversation_id,
        role="assistant",
        content=welcome,
    )

    st.session_state["active_document_id"] = document_id
    st.session_state["active_conversation_id"] = conversation_id
    st.session_state["messages"] = get_messages(conversation_id)

    return conversation_id


def load_conversation(document_id, conversation_id):

    try:
        messages = get_messages(conversation_id)

        st.session_state["active_document_id"] = document_id
        st.session_state["active_conversation_id"] = conversation_id
        st.session_state["messages"] = messages

        return True

    except Exception as error:
        st.error(f"Unable to load conversation: {error}")
        return False


# ============================================================
# OPEN SAVED PDF
# ============================================================

def open_saved_document(
    document_id,
    conversation_id=None,
    start_new_chat=False,
):

    if not COHERE_API_KEY or not PINECONE_API_KEY:
        st.error(
            "Please configure Cohere and Pinecone API keys."
        )
        return False

    document = get_document(document_id)

    if document is None:
        st.error("Document not found.")
        return False

    temporary_path = None

    try:
        pdf_bytes = bytes(document["pdf_data"])

        temporary_path = create_temporary_pdf(pdf_bytes)

        with st.spinner("Opening saved PDF..."):

            vectorstore = VectorStore(
                pdf_path=temporary_path,
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

            conversations = list_conversations(document_id)

            if conversations:

                if not load_conversation(
                    document_id,
                    conversations[0]["id"],
                ):
                    return False

            else:

                create_new_conversation(document_id)

        return True

    except Exception as error:
        st.error(f"Unable to open PDF: {error}")
        return False

    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


# ============================================================
# UPLOAD PDF
# ============================================================

def process_uploaded_pdf(uploaded_file):

    if not COHERE_API_KEY:
        st.error("COHERE_API_KEY is missing.")
        return False

    if not PINECONE_API_KEY:
        st.error("PINECONE_API_KEY is missing.")
        return False

    pdf_bytes = uploaded_file.getvalue()

    if not pdf_bytes:
        st.error("Uploaded PDF is empty.")
        return False

    fingerprint = hashlib.sha256(pdf_bytes).hexdigest()

    if (
        st.session_state.get("pdf_fingerprint") == fingerprint
        and st.session_state.get("active_document_id") is not None
        and st.session_state.get("active_conversation_id") is not None
    ):
        return False

    existing = get_document_by_fingerprint(fingerprint)

    if existing:
        return open_saved_document(
            existing["id"],
            start_new_chat=True,
        )

    temporary_path = None

    try:
        temporary_path = create_temporary_pdf(pdf_bytes)

        with st.spinner("Processing PDF..."):

            with fitz.open(temporary_path) as document:
                page_count = len(document)

                if page_count == 0:
                    raise ValueError("PDF has no pages.")

            vectorstore = VectorStore(
                pdf_path=temporary_path,
                cohere_api_key=COHERE_API_KEY,
                pinecone_api_key=PINECONE_API_KEY,
            )

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

        st.success("PDF uploaded successfully.")

        return True

    except Exception as error:
        st.error(f"Unable to process PDF: {error}")
        return False

    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


# ============================================================
# BACKGROUND ANSWER GENERATION
# ============================================================

def generate_answer_in_background(
    task_queue,
    vectorstore,
    user_question,
    document_id,
    conversation_id,
    cohere_api_key,
):

    try:
        chatbot = Chatbot(
            vectorstore=vectorstore,
            cohere_api_key=cohere_api_key,
        )

        response_stream, sources = chatbot.respond(user_question)

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
            answer = (
                "The AI could not generate a response. "
                "Please try again."
            )

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
            f"Details: {error}"
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


def start_answer_generation(
    user_question,
    document_id,
    conversation_id,
):

    for task in st.session_state["generation_tasks"].values():

        if (
            task["conversation_id"] == conversation_id
            and task["status"] == "running"
        ):
            st.warning("Please wait for the current answer.")
            return

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

    save_message(
        document_id=document_id,
        conversation_id=conversation_id,
        role="user",
        content=user_question,
    )

    st.session_state["messages"].append({
        "role": "user",
        "content": user_question,
    })

    st.session_state["generation_tasks"][task_id] = task

    thread = threading.Thread(
        target=generate_answer_in_background,
        kwargs={
            "task_queue": task_queue,
            "vectorstore": st.session_state["vectorstore"],
            "user_question": user_question,
            "document_id": document_id,
            "conversation_id": conversation_id,
            "cohere_api_key": COHERE_API_KEY,
        },
        daemon=True,
    )

    thread.start()


def update_generation_tasks():

    active_conversation_id = st.session_state.get(
        "active_conversation_id"
    )

    for task_id, task in list(
        st.session_state["generation_tasks"].items()
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

        if task["status"] not in ("completed", "failed"):
            continue

        if (
            task["conversation_id"] == active_conversation_id
            and not task["message_added"]
        ):
            st.session_state["messages"].append({
                "role": "assistant",
                "content": task["answer"],
                "sources": task["sources"],
            })

            task["message_added"] = True

        st.session_state["generation_tasks"].pop(task_id, None)


# ============================================================
# CHAT PANEL
# ============================================================

@st.fragment(run_every=0.3)
def render_chat_history():

    update_generation_tasks()

    active_conversation_id = st.session_state.get(
        "active_conversation_id"
    )

    with st.container(height=760):

        messages = st.session_state["messages"]

        if not messages:

            if st.session_state.get("pdf_bytes") is None:
                st.info("Upload a PDF to start chatting.")
            else:
                st.info("Ask a question about your PDF.")

        for message in messages:

            role = message.get("role", "assistant")

            with st.chat_message(role):

                render_ai_answer(
                    message.get("content", "")
                )

                sources = message.get("sources", [])

                if sources:
                    render_source_context(sources)

        for task in st.session_state["generation_tasks"].values():

            if task["conversation_id"] != active_conversation_id:
                continue

            if task["status"] != "running":
                continue

            with st.chat_message("assistant"):

                if task["answer"]:
                    render_ai_answer(task["answer"])
                else:
                    st.markdown("Thinking...")

                if task["sources"]:
                    render_source_context(task["sources"])

    user_question = st.chat_input(
        "Ask anything about your PDF...",
        key="workspace_chat_input",
        disabled=(
            st.session_state.get("vectorstore") is None
        ),
    )

    if not user_question:
        return

    document_id = st.session_state.get(
        "active_document_id"
    )

    conversation_id = st.session_state.get(
        "active_conversation_id"
    )

    if (
        st.session_state.get("vectorstore") is None
        or document_id is None
        or conversation_id is None
    ):
        st.warning("Please open a PDF first.")
        return

    start_answer_generation(
        user_question,
        document_id,
        conversation_id,
    )

    st.rerun(scope="fragment")


# ============================================================
# PDF VIEWER
# ============================================================

def render_pdf_viewer():

    st.markdown(
        '<div class="panel-heading">Document Viewer</div>',
        unsafe_allow_html=True,
    )

    pdf_bytes = st.session_state.get("pdf_bytes")

    if not pdf_bytes:
        st.info(
            "No document is open. Upload a PDF "
            "or open a saved document."
        )
        return

    try:
        with fitz.open(
            stream=pdf_bytes,
            filetype="pdf",
        ) as document:

            total_pages = len(document)

            if total_pages == 0:
                st.warning("PDF has no pages.")
                return

            current_page = max(
                0,
                min(
                    st.session_state["pdf_page_number"],
                    total_pages - 1,
                ),
            )

            previous_col, counter_col, next_col = st.columns(
                [1, 2, 1]
            )

            with previous_col:

                if st.button(
                    "← Previous",
                    key="pdf_previous",
                    disabled=current_page == 0,
                    use_container_width=True,
                ):
                    st.session_state["pdf_page_number"] = (
                        current_page - 1
                    )
                    st.rerun()

            with counter_col:

                counter_html = (
                    '<div class="page-counter">'
                    f'Page <b>{current_page + 1}</b> '
                    f'of <b>{total_pages}</b>'
                    '</div>'
                )

                st.markdown(
                    counter_html,
                    unsafe_allow_html=True,
                )

            with next_col:

                if st.button(
                    "Next →",
                    key="pdf_next",
                    disabled=current_page >= total_pages - 1,
                    use_container_width=True,
                ):
                    st.session_state["pdf_page_number"] = (
                        current_page + 1
                    )
                    st.rerun()

            page = document.load_page(current_page)

            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5),
                alpha=False,
            )

            st.image(
                pixmap.tobytes("png"),
                use_container_width=True,
            )

    except Exception as error:
        st.error(f"Unable to display PDF: {error}")


# ============================================================
# DOCUMENT NAVIGATION
# ============================================================

def activate_document(document_id):

    if open_saved_document(
        document_id,
        start_new_chat=True,
    ):
        st.session_state["current_page"] = "Workspace"
        st.rerun()


def activate_conversation(document_id, conversation_id):

    if open_saved_document(
        document_id,
        conversation_id=conversation_id,
    ):
        st.session_state["current_page"] = "Workspace"
        st.session_state["selected_chat_document_id"] = None
        st.rerun()


# ============================================================
# COMPACT DOCUMENT CARD — CORRECTED
# ============================================================

def render_document_card(document):

    document_id = document["id"]
    document_name = document["name"]

    page_count = document.get("page_count", 0)
    message_count = document.get("message_count", 0)

    raw_date = document.get("created_at", "")
    upload_date = str(raw_date)[:10] if raw_date else "—"

    is_active = (
        st.session_state.get("active_document_id")
        == document_id
    )

    safe_name = escape_text(document_name)

    with st.container(border=True):

        # Document title

        icon_col, name_col = st.columns(
            [0.5, 4],
            vertical_alignment="center",
        )

        with icon_col:
            st.markdown(
                '<div class="ai-doc-icon">📄</div>',
                unsafe_allow_html=True,
            )

        with name_col:

            status = (
                "● Currently open"
                if is_active
                else "PDF document"
            )

            title_html = (
                f'<div class="ai-doc-title">{safe_name}</div>'
                f'<div class="ai-doc-subtitle">{status}</div>'
            )

            st.markdown(
                title_html,
                unsafe_allow_html=True,
            )

        # =================================================
        # FIX: NO INDENTED MULTILINE HTML
        # =================================================

        metrics_html = (
            '<div class="ai-doc-metrics">'
            '<div class="ai-doc-metric">'
            f'<div class="ai-doc-metric-value">{int(page_count)}</div>'
            '<div class="ai-doc-metric-label">Pages</div>'
            '</div>'
            '<div class="ai-doc-metric">'
            f'<div class="ai-doc-metric-value">{int(message_count)}</div>'
            '<div class="ai-doc-metric-label">Messages</div>'
            '</div>'
            '<div class="ai-doc-metric">'
            f'<div class="ai-doc-metric-value">{escape_text(upload_date)}</div>'
            '<div class="ai-doc-metric-label">Uploaded</div>'
            '</div>'
            '</div>'
        )

        st.markdown(
            metrics_html,
            unsafe_allow_html=True,
        )

        # Document actions

        open_col, chat_col, delete_col = st.columns(
            [1, 1.2, 1],
            gap="small",
        )

        with open_col:

            if st.button(
                "Open PDF",
                key=f"open_{document_id}",
                use_container_width=True,
            ):
                activate_document(document_id)

        with chat_col:

            if st.button(
                "Open Chats",
                key=f"chats_{document_id}",
                use_container_width=True,
            ):

                selected = st.session_state.get(
                    "selected_chat_document_id"
                )

                st.session_state[
                    "selected_chat_document_id"
                ] = (
                    None
                    if selected == document_id
                    else document_id
                )

                st.rerun()

        with delete_col:

            if st.button(
                "Delete",
                key=f"delete_{document_id}",
                use_container_width=True,
            ):
                st.session_state[
                    f"confirm_delete_{document_id}"
                ] = True

                st.rerun()

        # Previous conversations

        if (
            st.session_state.get(
                "selected_chat_document_id"
            ) == document_id
        ):

            st.markdown("**Previous conversations**")

            conversations = list_conversations(document_id)

            if not conversations:
                st.caption("No saved conversations.")

            for conversation in conversations:

                conversation_id = conversation["id"]

                title = (
                    conversation.get("title")
                    or "Untitled chat"
                )

                if st.button(
                    title,
                    key=f"conversation_{conversation_id}",
                    use_container_width=True,
                ):
                    activate_conversation(
                        document_id,
                        conversation_id,
                    )

        # Delete confirmation

        confirm_key = f"confirm_delete_{document_id}"

        if st.session_state.get(confirm_key, False):

            st.warning(
                "Delete this PDF and all saved conversations?"
            )

            yes_col, no_col = st.columns(2)

            with yes_col:

                if st.button(
                    "Yes, Delete",
                    key=f"yes_{document_id}",
                    use_container_width=True,
                ):

                    running = any(
                        task["document_id"] == document_id
                        and task["status"] == "running"
                        for task in st.session_state[
                            "generation_tasks"
                        ].values()
                    )

                    if running:

                        st.error(
                            "Wait for the current AI answer "
                            "before deleting this document."
                        )

                    else:

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
                            confirm_key,
                            None,
                        )

                        st.rerun()

            with no_col:

                if st.button(
                    "Cancel",
                    key=f"cancel_{document_id}",
                    use_container_width=True,
                ):
                    st.session_state.pop(
                        confirm_key,
                        None,
                    )
                    st.rerun()


# ============================================================
# DOCUMENTS PAGE
# ============================================================

def render_documents_page():

    st.markdown(
        '<div class="ai-doc-page-title">Documents</div>'
        '<div class="ai-doc-page-subtitle">'
        'Manage your uploaded PDFs and saved conversations.'
        '</div>',
        unsafe_allow_html=True,
    )

    documents = list_documents()

    search_col, filter_col = st.columns(
        [2.2, 1]
    )

    with search_col:

        search_query = st.text_input(
            "Search documents",
            placeholder="Search documents by name...",
            label_visibility="collapsed",
            key="document_search",
        )

    with filter_col:

        selected_filter = st.selectbox(
            "Filter",
            [
                "All documents",
                "Currently open",
                "With chat history",
            ],
            label_visibility="collapsed",
            key="document_filter",
        )

    filtered = []

    for document in documents:

        document_id = document["id"]

        is_active = (
            st.session_state.get("active_document_id")
            == document_id
        )

        has_chat = (
            document.get("message_count", 0) > 0
        )

        if (
            search_query.strip()
            and search_query.lower().strip()
            not in document["name"].lower()
        ):
            continue

        if (
            selected_filter == "Currently open"
            and not is_active
        ):
            continue

        if (
            selected_filter == "With chat history"
            and not has_chat
        ):
            continue

        filtered.append(document)

    heading_html = (
        '<div class="ai-library-heading">'
        f'Your document library · {len(filtered)} documents'
        '</div>'
    )

    st.markdown(
        heading_html,
        unsafe_allow_html=True,
    )

    if not documents:
        st.info(
            "No documents uploaded yet. "
            "Upload a PDF from the sidebar."
        )
        return

    if not filtered:
        st.info("No matching documents.")
        return

    for start in range(0, len(filtered), 2):

        columns = st.columns(
            2,
            gap="medium",
        )

        for col_index in range(2):

            index = start + col_index

            if index >= len(filtered):
                break

            with columns[col_index]:
                render_document_card(
                    filtered[index]
                )


# ============================================================
# HELP AND ABOUT
# ============================================================

def render_about_page():

    st.title("Help & About")

    st.markdown(
        """
### AI PDF Assistant

Upload PDFs, ask questions, solve assignments,
and create technical diagrams.

### How to use

1. Upload a PDF from the sidebar.
2. Wait for document processing.
3. Ask questions in the Workspace.
4. View PDF or web sources below answers.
5. Open Documents to revisit saved conversations.

### Example questions

- Solve Question 3 completely.
- Explain Question 2(b).
- Draw the IPv6 base header.
- Create a flowchart for binary search.
- Solve this numerical problem step by step.
- Summarize the uploaded PDF.

### Supported diagrams

- Mermaid flowcharts
- Process diagrams
- Sequence diagrams
- State diagrams
- Network packet-header diagrams

### Limitations

Scanned PDFs and embedded screenshots may
require OCR or image understanding, which
the current text-extraction pipeline does not provide.

Mermaid rendering requires internet access
to load its JavaScript library.
        """
    )


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

current_page = render_navigation("Workspace")


# ============================================================
# NEW CHAT
# ============================================================

if st.session_state.get(
    "start_new_chat_requested",
    False,
):

    st.session_state["start_new_chat_requested"] = False

    document_id = st.session_state.get(
        "active_document_id"
    )

    if document_id is not None:
        create_new_conversation(document_id)
    else:
        st.session_state["messages"] = []


# ============================================================
# SIDEBAR PDF UPLOAD
# ============================================================

with st.sidebar:

    st.markdown("---")

    st.markdown("**UPLOAD DOCUMENT**")

    uploaded_pdf = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
        key=(
            f"pdf_uploader_"
            f"{st.session_state['pdf_uploader_version']}"
        ),
    )

    if uploaded_pdf is not None:

        if process_uploaded_pdf(uploaded_pdf):

            st.session_state["current_page"] = "Workspace"
            st.rerun()


# ============================================================
# TOPBAR
# ============================================================

render_topbar(
    st.session_state.get("pdf_name")
)


# ============================================================
# PAGE ROUTING
# ============================================================

if current_page == "Workspace":

    pdf_col, chat_col = st.columns(
        [1.08, 1],
        gap="large",
    )

    with pdf_col:
        render_pdf_viewer()

    with chat_col:

        st.markdown(
            '<div class="panel-heading">'
            'AI Assistant'
            '</div>',
            unsafe_allow_html=True,
        )

        render_chat_history()


elif current_page == "Documents":

    render_documents_page()


elif current_page == "Settings":

    render_settings_page()


elif current_page == "Help & About":

    render_about_page()

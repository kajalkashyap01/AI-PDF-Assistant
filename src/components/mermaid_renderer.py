
from __future__ import annotations

import html
import json
import re
import uuid

import streamlit as st
import streamlit.components.v1 as components


MERMAID_PATTERN = re.compile(
    r"```mermaid[ \t]*\r?\n(.*?)```",
    flags=re.IGNORECASE | re.DOTALL,
)

INCOMPLETE_PATTERN = re.compile(
    r"```mermaid\b",
    flags=re.IGNORECASE,
)


def render_mermaid_diagram(diagram_code: str) -> None:
    """Render a complete Mermaid diagram in Streamlit."""

    diagram_code = diagram_code.strip()

    if not diagram_code:
        return

    diagram_id = "mermaid_" + uuid.uuid4().hex

    safe_code = html.escape(
        diagram_code,
        quote=True,
    )

    safe_id = json.dumps(diagram_id)

    diagram_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">

        <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                padding: 12px;
                background: transparent;
                font-family: Arial, sans-serif;
            }

            .diagram-container {
                width: 100%;
                min-height: 100px;
                overflow: auto;
                text-align: center;
            }

            .mermaid {
                display: flex;
                justify-content: center;
                width: 100%;
            }

            .mermaid svg {
                max-width: 100%;
                height: auto;
            }

            .error {
                padding: 12px;
                border-radius: 8px;
                color: #9b2525;
                background: #fff0f0;
                font-size: 13px;
            }
        </style>
    </head>

    <body>
        <div class="diagram-container">
            <pre class="mermaid" id="DIAGRAM_ID">DIAGRAM_CODE</pre>
        </div>

        <script>
            async function drawDiagram() {
                const target = document.getElementById(
                    DIAGRAM_ID_JSON
                );

                try {
                    if (typeof mermaid === "undefined") {
                        throw new Error(
                            "Mermaid library could not be loaded."
                        );
                    }

                    mermaid.initialize({
                        startOnLoad: false,
                        theme: "default",
                        securityLevel: "strict",
                        flowchart: {
                            useMaxWidth: true,
                            htmlLabels: false
                        }
                    });

                    await mermaid.run({
                        nodes: [target]
                    });

                } catch (error) {
                    console.error(error);

                    target.textContent = (
                        "Unable to render this diagram. " +
                        "Please check the Mermaid syntax."
                    );

                    target.className = "error";
                }
            }

            drawDiagram();
        </script>
    </body>
    </html>
    """

    diagram_html = diagram_html.replace(
        "DIAGRAM_ID_JSON",
        safe_id,
    )

    diagram_html = diagram_html.replace(
        "DIAGRAM_ID",
        diagram_id,
    )

    diagram_html = diagram_html.replace(
        "DIAGRAM_CODE",
        safe_code,
    )

    components.html(
        diagram_html,
        height=520,
        scrolling=True,
    )


def render_message_with_mermaid(content: str) -> None:
    """
    Render Markdown and completed Mermaid diagrams.

    Incomplete diagrams are displayed as code until
    the AI finishes streaming the complete block.
    """

    if not content:
        return

    last_position = 0

    for match in MERMAID_PATTERN.finditer(content):

        preceding_text = content[
            last_position:match.start()
        ]

        if preceding_text.strip():
            st.markdown(preceding_text)

        diagram_code = match.group(1).strip()

        if diagram_code:
            render_mermaid_diagram(diagram_code)

        last_position = match.end()

    remaining_text = content[last_position:]

    if not remaining_text.strip():
        return

    incomplete_match = INCOMPLETE_PATTERN.search(
        remaining_text
    )

    if incomplete_match:

        normal_text = remaining_text[
            :incomplete_match.start()
        ]

        unfinished_code = remaining_text[
            incomplete_match.end():
        ].strip()

        if normal_text.strip():
            st.markdown(normal_text)

        if unfinished_code:
            st.code(
                unfinished_code,
                language="text",
            )
        else:
            st.caption("Generating flowchart...")

    else:
        st.markdown(remaining_text)

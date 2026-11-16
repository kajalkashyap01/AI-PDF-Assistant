
from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st


PACKET_HEADER_PATTERN = re.compile(
    r"```packet-header\s*\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)


def _validate_header(data: Any) -> dict:
    """Validate the structure before rendering."""

    if not isinstance(data, dict):
        raise ValueError("Diagram must be a JSON object.")

    title = str(data.get("title", "Packet Header"))
    rows = data.get("rows")

    if not isinstance(rows, list) or not rows:
        raise ValueError("Diagram must contain rows.")

    validated_rows = []

    for row in rows:
        if not isinstance(row, list) or not row:
            raise ValueError("Each row must contain fields.")

        validated_fields = []

        for field in row:
            if not isinstance(field, dict):
                raise ValueError("Invalid field.")

            name = str(field.get("name", "")).strip()
            bits = field.get("bits")

            if not name:
                raise ValueError("A field name is missing.")

            if not isinstance(bits, int) or bits <= 0:
                raise ValueError("Field width must be positive.")

            validated_fields.append({
                "name": name,
                "bits": bits,
            })

        validated_rows.append(validated_fields)

    return {
        "title": title,
        "rows": validated_rows,
    }


def render_packet_header(
    diagram_code: str,
) -> None:
    """
    Render a structured network header with
    field widths proportional to bit sizes.
    """

    try:
        data = _validate_header(
            json.loads(diagram_code)
        )

    except (ValueError, TypeError, json.JSONDecodeError):
        st.warning(
            "The packet-header diagram could not be rendered."
        )
        with st.expander("View diagram data"):
            st.code(diagram_code, language="json")
        return

    st.markdown(
        f"**{data['title']}**"
    )

    st.markdown(
        '<div class="ai-packet-header">',
        unsafe_allow_html=True,
    )

    for row in data["rows"]:

        total_bits = sum(
            field["bits"] for field in row
        )

        columns = st.columns(
            [field["bits"] for field in row],
            gap="small",
        )

        for column, field in zip(columns, row):
            with column:
                st.markdown(
                    f"""
                    <div class="ai-packet-field">
                        <span class="ai-packet-field-name">
                            {field["name"]}
                        </span>
                        <span class="ai-packet-field-bits">
                            {field["bits"]} bits
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.caption(f"{total_bits} bits")

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


def render_packet_headers_in_message(
    content: str,
    render_other_content,
) -> None:
    """
    Render packet headers and delegate other
    Markdown/Mermaid content to the existing renderer.
    """

    last_position = 0

    for match in PACKET_HEADER_PATTERN.finditer(content):

        before = content[last_position:match.start()]

        if before.strip():
            render_other_content(before)

        render_packet_header(
            match.group(1).strip()
        )

        last_position = match.end()

    remaining = content[last_position:]

    if remaining.strip():
        render_other_content(remaining)

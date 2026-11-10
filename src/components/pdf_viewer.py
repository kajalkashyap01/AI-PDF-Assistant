
import streamlit as st
import fitz


def render_pdf_viewer(pdf_bytes):

    st.markdown(
        '<div class="panel-heading">Document viewer</div>',
        unsafe_allow_html=True,
    )

    # ---------------------------------------------
    # EMPTY DOCUMENT STATE
    # ---------------------------------------------

    if pdf_bytes is None:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon"></div>
                <b>No document uploaded</b>
                <span>
                    Upload a PDF from the left sidebar or open
                    a saved document from Documents.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:

        with fitz.open(
            stream=pdf_bytes,
            filetype="pdf",
        ) as doc:

            total_pages = len(doc)

            if total_pages == 0:
                st.warning("This PDF does not contain any pages.")
                return

            # ---------------------------------------------
            # INITIALIZE PAGE NUMBER
            # ---------------------------------------------

            if "pdf_page_number" not in st.session_state:
                st.session_state["pdf_page_number"] = 0

            current_page = max(
                0,
                min(
                    int(st.session_state["pdf_page_number"]),
                    total_pages - 1,
                ),
            )

            st.session_state["pdf_page_number"] = current_page

            # ---------------------------------------------
            # PAGE NAVIGATION
            # ---------------------------------------------

            previous_col, counter_col, next_col = st.columns(
                [1, 2, 1],
                vertical_alignment="center",
            )

            # PREVIOUS BUTTON
            with previous_col:

                if st.button(
                    "← Previous",
                    key="pdf_previous",
                    use_container_width=True,
                    disabled=current_page == 0,
                    type="secondary",
                ):

                    st.session_state["pdf_page_number"] = (
                        current_page - 1
                    )

                    st.rerun()

            # PAGE COUNTER
            with counter_col:

                st.markdown(
                    f"""
                    <div class="page-counter">
                        Page <b>{current_page + 1}</b>
                        of <b>{total_pages}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # NEXT BUTTON
            with next_col:

                if st.button(
                    "Next →",
                    key="pdf_next",
                    use_container_width=True,
                    disabled=current_page >= total_pages - 1,
                    type="secondary",
                ):

                    st.session_state["pdf_page_number"] = (
                        current_page + 1
                    )

                    st.rerun()

            # ---------------------------------------------
            # DISPLAY PDF PAGE
            # ---------------------------------------------

            st.markdown(
                '<div class="pdf-page-container">',
                unsafe_allow_html=True,
            )

            page = doc.load_page(current_page)

            pix = page.get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5),
                alpha=False,
            )

            st.image(
                pix.tobytes("png"),
                use_container_width=True,
            )

            st.markdown(
                '</div>',
                unsafe_allow_html=True,
            )

    except Exception as error:

        st.error(
            f"Unable to display this PDF: {error}"
        )

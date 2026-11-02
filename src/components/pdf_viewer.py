import streamlit as st
import fitz

def render_pdf_viewer(pdf_bytes):
    st.markdown("### 📖 PDF Viewer")
    if pdf_bytes is not None:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀ Prev") and st.session_state["current_page"] > 0:
                st.session_state["current_page"] -= 1
                st.rerun()
        with c2:
            st.markdown(f"<p style='text-align:center; margin:5px;'>Page <b>{st.session_state['current_page'] + 1}</b> of {total_pages}</p>", unsafe_allow_html=True)
        with c3:
            if st.button("Next ▶") and st.session_state["current_page"] < total_pages - 1:
                st.session_state["current_page"] += 1
                st.rerun()
        
        page = doc.load_page(st.session_state["current_page"])
        pix = page.get_pixmap(dpi=150)
        st.image(pix.tobytes("png"), use_container_width=True)
    else:
        st.info("👈 Please upload a PDF document from the sidebar to begin viewing.")
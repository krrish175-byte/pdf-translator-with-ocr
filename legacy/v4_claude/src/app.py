import streamlit as st
import os
from converter import PDFTranslator

st.set_page_config(page_title="PDF Translator (Claude AI)", layout="wide")

st.title("📄 AI-Powered PDF Translator")
st.markdown("Translates PDFs while preserving layout using **Anthropic Claude 3.5 Sonnet**.")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Claude API Key")
    
    source_lang = st.selectbox("Source Language", ["English", "Chinese", "Japanese", "French", "Spanish"], index=0)
    target_lang = st.selectbox("Target Language", ["Japanese", "English", "Chinese", "French", "Spanish"], index=0)

    st.info("Note: heavily visual PDFs work best. Processing may take time depending on page count.")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file and api_key:
    if st.button("Translate PDF"):
        translator = PDFTranslator(api_key)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(text, value):
            status_text.text(text)
            progress_bar.progress(value)
            
        try:
            pdf_bytes = uploaded_file.read()
            translated_pdf = translator.translate_pdf(
                pdf_bytes, 
                source_lang, 
                target_lang, 
                progress_callback=update_progress
            )
            
            update_progress("Done!", 1.0)
            
            st.success("Translation Complete!")
            st.download_button(
                label="Download Translated PDF",
                data=translated_pdf,
                file_name=f"translated_{uploaded_file.name}",
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            
elif uploaded_file and not api_key:
    st.warning("Please enter your Anthropic API Key to proceed.")

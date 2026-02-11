# Gemini-Powered PDF Translator

A modern PDF translator using **Google Gemini 1.5 Flash** (Free Tier) to translate English/Chinese PDFs to Japanese (and vice-versa) while preserving visual layout.

## Features
- **Layout Preservation**: Uses Gemini's vision capabilities to reconstruct HTML/CSS matching the original PDF.
- **Multimodal**: Handles text, tables, and images.
- **Web Interface**: Simple file upload and configuration via Streamlit.
- **Cost**: Uses the Free Tier of Google Gemini API.

## Setup


1. **Install Dependencies**:
   It is recommended to use a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or .\venv\Scripts\activate on Windows
   
   pip install -r requirements.txt
   ```
   *Note: Ensure `poppler` is installed (`brew install poppler` on macOS) for `pdf2image`.*

2. **Run Application**:
   ```bash
   streamlit run src/app.py
   ```

## Usage
1. Open the local URL (usually `http://localhost:8501`).
2. Enter your **Gemini API Key** in the sidebar.
   - [Get a Free Key Here](https://aistudio.google.com/apikey)
3. Select Source and Target languages.
4. Upload a PDF file.
5. Click **Translate PDF**.
6. Download the result once processing is complete.

## Architecture
- **Frontend**: Streamlit
- **PDF Processing**: `pdf2image`, `weasyprint`, `pymupdf`
- **AI Engine**: Google Generative AI (Gemini 1.5 Flash)

## Limitations
- Processing speed depends on PDF size and Gemini API latency.
- Large PDFs may require splitting or hit rate limits (though Free Tier is generous).

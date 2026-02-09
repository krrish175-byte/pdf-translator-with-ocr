# PDF Translator with OCR

A web application that translates PDF documents between English, Japanese, and Chinese while preserving formatting and translating text within images using OCR.

## Features

- 🌐 **Multi-Language Support** - Translate between English, Japanese, and Chinese
- 📄 **PDF Text Translation** - Extract and translate all text content from PDFs
- 🖼️ **OCR Image Translation** - Detect and translate text within images  
- 📊 **Real-time Progress** - Live progress updates during translation
- 👁️ **Preview** - View translated pages before downloading
- 🎨 **Modern UI** - Clean white & red theme with drag-and-drop upload

## Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `ja` | 日本語 (Japanese) |
| `zh` | 中文 (Chinese Simplified) |

## Requirements

- Python 3.10+
- Tesseract OCR (with language packs)
- Poppler

## Installation

### 1. Install System Dependencies

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng tesseract-ocr-chi-sim poppler-utils
```

**Windows:**
1. Download and install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Download Poppler from: https://github.com/osborne/poppler-windows/releases
3. Add both to your system PATH

### 2. Clone & Setup Python Environment

```bash
git clone https://github.com/YOUR_USERNAME/pdf-translator-with-ocr.git
cd pdf-translator-with-ocr

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

Open http://localhost:5001 in your browser.

## Usage

1. Drag and drop a PDF file or click to browse
2. Select source and target languages:
   - **From:** English / Japanese / Chinese
   - **To:** English / Japanese / Chinese
3. Select translation options:
   - **Translate Text** - Extract and translate PDF text
   - **Translate Images (OCR)** - Detect and translate text in images
4. Click "Start Translation"
5. Preview the translated pages
6. Download your translated PDF

## Project Structure

```
pdf-translator-with-ocr/
├── app.py              # Flask API server
├── pdf_processor.py    # PDF extraction and rebuilding
├── translator.py       # Translation service (Google Translate)
├── ocr_processor.py    # Tesseract OCR integration
├── requirements.txt    # Python dependencies
└── static/
    ├── index.html      # Frontend UI
    ├── styles.css      # White & red theme
    └── app.js          # Frontend logic
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload PDF file with language params |
| `/api/translate/<task_id>` | GET | Start translation (SSE) |
| `/api/preview/<task_id>` | GET | Get page preview |
| `/api/download/<task_id>` | GET | Download translated PDF |

## Technologies

- **Backend**: Flask, PyMuPDF, pytesseract, deep-translator, OpenCV, Pillow
- **Frontend**: HTML, CSS, JavaScript
- **OCR**: Tesseract OCR
- **Translation**: Google Translate (via deep-translator)

## Troubleshooting

**"Tesseract not found" error:**
- Make sure Tesseract is installed and in your PATH
- On Windows, you may need to set `pytesseract.pytesseract.tesseract_cmd`

**"Poppler not found" error:**
- Install Poppler and ensure it's in your PATH
- On Windows, add the Poppler `bin` folder to PATH

**Chinese/Japanese OCR not working:**
- Ensure language packs are installed:
  - macOS: `brew install tesseract-lang`
  - Ubuntu: `apt install tesseract-ocr-jpn tesseract-ocr-chi-sim`

## License

MIT

import os
import sys
# Ensure src is in path if running from root
sys.path.append(os.path.join(os.getcwd(), 'src'))

from converter import PDFTranslator

def main():
    if len(sys.argv) < 3:
        print("Usage: python src/cli.py <pdf_path> <api_key>")
        return

    pdf_path = sys.argv[1]
    api_key = sys.argv[2]
    
    print(f"Translating {pdf_path}...")
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    translator = PDFTranslator(api_key)
    output_bytes = translator.translate_pdf(
        pdf_bytes,
        progress_callback=lambda msg, p: print(f"[{p:.1%}] {msg}")
    )
    
    with open("output_gemini.pdf", "wb") as f:
        f.write(output_bytes)
    print("Saved to output_gemini.pdf")

if __name__ == "__main__":
    main()

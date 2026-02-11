from pdf2image import convert_from_bytes
from weasyprint import HTML

def convert_pdf_to_images(pdf_bytes):
    """
    Convert PDF bytes to a list of PIL Images.
    """
    # 300 DPI for high quality text recognition
    return convert_from_bytes(pdf_bytes, dpi=150, fmt='jpeg')

def convert_html_to_pdf(html_content, output_path=None):
    """
    Convert HTML content to PDF bytes or save to file.
    """
    html = HTML(string=html_content)
    if output_path:
        html.write_pdf(output_path)
        return output_path
    else:
        return html.write_pdf()

import os
import io
import json
import math
import pandas as pd
import pdfplumber
from PIL import Image

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _sanitize(obj):
    """Replace NaN/Inf values with None so JSON serialization works."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def process_excel(filepath: str) -> dict:
    """Read Excel file and return structured data."""
    df = pd.read_excel(filepath)
    df = df.fillna("")
    return {
        "type": "excel",
        "columns": list(df.columns),
        "row_count": len(df),
        "preview": _sanitize(df.head(20).to_dict(orient="records")),
        "summary": _sanitize(df.describe(include="all").to_dict()),
    }


def process_pdf(filepath: str) -> dict:
    """Extract text and tables from PDF. Falls back to OCR for scanned PDFs."""
    text_pages = []
    tables = []
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages[:20]):  # Limit to 20 pages
            txt = page.extract_text()
            if txt:
                text_pages.append({"page": i + 1, "text": txt})
            found_tables = page.extract_tables()
            for t in found_tables:
                if t:
                    tables.append({"page": i + 1, "data": t})

    # If pdfplumber found no text, try OCR via PyMuPDF + AI vision
    if not text_pages and not tables:
        try:
            text_pages = _ocr_pdf_pages(filepath)
        except Exception:
            pass

    return {
        "type": "pdf",
        "pages": len(text_pages),
        "text": text_pages,
        "tables": tables,
    }


def _ocr_pdf_pages(filepath: str) -> list:
    """Convert scanned PDF pages to images and extract text via AI vision."""
    import fitz  # PyMuPDF
    import tempfile
    import base64
    import mimetypes
    from services.ai_service import _get_client, _get_deployment

    doc = fitz.open(filepath)
    text_pages = []

    for page_num in range(min(len(doc), 10)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=200)
        img_path = os.path.join(tempfile.gettempdir(), f"ocr_page_{page_num}.png")
        pix.save(img_path)

        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            response = _get_client().chat.completions.create(
                model=_get_deployment(),
                messages=[
                    {"role": "system", "content": "You are a document reader. Extract ALL text visible in this image. Return the raw text exactly as shown, preserving layout where possible. If it's an invoice or business document, include all numbers, names, dates, and line items."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Read and extract all text from this image:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}},
                    ]},
                ],
                max_completion_tokens=2000,
            )
            text = response.choices[0].message.content.strip()
            if text:
                text_pages.append({"page": page_num + 1, "text": text})
        except Exception:
            continue
        finally:
            try:
                os.remove(img_path)
            except OSError:
                pass

    doc.close()
    return text_pages


def process_image(filepath: str) -> dict:
    """Process image - extract text using AI vision or OCR fallback."""
    img = Image.open(filepath)
    result = {
        "type": "image",
        "size": img.size,
        "mode": img.mode,
        "format": img.format,
    }
    # Try pytesseract first (if installed)
    try:
        import pytesseract
        text = pytesseract.image_to_string(img)
        if text and len(text.strip()) > 20:
            result["extracted_text"] = text.strip()
            return result
    except Exception:
        pass

    # Fallback: Use Azure OpenAI vision to read the image
    try:
        import base64
        import mimetypes
        from services.ai_service import _get_client, _get_deployment

        mime, _ = mimetypes.guess_type(filepath)
        if not mime:
            mime = "image/jpeg"
        with open(filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        response = _get_client().chat.completions.create(
            model=_get_deployment(),
            messages=[
                {"role": "system", "content": "You are a document reader. Extract ALL text visible in this image. Return the raw text exactly as shown, preserving layout where possible. If it's an invoice or business document, include all numbers, names, dates, and line items."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Read and extract all text from this image:"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}},
                ]},
            ],
            max_completion_tokens=2000,
        )
        text = response.choices[0].message.content.strip()
        result["extracted_text"] = text
    except Exception as e:
        result["extracted_text"] = f"(Could not read image: {str(e)})"

    return result


def process_file(filepath: str) -> dict:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".xlsx", ".xls", ".csv"):
        if ext == ".csv":
            df = pd.read_csv(filepath)
            df = df.fillna("")
            return {
                "type": "csv",
                "columns": list(df.columns),
                "row_count": len(df),
                "preview": _sanitize(df.head(20).to_dict(orient="records")),
            }
        return process_excel(filepath)
    elif ext == ".pdf":
        return process_pdf(filepath)
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        return process_image(filepath)
    else:
        return {"type": "unknown", "message": f"Unsupported file type: {ext}"}

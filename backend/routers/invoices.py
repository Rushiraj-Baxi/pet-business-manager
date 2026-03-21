import os
import math
import re
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import List

from database import get_db
from models import Product, Sale, RawMaterial, Purchase, Expense
from services.file_processor import process_pdf, UPLOAD_DIR
from services.ai_service import parse_invoice_text, parse_invoice_image

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _normalize_name(name: str) -> str:
    """Normalize a product/material name for fuzzy matching.
    e.g. 'PET Preform 26gm', 'Pet preform 26 g', 'pet preform 26g' all → 'pet preform 26g'
    """
    s = name.strip().lower()
    s = re.sub(r'\s+', ' ', s)  # collapse whitespace
    # normalize weight units: gm, gms, gram, grams → g
    s = re.sub(r'(\d)\s*(gms|gm|grams|gram)\b', r'\1g', s)
    # normalize: 26 g → 26g (number + space + single-letter unit)
    s = re.sub(r'(\d)\s+([gG])\b', r'\1g', s)
    # normalize ml units
    s = re.sub(r'(\d)\s*(mls|ml)\b', r'\1ml', s)
    s = re.sub(r'(\d)\s+(ml)\b', r'\1ml', s)
    # normalize kg
    s = re.sub(r'(\d)\s*(kgs|kg)\b', r'\1kg', s)
    s = re.sub(r'(\d)\s+(kg)\b', r'\1kg', s)
    return s.strip()


def _find_product_fuzzy(db: Session, name: str):
    """Find an existing product by fuzzy name matching."""
    # 1. Exact match (case-insensitive)
    product = db.query(Product).filter(func.lower(Product.name) == name.strip().lower()).first()
    if product:
        return product
    # 2. Normalized match — compare against all products
    norm = _normalize_name(name)
    for p in db.query(Product).all():
        if _normalize_name(p.name) == norm:
            return p
    return None


def _find_material_fuzzy(db: Session, name: str):
    """Find an existing material by fuzzy name matching."""
    material = db.query(RawMaterial).filter(func.lower(RawMaterial.name) == name.strip().lower()).first()
    if material:
        return material
    norm = _normalize_name(name)
    for m in db.query(RawMaterial).all():
        if _normalize_name(m.name) == norm:
            return m
    return None


def _normalize_customer(name: str) -> str:
    """Normalize a customer name for consistency.
    e.g. 'M/S SURAKSHPET' = 'SURAKSHPET', '&' = 'and', consistent casing.
    """
    s = name.strip()
    if not s:
        return s
    # Remove M/S, M/s, m/s prefix
    s = re.sub(r'^[Mm]/[Ss]\s+', '', s)
    # Title case
    s = s.title()
    # Normalize & vs and
    s = re.sub(r'\s*&\s*', ' And ', s)
    s = re.sub(r'\bAnd\b', 'And', s)
    # Collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _safe_float(val, default=0.0) -> float:
    try:
        v = float(val)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0) -> int:
    try:
        v = float(val)
        return default if math.isnan(v) else int(v)
    except (ValueError, TypeError):
        return default


def _parse_date(val) -> datetime:
    if not val:
        return datetime.now(timezone.utc)
    try:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(str(val), fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        from pandas import to_datetime
        return to_datetime(val).to_pydatetime().replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _extract_text(filepath: str) -> str:
    """Extract text from a PDF file. Returns empty string for images (handled by vision)."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        result = process_pdf(filepath)
        text_parts = []
        for page in result.get("text", []):
            text_parts.append(page.get("text", ""))
        # Also include table data as text
        for table in result.get("tables", []):
            for row in table.get("data", []):
                text_parts.append(" | ".join(str(c or "") for c in row))
        return "\n".join(text_parts)
    return ""  # Images will be handled directly by AI vision


def _parse_scanned_pdf(filepath: str, invoice_type: str) -> dict:
    """Convert scanned PDF pages to images and parse with AI vision."""
    from pdf2image import convert_from_path
    import tempfile

    images = convert_from_path(filepath, dpi=200, first_page=1, last_page=5)
    all_parsed = None

    for page_num, img in enumerate(images):
        img_path = os.path.join(tempfile.gettempdir(), f"scan_page_{page_num}.png")
        img.save(img_path, "PNG")

        try:
            parsed = parse_invoice_image(img_path, invoice_type)
            if all_parsed is None:
                all_parsed = parsed
            else:
                # Merge items from subsequent pages
                all_parsed.setdefault("items", []).extend(parsed.get("items", []))
        except Exception:
            continue
        finally:
            try:
                os.remove(img_path)
            except OSError:
                pass

    if all_parsed is None:
        raise ValueError("Could not read scanned PDF — AI vision failed on all pages")
    return all_parsed


def _process_sales_invoice(parsed: dict, db: Session) -> dict:
    """Create sales records from parsed invoice data."""
    result = {"imported": 0, "skipped": 0, "details": [], "errors": []}
    party = _normalize_customer((parsed.get("party_name") or "").strip())
    inv_no = parsed.get("invoice_no") or ""
    inv_date = _parse_date(parsed.get("date"))

    for item in parsed.get("items", []):
        try:
            name = str(item.get("name") or "Unknown Product").strip()
            qty = _safe_int(item.get("quantity"))
            rate = _safe_float(item.get("rate"))
            taxable = _safe_float(item.get("taxable_amount"))
            gst_amt = _safe_float(item.get("gst_amount"))
            total = _safe_float(item.get("total"))

            if qty <= 0:
                result["skipped"] += 1
                continue

            # Best total: total > taxable+gst > rate*qty
            total = total or (taxable + gst_amt) or (rate * qty)
            rate = rate or (total / qty if qty > 0 else 0)
            if taxable <= 0:
                taxable = round(total / 1.18, 2) if total > 0 else 0

            # Determine product type
            name_lower = name.lower()
            ptype = "cap" if any(w in name_lower for w in ["cap", "lid", "cover"]) else "preform"

            # Find or create product (fuzzy match to prevent duplicates)
            product = _find_product_fuzzy(db, name)
            if not product:
                product = Product(
                    name=name, type=ptype, variant=name,
                    sell_price=rate, cost_price=0, stock=qty * 2,
                )
                db.add(product)
                db.flush()

            if product.stock < qty:
                product.stock += qty

            sale = Sale(
                product_id=product.id,
                quantity=qty,
                price_per_unit=rate,
                total_price=total,
                taxable_amount=taxable,
                customer=party,
                invoice_no=inv_no,
                date=inv_date,
            )
            product.stock -= qty
            db.add(sale)
            result["imported"] += 1
            result["details"].append(f"Inv {inv_no}: {name} x{qty} to {party} = ₹{total:,.0f}")
        except Exception as e:
            result["errors"].append(f"Item '{item.get('name', '?')}': {str(e)}")
            result["skipped"] += 1

    return result


def _process_purchase_invoice(parsed: dict, db: Session) -> dict:
    """Create purchase records and expenses from parsed invoice data."""
    result = {"imported": 0, "skipped": 0, "details": [], "errors": []}
    supplier = _normalize_customer((parsed.get("party_name") or "").strip())
    inv_no = parsed.get("invoice_no") or ""
    inv_date = _parse_date(parsed.get("date"))

    for item in parsed.get("items", []):
        try:
            name = str(item.get("name") or "Unknown Material").strip()
            qty = _safe_float(item.get("quantity"))
            unit = str(item.get("unit") or "kg").strip()
            rate = _safe_float(item.get("rate"))
            total = _safe_float(item.get("total"))
            taxable = _safe_float(item.get("taxable_amount"))
            gst_amt = _safe_float(item.get("gst_amount"))

            if qty <= 0 and total <= 0:
                result["skipped"] += 1
                continue

            total = total or (taxable + gst_amt) or (rate * qty)
            rate = rate or (total / qty if qty > 0 else 0)

            # Find or create raw material (fuzzy match to prevent duplicates)
            material = _find_material_fuzzy(db, name)
            if not material:
                material = RawMaterial(
                    name=name, unit=unit,
                    current_stock=0, price_per_unit=rate, reorder_level=0,
                )
                db.add(material)
                db.flush()

            # Create purchase record
            purchase = Purchase(
                raw_material_id=material.id,
                quantity=qty,
                price_per_unit=rate,
                total_price=total,
                supplier=supplier,
                date=inv_date,
            )
            material.current_stock += qty
            material.price_per_unit = rate  # Update latest price
            db.add(purchase)

            result["imported"] += 1
            result["details"].append(f"Inv {inv_no}: {name} {qty}{unit} from {supplier} = ₹{total:,.0f}")
        except Exception as e:
            result["errors"].append(f"Item '{item.get('name', '?')}': {str(e)}")
            result["skipped"] += 1

    return result


@router.post("/upload")
async def upload_invoices(
    files: List[UploadFile] = File(...),
    invoice_type: str = Form("sales"),
    db: Session = Depends(get_db),
):
    """Upload multiple invoice files (PDF/images), parse with AI, and import."""
    total_results = {
        "total_files": len(files),
        "processed": 0,
        "failed": 0,
        "total_imported": 0,
        "total_skipped": 0,
        "file_results": [],
    }

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            total_results["file_results"].append({
                "filename": file.filename,
                "status": "skipped",
                "reason": f"Unsupported file type: {ext}",
                "imported": 0,
            })
            total_results["failed"] += 1
            continue

        # Save file temporarily
        safe_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, safe_name)
        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        file_result = {
            "filename": file.filename,
            "status": "processing",
            "imported": 0,
            "details": [],
            "errors": [],
        }

        try:
            is_image = ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

            if is_image:
                # Use AI vision to read the image directly
                parsed = parse_invoice_image(filepath, invoice_type)
            else:
                # Extract text from PDF, then parse with AI
                text = _extract_text(filepath)
                if text and len(text.strip()) >= 20:
                    parsed = parse_invoice_text(text, invoice_type)
                else:
                    # Scanned PDF — convert pages to images and use AI vision
                    parsed = _parse_scanned_pdf(filepath, invoice_type)

            # Process based on type
            if invoice_type == "sales":
                import_result = _process_sales_invoice(parsed, db)
            else:
                import_result = _process_purchase_invoice(parsed, db)

            db.commit()

            file_result["status"] = "success" if import_result["imported"] > 0 else "no_data"
            file_result["imported"] = import_result["imported"]
            file_result["details"] = import_result["details"]
            file_result["errors"] = import_result["errors"]
            file_result["invoice_no"] = parsed.get("invoice_no")
            file_result["party"] = parsed.get("party_name")
            file_result["date"] = parsed.get("date")

            total_results["total_imported"] += import_result["imported"]
            total_results["total_skipped"] += import_result["skipped"]
            total_results["processed"] += 1

        except Exception as e:
            db.rollback()
            file_result["status"] = "failed"
            file_result["errors"].append(str(e))
            total_results["failed"] += 1

        total_results["file_results"].append(file_result)

        # Clean up temp file
        try:
            os.remove(filepath)
        except OSError:
            pass

    return total_results

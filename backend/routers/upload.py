import os
import re
import uuid
import math
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from models import Product, Sale, RawMaterial, Purchase, Production
from services.file_processor import process_file, UPLOAD_DIR
from services.ai_service import analyze_excel_structure

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _safe_float(val, default=0.0) -> float:
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0) -> int:
    try:
        v = float(val)
        if math.isnan(v):
            return default
        return int(v)
    except (ValueError, TypeError):
        return default


def _parse_date(val) -> datetime:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
    try:
        return pd.to_datetime(val).to_pydatetime().replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _get_cell(row, col_idx):
    """Safely get a cell value from a row list."""
    if col_idx is None:
        return None
    try:
        val = row[col_idx]
        if isinstance(val, float) and math.isnan(val):
            return None
        if val == "" or val == "-":
            return None
        return val
    except (IndexError, KeyError):
        return None


def _ai_import(filepath: str, db: Session) -> dict:
    """Use AI to parse any Excel format and import data."""
    results = {"imported": 0, "skipped": 0, "errors": [], "type": "unknown", "details": []}

    # Read all sheets
    xl = pd.ExcelFile(filepath)
    all_imported = 0
    all_details = []
    all_errors = []

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
        if len(df) < 2:
            continue

        # Convert to list of lists for AI analysis
        raw_rows = []
        for _, row in df.iterrows():
            raw_rows.append([None if (isinstance(v, float) and math.isnan(v)) else v for v in row.tolist()])

        # Ask AI to analyze the structure
        try:
            mapping = analyze_excel_structure(raw_rows)
        except Exception as e:
            all_errors.append(f"Sheet '{sheet_name}': AI analysis failed - {str(e)}")
            continue

        data_type = mapping.get("data_type", "unknown")
        data_start = mapping.get("data_start_index", 4)
        col_map = mapping.get("column_mapping", {})
        product_type = mapping.get("product_type_guess", "preform")
        results["type"] = data_type

        if data_type == "sales":
            last_good_date = None  # Track date for rows missing one
            for i in range(data_start, len(raw_rows)):
                row = raw_rows[i]

                # Skip empty/summary rows
                invoice = _get_cell(row, col_map.get("invoice_no"))
                date_val = _get_cell(row, col_map.get("date"))
                qty_kg = _get_cell(row, col_map.get("quantity_kg"))
                qty_nos = _get_cell(row, col_map.get("quantity_nos"))
                product_name_val = _get_cell(row, col_map.get("product_name"))

                # Need some quantity to be a valid row
                quantity = _safe_float(qty_kg) or _safe_float(qty_nos)
                if quantity <= 0:
                    results["skipped"] += 1
                    continue
                # Need at least a product name or invoice or date to be a data row
                if invoice is None and date_val is None and product_name_val is None:
                    results["skipped"] += 1
                    continue

                # Track last good date for rows that are missing one
                if date_val is not None:
                    last_good_date = date_val

                try:
                    customer_name = str(_get_cell(row, col_map.get("customer_name")) or "").strip()
                    product_name = str(_get_cell(row, col_map.get("product_name")) or "PET Preforms").strip()
                    rate = _safe_float(_get_cell(row, col_map.get("rate_per_unit")))
                    taxable = _safe_float(_get_cell(row, col_map.get("taxable_amount")))
                    gst_amount = _safe_float(_get_cell(row, col_map.get("gst_amount")))
                    invoice_value = _safe_float(_get_cell(row, col_map.get("invoice_value")))
                    date = _parse_date(date_val) if date_val else (_parse_date(last_good_date) if last_good_date else datetime.now(timezone.utc))

                    # Determine the best total price: invoice_value > taxable + gst > taxable > rate * qty
                    total_price = invoice_value or (taxable + gst_amount) or taxable or (rate * quantity)
                    price_per_unit = rate if rate > 0 else (total_price / quantity if quantity > 0 else 0)

                    # Determine product type from name
                    name_lower = product_name.lower()
                    if any(w in name_lower for w in ["cap", "lid", "cover"]):
                        ptype = "cap"
                    else:
                        ptype = "preform"

                    # Find or create product
                    product = db.query(Product).filter(Product.name == product_name).first()
                    if not product:
                        variant = product_name  # Use full name as variant
                        product = Product(
                            name=product_name, type=ptype, variant=variant,
                            sell_price=price_per_unit, cost_price=0,
                            stock=_safe_int(quantity) * 2,
                        )
                        db.add(product)
                        db.flush()

                    # Ensure stock
                    qty_int = _safe_int(quantity)
                    if product.stock < qty_int:
                        product.stock += qty_int

                    sale = Sale(
                        product_id=product.id,
                        quantity=qty_int,
                        price_per_unit=price_per_unit,
                        total_price=total_price,
                        taxable_amount=taxable if taxable > 0 else round(total_price / 1.18, 2),
                        customer=customer_name,
                        date=date,
                    )
                    product.stock -= qty_int
                    db.add(sale)
                    all_imported += 1
                    all_details.append(f"Inv {invoice}: {product_name} {_safe_int(quantity)}kg to {customer_name} = ₹{total_price:,.0f}")

                except Exception as e:
                    all_errors.append(f"Row {i + 1}: {str(e)}")
                    results["skipped"] += 1

        elif data_type == "products":
            # Handle product list imports
            for i in range(data_start, len(raw_rows)):
                row = raw_rows[i]
                name = str(_get_cell(row, col_map.get("product_name")) or "").strip()
                if not name:
                    results["skipped"] += 1
                    continue
                try:
                    product = db.query(Product).filter(Product.name == name).first()
                    if not product:
                        product = Product(name=name, type=product_type, variant=name, sell_price=0, cost_price=0, stock=0)
                        db.add(product)
                    all_imported += 1
                    all_details.append(f"Product: {name}")
                except Exception as e:
                    all_errors.append(f"Row {i + 1}: {str(e)}")

        db.commit()

    results["imported"] = all_imported
    results["details"] = all_details
    results["errors"] = all_errors
    return results


def _simple_import(filepath: str, ext: str, db: Session) -> dict:
    """Fallback: simple column-name-based import for well-formatted files."""
    df = pd.read_csv(filepath) if ext == ".csv" else pd.read_excel(filepath)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.fillna("")

    # If columns already make sense, do a direct import
    has_product = next((c for c in df.columns if any(k in c for k in ["product", "item", "name"])), None)
    has_qty = next((c for c in df.columns if any(k in c for k in ["qty", "quantity", "units"])), None)

    if has_product and has_qty:
        results = {"imported": 0, "skipped": 0, "errors": [], "type": "sales", "details": []}
        for _, row in df.iterrows():
            name = str(row.get(has_product, "")).strip()
            qty = _safe_int(row.get(has_qty, 0))
            if not name or qty <= 0:
                results["skipped"] += 1
                continue
            product = db.query(Product).filter(Product.name == name).first()
            if not product:
                product = Product(name=name, type="preform", variant=name, sell_price=0, cost_price=0, stock=qty * 2)
                db.add(product)
                db.flush()
            if product.stock < qty:
                product.stock += qty
            has_price = next((c for c in df.columns if any(k in c for k in ["price", "rate", "amount", "total"])), None)
            price = _safe_float(row.get(has_price, 0)) if has_price else 0
            per_unit = price / qty if qty > 0 and price > 0 else product.sell_price
            sale = Sale(product_id=product.id, quantity=qty, price_per_unit=per_unit, total_price=per_unit * qty, customer="", date=datetime.now(timezone.utc))
            product.stock -= qty
            db.add(sale)
            results["imported"] += 1
            results["details"].append(f"{name} x{qty}")
        db.commit()
        return results

    return None


@router.post("")
async def upload_file(file: UploadFile = File(...), auto_import: bool = Query(True), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    result = process_file(filepath)
    result["original_filename"] = file.filename

    if auto_import and ext in (".xlsx", ".xls", ".csv"):
        try:
            # First try AI-powered import for complex Excel formats
            import_result = _ai_import(filepath, db)
            if import_result["imported"] > 0:
                result["import"] = import_result
            else:
                # Fallback to simple column-name matching
                simple = _simple_import(filepath, ext, db)
                result["import"] = simple or import_result
        except Exception as e:
            # Final fallback
            try:
                simple = _simple_import(filepath, ext, db)
                result["import"] = simple or {"type": "error", "imported": 0, "errors": [str(e)]}
            except Exception as e2:
                result["import"] = {"type": "error", "imported": 0, "errors": [str(e), str(e2)]}

    return result

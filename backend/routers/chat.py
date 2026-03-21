from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import ChatHistory, Sale, Product, RawMaterial, Purchase, Production, Expense, CustomChart, BusinessEntry, Machine
from services.ai_service import chat_with_ai
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import json
import re

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


def _normalize_name(name: str) -> str:
    """Normalize a product/material name for fuzzy matching."""
    s = name.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(\d)\s*(gms|gm|grams|gram)\b', r'\1g', s)
    s = re.sub(r'(\d)\s+([gG])\b', r'\1g', s)
    s = re.sub(r'(\d)\s*(mls|ml)\b', r'\1ml', s)
    s = re.sub(r'(\d)\s+(ml)\b', r'\1ml', s)
    s = re.sub(r'(\d)\s*(kgs|kg)\b', r'\1kg', s)
    s = re.sub(r'(\d)\s+(kg)\b', r'\1kg', s)
    return s.strip()


def _find_product(db, name):
    """Find product by exact match or normalized fuzzy match."""
    p = db.query(Product).filter(func.lower(Product.name) == name.strip().lower()).first()
    if p:
        return p
    norm = _normalize_name(name)
    for prod in db.query(Product).all():
        if _normalize_name(prod.name) == norm:
            return prod
    return None


def _find_material(db, name):
    return db.query(RawMaterial).filter(func.lower(RawMaterial.name) == name.strip().lower()).first()


def _find_machine(db, name):
    return db.query(Machine).filter(func.lower(Machine.name) == name.strip().lower()).first()


def _execute_actions(actions: list[dict], db: Session) -> list[dict]:
    """Execute AI-generated actions against the database. Returns results list."""
    results = []
    for action in actions:
        atype = action.get("type", "")
        try:
            # ── PRODUCTS ────────────────────────────────────
            if atype == "add_product":
                p = Product(
                    name=action["name"],
                    type=action.get("product_type", "preform"),
                    variant=action.get("variant", ""),
                    sell_price=float(action.get("sell_price", 0)),
                    cost_price=float(action.get("cost_price", 0)),
                    stock=int(action.get("stock", 0)),
                )
                db.add(p)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Added product '{p.name}' (id={p.id})", "affected": ["products", "dashboard"]})

            elif atype == "update_product":
                product = _find_product(db, action["product_name"])
                if not product:
                    results.append({"ok": False, "action": atype, "detail": f"Product '{action['product_name']}' not found"})
                    continue
                if "name" in action and action["name"]:
                    product.name = action["name"]
                if "product_type" in action:
                    product.type = action["product_type"]
                if "variant" in action:
                    product.variant = action["variant"]
                if "sell_price" in action:
                    product.sell_price = float(action["sell_price"])
                if "cost_price" in action:
                    product.cost_price = float(action["cost_price"])
                if "stock" in action:
                    product.stock = int(action["stock"])
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated product '{product.name}'", "affected": ["products", "dashboard"]})

            elif atype == "delete_product":
                product = _find_product(db, action["product_name"])
                if not product:
                    results.append({"ok": False, "action": atype, "detail": f"Product '{action['product_name']}' not found"})
                    continue
                db.delete(product)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted product '{action['product_name']}'", "affected": ["products", "dashboard"]})

            elif atype == "update_stock":
                product = _find_product(db, action["product_name"])
                if not product:
                    results.append({"ok": False, "action": atype, "detail": f"Product '{action['product_name']}' not found"})
                    continue
                change = int(action.get("stock_change", 0))
                old = product.stock
                product.stock = max(0, product.stock + change)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Stock for '{product.name}': {old} → {product.stock}", "affected": ["products", "dashboard"]})

            elif atype == "update_price":
                product = _find_product(db, action["product_name"])
                if not product:
                    results.append({"ok": False, "action": atype, "detail": f"Product '{action['product_name']}' not found"})
                    continue
                if "sell_price" in action:
                    product.sell_price = float(action["sell_price"])
                if "cost_price" in action:
                    product.cost_price = float(action["cost_price"])
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated prices for '{product.name}'", "affected": ["products", "dashboard"]})

            # ── SALES ───────────────────────────────────────
            elif atype == "add_sale":
                product = _find_product(db, action["product_name"])
                if not product:
                    results.append({"ok": False, "action": atype, "detail": f"Product '{action['product_name']}' not found"})
                    continue
                qty = int(action["quantity"])
                ppu = float(action.get("price_per_unit", product.sell_price))
                d = datetime.fromisoformat(action["date"]) if action.get("date") else datetime.now(timezone.utc)
                s = Sale(
                    product_id=product.id,
                    quantity=qty,
                    price_per_unit=ppu,
                    total_price=qty * ppu,
                    taxable_amount=float(action.get("taxable_amount", 0)),
                    igst=float(action.get("igst", 0)),
                    sgst=float(action.get("sgst", 0)),
                    cgst=float(action.get("cgst", 0)),
                    customer=action.get("customer", ""),
                    invoice_no=action.get("invoice_no", ""),
                    date=d,
                )
                db.add(s)
                product.stock = max(0, product.stock - qty)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Recorded sale of {qty} x '{product.name}' for ₹{qty * ppu:,.2f}", "affected": ["sales", "dashboard", "analytics"]})

            elif atype == "delete_sale":
                sale = db.query(Sale).get(int(action["sale_id"]))
                if not sale:
                    results.append({"ok": False, "action": atype, "detail": f"Sale #{action['sale_id']} not found"})
                    continue
                prod = db.query(Product).filter(Product.id == sale.product_id).first()
                if prod:
                    prod.stock += sale.quantity
                db.delete(sale)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted sale #{action['sale_id']}", "affected": ["sales", "dashboard", "analytics"]})

            # ── RAW MATERIALS ───────────────────────────────
            elif atype == "add_material":
                m = RawMaterial(
                    name=action["name"],
                    unit=action.get("unit", "kg"),
                    material_category=action.get("material_category", "other"),
                    current_stock=float(action.get("current_stock", 0)),
                    price_per_unit=float(action.get("price_per_unit", 0)),
                    reorder_level=float(action.get("reorder_level", 0)),
                )
                db.add(m)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Added material '{m.name}' (id={m.id})", "affected": ["materials", "dashboard"]})

            elif atype == "update_material":
                mat = _find_material(db, action["material_name"])
                if not mat:
                    results.append({"ok": False, "action": atype, "detail": f"Material '{action['material_name']}' not found"})
                    continue
                if "name" in action and action["name"]:
                    mat.name = action["name"]
                if "current_stock" in action:
                    mat.current_stock = float(action["current_stock"])
                if "price_per_unit" in action:
                    mat.price_per_unit = float(action["price_per_unit"])
                if "reorder_level" in action:
                    mat.reorder_level = float(action["reorder_level"])
                if "unit" in action:
                    mat.unit = action["unit"]
                if "material_category" in action:
                    mat.material_category = action["material_category"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated material '{mat.name}'", "affected": ["materials", "dashboard"]})

            elif atype == "delete_material":
                mat = _find_material(db, action["material_name"])
                if not mat:
                    results.append({"ok": False, "action": atype, "detail": f"Material '{action['material_name']}' not found"})
                    continue
                db.delete(mat)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted material '{action['material_name']}'", "affected": ["materials", "dashboard"]})

            # ── PURCHASES ───────────────────────────────────
            elif atype == "add_purchase":
                mat = _find_material(db, action["material_name"])
                if not mat:
                    results.append({"ok": False, "action": atype, "detail": f"Material '{action['material_name']}' not found"})
                    continue
                qty = float(action["quantity"])
                ppu = float(action["price_per_unit"])
                pur = Purchase(
                    raw_material_id=mat.id,
                    quantity=qty,
                    price_per_unit=ppu,
                    total_price=qty * ppu,
                    supplier=action.get("supplier", ""),
                )
                db.add(pur)
                mat.current_stock += qty
                mat.price_per_unit = ppu
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Purchased {qty} {mat.unit} of '{mat.name}' for ₹{qty * ppu:,.2f}", "affected": ["materials", "dashboard"]})

            elif atype == "delete_purchase":
                pur = db.query(Purchase).get(int(action["purchase_id"]))
                if not pur:
                    results.append({"ok": False, "action": atype, "detail": f"Purchase #{action['purchase_id']} not found"})
                    continue
                mat = db.query(RawMaterial).filter(RawMaterial.id == pur.raw_material_id).first()
                if mat:
                    mat.current_stock = max(0, mat.current_stock - pur.quantity)
                db.delete(pur)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted purchase #{action['purchase_id']}", "affected": ["materials"]})

            # ── PRODUCTION ──────────────────────────────────
            elif atype == "add_production":
                product = _find_product(db, action["product_name"])
                mat = _find_material(db, action["material_name"])
                if not product:
                    results.append({"ok": False, "action": atype, "detail": f"Product '{action.get('product_name')}' not found"})
                    continue
                if not mat:
                    results.append({"ok": False, "action": atype, "detail": f"Material '{action.get('material_name')}' not found"})
                    continue
                qty = int(action["quantity_produced"])
                used = float(action["raw_material_used"])
                wastage = float(action.get("wastage", 0))
                prod_date = datetime.fromisoformat(action["date"]) if action.get("date") else datetime.now(timezone.utc)
                machine_id = None
                if action.get("machine_name"):
                    machine = _find_machine(db, action["machine_name"])
                    if machine:
                        machine_id = machine.id
                prod = Production(
                    product_id=product.id,
                    raw_material_id=mat.id,
                    quantity_produced=qty,
                    raw_material_used=used,
                    wastage=wastage,
                    machine_id=machine_id,
                    hours_run=float(action.get("hours_run", 0)),
                    date=prod_date,
                )
                db.add(prod)
                product.stock += qty
                mat.current_stock = max(0, mat.current_stock - used)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Produced {qty} x '{product.name}', used {used} {mat.unit} of '{mat.name}'", "affected": ["production", "products", "materials", "dashboard"]})

            elif atype == "delete_production":
                prod_rec = db.query(Production).get(int(action["production_id"]))
                if not prod_rec:
                    results.append({"ok": False, "action": atype, "detail": f"Production #{action['production_id']} not found"})
                    continue
                db.delete(prod_rec)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted production #{action['production_id']}", "affected": ["production", "dashboard"]})

            # ── EXPENSES ────────────────────────────────────
            elif atype == "add_expense":
                exp = Expense(
                    category=action["category"],
                    amount=float(action["amount"]),
                    description=action.get("description", ""),
                )
                db.add(exp)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Added expense: {exp.category} ₹{exp.amount:,.2f}", "affected": ["analytics", "dashboard"]})

            elif atype == "delete_expense":
                exp = db.query(Expense).get(int(action["expense_id"]))
                if not exp:
                    results.append({"ok": False, "action": atype, "detail": f"Expense #{action['expense_id']} not found"})
                    continue
                db.delete(exp)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted expense #{action['expense_id']}", "affected": ["analytics", "dashboard"]})

            # ── CHARTS ──────────────────────────────────────
            elif atype == "add_chart":
                c = CustomChart(
                    title=action["title"],
                    chart_type=action.get("chart_type", "bar"),
                    data_source=action.get("data_source", "sales_by_product"),
                    config=json.dumps(action.get("config", {})),
                    position=int(action.get("position", 0)),
                    page=action.get("page", "dashboard"),
                )
                db.add(c)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Created chart '{c.title}' (id={c.id})", "affected": ["charts", "dashboard"]})

            elif atype == "edit_chart":
                c = db.query(CustomChart).get(int(action["chart_id"]))
                if not c:
                    # Try by title
                    c = db.query(CustomChart).filter(func.lower(CustomChart.title) == action.get("chart_title", "").lower()).first()
                if not c:
                    results.append({"ok": False, "action": atype, "detail": f"Chart not found"})
                    continue
                if "title" in action:
                    c.title = action["title"]
                if "chart_type" in action:
                    c.chart_type = action["chart_type"]
                if "data_source" in action:
                    c.data_source = action["data_source"]
                if "config" in action:
                    c.config = json.dumps(action["config"])
                if "position" in action:
                    c.position = int(action["position"])
                if "page" in action:
                    c.page = action["page"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated chart '{c.title}'", "affected": ["charts", "dashboard"]})

            elif atype == "delete_chart":
                c = db.query(CustomChart).get(int(action.get("chart_id", 0)))
                if not c:
                    c = db.query(CustomChart).filter(func.lower(CustomChart.title) == action.get("chart_title", "").lower()).first()
                if not c:
                    results.append({"ok": False, "action": atype, "detail": "Chart not found"})
                    continue
                name = c.title
                db.delete(c)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted chart '{name}'", "affected": ["charts", "dashboard"]})

            # ── COSTS & LIABILITIES ─────────────────────────
            elif atype == "add_business_entry":
                be = BusinessEntry(
                    category=action.get("category", "cost"),
                    label=action["label"],
                    amount=float(action.get("amount", 0)),
                )
                db.add(be)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Added {be.category} '{be.label}' = \u20b9{be.amount:,.2f}", "affected": ["costs"]})

            elif atype == "update_business_entry":
                be = db.query(BusinessEntry).filter(func.lower(BusinessEntry.label) == action["label"].strip().lower()).first()
                if not be:
                    be = db.query(BusinessEntry).get(int(action.get("entry_id", 0)))
                if not be:
                    results.append({"ok": False, "action": atype, "detail": f"Entry '{action.get('label', action.get('entry_id'))}' not found"})
                    continue
                if "amount" in action:
                    be.amount = float(action["amount"])
                if "new_label" in action:
                    be.label = action["new_label"]
                if "category" in action:
                    be.category = action["category"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated {be.category} '{be.label}' = \u20b9{be.amount:,.2f}", "affected": ["costs"]})

            elif atype == "delete_business_entry":
                be = db.query(BusinessEntry).filter(func.lower(BusinessEntry.label) == action.get("label", "").strip().lower()).first()
                if not be:
                    be = db.query(BusinessEntry).get(int(action.get("entry_id", 0)))
                if not be:
                    results.append({"ok": False, "action": atype, "detail": f"Entry not found"})
                    continue
                lbl = be.label
                db.delete(be)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted entry '{lbl}'", "affected": ["costs"]})

            # ── MACHINES ────────────────────────────────────
            elif atype == "add_machine":
                m = Machine(
                    name=action["name"],
                    machine_type=action.get("machine_type", ""),
                    capacity_per_hour=int(action.get("capacity_per_hour", 0)),
                    status=action.get("status", "active"),
                )
                db.add(m)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Added machine '{m.name}' (id={m.id})", "affected": ["machines", "reports"]})

            elif atype == "update_machine":
                machine = _find_machine(db, action.get("machine_name", ""))
                if not machine:
                    results.append({"ok": False, "action": atype, "detail": f"Machine '{action.get('machine_name')}' not found"})
                    continue
                if "name" in action and action["name"]:
                    machine.name = action["name"]
                if "machine_type" in action:
                    machine.machine_type = action["machine_type"]
                if "capacity_per_hour" in action:
                    machine.capacity_per_hour = int(action["capacity_per_hour"])
                if "status" in action:
                    machine.status = action["status"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated machine '{machine.name}'", "affected": ["machines", "reports"]})

            elif atype == "delete_machine":
                machine = _find_machine(db, action.get("machine_name", ""))
                if not machine:
                    results.append({"ok": False, "action": atype, "detail": f"Machine '{action.get('machine_name')}' not found"})
                    continue
                name = machine.name
                db.delete(machine)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted machine '{name}'", "affected": ["machines", "reports"]})

            # ── MERGE PRODUCTS (consolidate duplicates) ─────
            elif atype == "merge_products":
                target_name = action.get("target_name", "").strip()
                source_names = action.get("source_names", [])
                if not target_name or not source_names:
                    results.append({"ok": False, "action": atype, "detail": "Need target_name and source_names"})
                    continue
                # Find or create the target product
                target = _find_product(db, target_name)
                merged_count = 0
                for src_name in source_names:
                    src = db.query(Product).filter(func.lower(Product.name) == src_name.strip().lower()).first()
                    if not src:
                        # Try normalized match
                        norm = _normalize_name(src_name)
                        for p in db.query(Product).all():
                            if _normalize_name(p.name) == norm and p.id != (target.id if target else -1):
                                src = p
                                break
                    if not src:
                        continue
                    if target and src.id == target.id:
                        continue
                    if not target:
                        # Use the first source as target and rename it
                        src.name = target_name
                        target = src
                        db.flush()
                        merged_count += 1
                        continue
                    # Reassign all sales from source to target
                    db.query(Sale).filter(Sale.product_id == src.id).update(
                        {Sale.product_id: target.id}, synchronize_session='fetch'
                    )
                    # Reassign all productions from source to target
                    db.query(Production).filter(Production.product_id == src.id).update(
                        {Production.product_id: target.id}, synchronize_session='fetch'
                    )
                    # Sum stock
                    target.stock += src.stock
                    # Delete the duplicate
                    db.delete(src)
                    db.flush()
                    merged_count += 1
                if target and target.name != target_name:
                    target.name = target_name
                    db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Merged {merged_count} product(s) into '{target_name}'", "affected": ["products", "sales", "dashboard", "analytics"]})

            # ── BULK UPDATE CUSTOMER NAME ───────────────────
            elif atype == "bulk_update_customer":
                old_name = action.get("old_name", "").strip()
                new_name = action.get("new_name", "").strip()
                if not old_name or not new_name:
                    results.append({"ok": False, "action": atype, "detail": "Need old_name and new_name"})
                    continue
                all_sales = db.query(Sale).all()
                matched = [s for s in all_sales if old_name.lower() in (s.customer or "").lower()]
                for s in matched:
                    s.customer = new_name
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated customer name from '{old_name}' to '{new_name}' on {len(matched)} sale(s)", "affected": ["sales", "dashboard", "analytics"]})

            # ── FIND AND UPDATE SALE (no ID needed) ─────────
            elif atype == "find_and_update_sale":
                query = db.query(Sale).join(Product)
                if "find_date" in action:
                    d = datetime.fromisoformat(action["find_date"]).date()
                    query = query.filter(func.date(Sale.date) == d)
                if "find_customer" in action:
                    query = query.filter(func.lower(Sale.customer).contains(action["find_customer"].strip().lower()))
                if "find_product" in action:
                    prod = _find_product(db, action["find_product"])
                    if prod:
                        query = query.filter(Sale.product_id == prod.id)
                if "find_invoice" in action:
                    query = query.filter(func.lower(Sale.invoice_no) == action["find_invoice"].strip().lower())
                matched = query.all()
                if not matched:
                    results.append({"ok": False, "action": atype, "detail": "No matching sales found"})
                    continue
                for sale in matched:
                    if "customer" in action:
                        sale.customer = action["customer"]
                    if "quantity" in action:
                        old_qty = sale.quantity
                        new_qty = int(action["quantity"])
                        prod = db.query(Product).get(sale.product_id)
                        if prod:
                            prod.stock += old_qty - new_qty
                        sale.quantity = new_qty
                        sale.total_price = new_qty * sale.price_per_unit
                    if "price_per_unit" in action:
                        sale.price_per_unit = float(action["price_per_unit"])
                        sale.total_price = sale.quantity * sale.price_per_unit
                    if "invoice_no" in action:
                        sale.invoice_no = action["invoice_no"]
                    if "date" in action:
                        sale.date = datetime.fromisoformat(action["date"])
                    if "taxable_amount" in action:
                        sale.taxable_amount = float(action["taxable_amount"])
                    if "igst" in action:
                        sale.igst = float(action["igst"])
                    if "sgst" in action:
                        sale.sgst = float(action["sgst"])
                    if "cgst" in action:
                        sale.cgst = float(action["cgst"])
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated {len(matched)} sale(s) matching criteria", "affected": ["sales", "dashboard", "analytics"]})

            # ── FIND AND DELETE SALE (no ID needed) ─────────
            elif atype == "find_and_delete_sale":
                query = db.query(Sale).join(Product)
                if "find_date" in action:
                    d = datetime.fromisoformat(action["find_date"]).date()
                    query = query.filter(func.date(Sale.date) == d)
                if "find_customer" in action:
                    query = query.filter(func.lower(Sale.customer).contains(action["find_customer"].strip().lower()))
                if "find_product" in action:
                    prod = _find_product(db, action["find_product"])
                    if prod:
                        query = query.filter(Sale.product_id == prod.id)
                if "find_invoice" in action:
                    query = query.filter(func.lower(Sale.invoice_no) == action["find_invoice"].strip().lower())
                matched = query.all()
                if not matched:
                    results.append({"ok": False, "action": atype, "detail": "No matching sales found"})
                    continue
                for sale in matched:
                    prod = db.query(Product).get(sale.product_id)
                    if prod:
                        prod.stock += sale.quantity
                    db.delete(sale)
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Deleted {len(matched)} sale(s) matching criteria", "affected": ["sales", "dashboard", "analytics"]})

            # ── FIND AND UPDATE PURCHASE (no ID needed) ─────
            elif atype == "find_and_update_purchase":
                query = db.query(Purchase).join(RawMaterial)
                if "find_date" in action:
                    d = datetime.fromisoformat(action["find_date"]).date()
                    query = query.filter(func.date(Purchase.date) == d)
                if "find_supplier" in action:
                    query = query.filter(func.lower(Purchase.supplier).contains(action["find_supplier"].strip().lower()))
                if "find_material" in action:
                    mat = _find_material(db, action["find_material"])
                    if mat:
                        query = query.filter(Purchase.raw_material_id == mat.id)
                matched = query.all()
                if not matched:
                    results.append({"ok": False, "action": atype, "detail": "No matching purchases found"})
                    continue
                for pur in matched:
                    if "quantity" in action:
                        mat = db.query(RawMaterial).get(pur.raw_material_id)
                        if mat:
                            mat.current_stock += float(action["quantity"]) - pur.quantity
                        pur.quantity = float(action["quantity"])
                        pur.total_price = pur.quantity * pur.price_per_unit
                    if "price_per_unit" in action:
                        pur.price_per_unit = float(action["price_per_unit"])
                        pur.total_price = pur.quantity * pur.price_per_unit
                    if "supplier" in action:
                        pur.supplier = action["supplier"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated {len(matched)} purchase(s) matching criteria", "affected": ["materials", "dashboard"]})

            # ── FIND AND UPDATE EXPENSE (no ID needed) ──────
            elif atype == "find_and_update_expense":
                query = db.query(Expense)
                if "find_date" in action:
                    d = datetime.fromisoformat(action["find_date"]).date()
                    query = query.filter(func.date(Expense.date) == d)
                if "find_category" in action:
                    query = query.filter(func.lower(Expense.category).contains(action["find_category"].strip().lower()))
                if "find_description" in action:
                    query = query.filter(func.lower(Expense.description).contains(action["find_description"].strip().lower()))
                matched = query.all()
                if not matched:
                    results.append({"ok": False, "action": atype, "detail": "No matching expenses found"})
                    continue
                for exp in matched:
                    if "category" in action:
                        exp.category = action["category"]
                    if "amount" in action:
                        exp.amount = float(action["amount"])
                    if "description" in action:
                        exp.description = action["description"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated {len(matched)} expense(s) matching criteria", "affected": ["analytics", "dashboard"]})

            # ── FIND AND UPDATE PRODUCTION (no ID needed) ───
            elif atype == "find_and_update_production":
                query = db.query(Production).join(Product)
                if "find_date" in action:
                    d = datetime.fromisoformat(action["find_date"]).date()
                    query = query.filter(func.date(Production.date) == d)
                if "find_product" in action:
                    prod = _find_product(db, action["find_product"])
                    if prod:
                        query = query.filter(Production.product_id == prod.id)
                matched = query.all()
                if not matched:
                    results.append({"ok": False, "action": atype, "detail": "No matching production records found"})
                    continue
                for rec in matched:
                    if "quantity_produced" in action:
                        rec.quantity_produced = int(action["quantity_produced"])
                    if "raw_material_used" in action:
                        rec.raw_material_used = float(action["raw_material_used"])
                    if "wastage" in action:
                        rec.wastage = float(action["wastage"])
                    if "hours_run" in action:
                        rec.hours_run = float(action["hours_run"])
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated {len(matched)} production record(s) matching criteria", "affected": ["production", "dashboard"]})

            # ── UPDATE SALE ─────────────────────────────────
            elif atype == "update_sale":
                sale = db.query(Sale).get(int(action["sale_id"]))
                if not sale:
                    results.append({"ok": False, "action": atype, "detail": f"Sale #{action['sale_id']} not found"})
                    continue
                if "product_name" in action:
                    prod = _find_product(db, action["product_name"])
                    if prod:
                        old_prod = db.query(Product).get(sale.product_id)
                        if old_prod:
                            old_prod.stock += sale.quantity
                        sale.product_id = prod.id
                        prod.stock = max(0, prod.stock - sale.quantity)
                if "quantity" in action:
                    old_qty = sale.quantity
                    new_qty = int(action["quantity"])
                    prod = db.query(Product).get(sale.product_id)
                    if prod:
                        prod.stock += old_qty - new_qty
                    sale.quantity = new_qty
                    sale.total_price = new_qty * sale.price_per_unit
                if "price_per_unit" in action:
                    sale.price_per_unit = float(action["price_per_unit"])
                    sale.total_price = sale.quantity * sale.price_per_unit
                if "customer" in action:
                    sale.customer = action["customer"]
                if "invoice_no" in action:
                    sale.invoice_no = action["invoice_no"]
                if "date" in action:
                    sale.date = datetime.fromisoformat(action["date"])
                if "taxable_amount" in action:
                    sale.taxable_amount = float(action["taxable_amount"])
                if "igst" in action:
                    sale.igst = float(action["igst"])
                if "sgst" in action:
                    sale.sgst = float(action["sgst"])
                if "cgst" in action:
                    sale.cgst = float(action["cgst"])
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated sale #{action['sale_id']}", "affected": ["sales", "dashboard", "analytics"]})

            # ── UPDATE PURCHASE ─────────────────────────────
            elif atype == "update_purchase":
                pur = db.query(Purchase).get(int(action["purchase_id"]))
                if not pur:
                    results.append({"ok": False, "action": atype, "detail": f"Purchase #{action['purchase_id']} not found"})
                    continue
                if "quantity" in action:
                    mat = db.query(RawMaterial).get(pur.raw_material_id)
                    if mat:
                        mat.current_stock += float(action["quantity"]) - pur.quantity
                    pur.quantity = float(action["quantity"])
                    pur.total_price = pur.quantity * pur.price_per_unit
                if "price_per_unit" in action:
                    pur.price_per_unit = float(action["price_per_unit"])
                    pur.total_price = pur.quantity * pur.price_per_unit
                if "supplier" in action:
                    pur.supplier = action["supplier"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated purchase #{action['purchase_id']}", "affected": ["materials", "dashboard"]})

            # ── UPDATE EXPENSE ──────────────────────────────
            elif atype == "update_expense":
                exp = db.query(Expense).get(int(action["expense_id"]))
                if not exp:
                    results.append({"ok": False, "action": atype, "detail": f"Expense #{action['expense_id']} not found"})
                    continue
                if "category" in action:
                    exp.category = action["category"]
                if "amount" in action:
                    exp.amount = float(action["amount"])
                if "description" in action:
                    exp.description = action["description"]
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated expense #{action['expense_id']}", "affected": ["analytics", "dashboard"]})

            # ── UPDATE PRODUCTION ───────────────────────────
            elif atype == "update_production":
                prod_rec = db.query(Production).get(int(action["production_id"]))
                if not prod_rec:
                    results.append({"ok": False, "action": atype, "detail": f"Production #{action['production_id']} not found"})
                    continue
                if "quantity_produced" in action:
                    prod_rec.quantity_produced = int(action["quantity_produced"])
                if "raw_material_used" in action:
                    prod_rec.raw_material_used = float(action["raw_material_used"])
                if "wastage" in action:
                    prod_rec.wastage = float(action["wastage"])
                if "hours_run" in action:
                    prod_rec.hours_run = float(action["hours_run"])
                db.flush()
                results.append({"ok": True, "action": atype, "detail": f"Updated production #{action['production_id']}", "affected": ["production", "dashboard"]})

            else:
                results.append({"ok": False, "action": atype, "detail": f"Unknown action type '{atype}'"})

        except Exception as e:
            results.append({"ok": False, "action": atype, "detail": str(e)})

    return results


def _parse_actions(reply: str) -> tuple[str, list[dict]]:
    """Extract action blocks from AI reply. Returns (cleaned_message, actions_list)."""
    pattern = r'<<<ACTIONS>>>(.*?)<<<END_ACTIONS>>>'
    match = re.search(pattern, reply, re.DOTALL)
    if not match:
        return reply, []
    actions_json = match.group(1).strip()
    cleaned = re.sub(pattern, '', reply, flags=re.DOTALL).strip()
    try:
        actions = json.loads(actions_json)
        if isinstance(actions, dict):
            actions = [actions]
        return cleaned, actions
    except json.JSONDecodeError:
        return cleaned, []


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    rows = db.query(ChatHistory).order_by(ChatHistory.timestamp.asc()).limit(100).all()
    return [{"role": r.role, "message": r.message, "timestamp": r.timestamp.isoformat()} for r in rows]


@router.post("")
def send_message(data: ChatRequest, db: Session = Depends(get_db)):
    # Build comprehensive context from DB
    since = datetime.now(timezone.utc) - timedelta(days=30)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()
    products = db.query(Product).all()
    materials = db.query(RawMaterial).all()
    productions = db.query(Production).filter(Production.date >= since).all()
    expenses = db.query(Expense).filter(Expense.date >= since).all()
    purchases = db.query(Purchase).filter(Purchase.date >= since).all()
    charts = db.query(CustomChart).all()
    business_entries = db.query(BusinessEntry).all()
    machines = db.query(Machine).all()

    # ALL sales with IDs (so AI can reference any record, not just recent)
    all_sales_for_ctx = db.query(Sale).join(Product).order_by(Sale.date.desc()).all()
    all_productions_for_ctx = db.query(Production).order_by(Production.date.desc()).all()
    all_expenses_for_ctx = db.query(Expense).order_by(Expense.date.desc()).all()
    all_purchases_for_ctx = db.query(Purchase).order_by(Purchase.date.desc()).all()

    total_revenue = sum(s.total_price for s in sales)
    total_units = sum(s.quantity for s in sales)
    cogs = sum(s.quantity * s.product.cost_price for s in sales)
    total_expenses = sum(e.amount for e in expenses)
    total_wastage = sum(p.wastage for p in productions)
    total_rm_used = sum(p.raw_material_used for p in productions)

    sales_by_product = {}
    for s in sales:
        key = s.product.name
        if key not in sales_by_product:
            sales_by_product[key] = {"name": key, "qty": 0, "revenue": 0}
        sales_by_product[key]["qty"] += s.quantity
        sales_by_product[key]["revenue"] += s.total_price

    sales_by_variant = {}
    for s in sales:
        key = f"{s.product.type} - {s.product.variant}"
        if key not in sales_by_variant:
            sales_by_variant[key] = {"type": s.product.type, "variant": s.product.variant, "qty": 0, "revenue": 0}
        sales_by_variant[key]["qty"] += s.quantity
        sales_by_variant[key]["revenue"] += s.total_price

    context = {
        "total_revenue": total_revenue,
        "total_units_sold": total_units,
        "gross_profit": total_revenue - cogs,
        "net_profit": total_revenue - cogs - total_expenses,
        "total_expenses": total_expenses,
        "wastage_pct": round(total_wastage / total_rm_used * 100, 2) if total_rm_used else 0,
        "products": [{"id": p.id, "name": p.name, "type": p.type, "variant": p.variant, "stock": p.stock, "sell_price": p.sell_price, "cost_price": p.cost_price} for p in products],
        "materials": [{"id": m.id, "name": m.name, "stock": m.current_stock, "unit": m.unit, "price": m.price_per_unit, "reorder_level": m.reorder_level} for m in materials],
        "sales_by_product": list(sales_by_product.values()),
        "sales_by_variant": list(sales_by_variant.values()),
        "all_sales": [{"id": s.id, "product": s.product.name, "qty": s.quantity, "total": s.total_price, "customer": s.customer, "date": s.date.strftime("%Y-%m-%d") if s.date else "", "invoice_no": s.invoice_no or ""} for s in all_sales_for_ctx],
        "all_productions": [{"id": p.id, "product": p.product.name, "material": p.raw_material.name, "qty": p.quantity_produced, "used": p.raw_material_used, "wastage": p.wastage, "date": p.date.strftime("%Y-%m-%d") if p.date else ""} for p in all_productions_for_ctx],
        "all_expenses": [{"id": e.id, "category": e.category, "amount": e.amount, "description": e.description, "date": e.date.strftime("%Y-%m-%d") if e.date else ""} for e in all_expenses_for_ctx],
        "all_purchases": [{"id": p.id, "material": p.raw_material.name, "qty": p.quantity, "price": p.price_per_unit, "total": p.total_price, "supplier": p.supplier, "date": p.date.strftime("%Y-%m-%d") if p.date else ""} for p in all_purchases_for_ctx],
        "custom_charts": [{"id": c.id, "title": c.title, "chart_type": c.chart_type, "data_source": c.data_source, "page": c.page} for c in charts],
        "business_entries": [{"id": e.id, "category": e.category, "label": e.label, "amount": e.amount} for e in business_entries],
        "machines": [{"id": m.id, "name": m.name, "type": m.machine_type, "capacity_per_hour": m.capacity_per_hour, "status": m.status} for m in machines],
    }

    # Get history
    history = db.query(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    hist_list = [{"role": h.role, "message": h.message} for h in reversed(history)]

    # Get AI response
    try:
        reply = chat_with_ai(data.message, context, hist_list)
    except Exception as e:
        reply = f"AI Error: {str(e)}. Please check your Azure OpenAI configuration."

    # Parse and execute any actions from the AI response
    cleaned_reply, actions = _parse_actions(reply)
    action_results = []
    affected_pages = set()
    if actions:
        action_results = _execute_actions(actions, db)
        summary_lines = []
        for r in action_results:
            icon = "✅" if r["ok"] else "❌"
            summary_lines.append(f"{icon} {r['detail']}")
            if r.get("affected"):
                affected_pages.update(r["affected"])
        if summary_lines:
            cleaned_reply += "\n\n---\n**Actions performed:**\n" + "\n".join(summary_lines)

    # Save to history
    db.add(ChatHistory(role="user", message=data.message))
    db.add(ChatHistory(role="assistant", message=cleaned_reply))
    db.commit()

    return {
        "role": "assistant",
        "message": cleaned_reply,
        "actions_performed": len(action_results) > 0,
        "action_results": action_results,
        "affected_pages": list(affected_pages),
    }


@router.post("/clear")
def clear_history(db: Session = Depends(get_db)):
    db.query(ChatHistory).delete()
    db.commit()
    return {"ok": True}

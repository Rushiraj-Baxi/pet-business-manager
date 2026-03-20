from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import get_db
from models import Sale, Product, RawMaterial, Production, Purchase, Expense

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(
    days: int = Query(30),
    product_type: Optional[str] = None,
    variant: Optional[str] = None,
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Sales query with filters
    sq = db.query(Sale).join(Product).filter(Sale.date >= since)
    if product_type:
        sq = sq.filter(Product.type == product_type)
    if variant:
        sq = sq.filter(Product.variant == variant)
    sales = sq.all()

    total_revenue = sum(s.total_price for s in sales)
    total_taxable = sum((s.taxable_amount or 0) for s in sales)
    total_units_sold = sum(s.quantity for s in sales)

    # Cost of goods sold
    cogs = sum(s.quantity * s.product.cost_price for s in sales)
    gross_profit = total_revenue - cogs

    # Wastage
    pq = db.query(Production).filter(Production.date >= since)
    prods = pq.all()
    total_wastage = sum(p.wastage for p in prods)
    total_rm_used = sum(p.raw_material_used for p in prods)
    wastage_pct = round(total_wastage / total_rm_used * 100, 2) if total_rm_used else 0

    # Expenses
    expenses = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.date >= since).scalar()
    net_profit = gross_profit - float(expenses) - total_wastage * _avg_material_cost(db)

    # Low stock alerts
    low_stock_products = db.query(Product).filter(Product.stock <= 10).all()
    low_stock_materials = db.query(RawMaterial).filter(
        RawMaterial.current_stock <= RawMaterial.reorder_level
    ).all()

    # Sales by product
    sales_by_product = {}
    for s in sales:
        key = s.product.name
        if key not in sales_by_product:
            sales_by_product[key] = {"name": key, "type": s.product.type, "variant": s.product.variant, "quantity": 0, "revenue": 0, "taxable": 0}
        sales_by_product[key]["quantity"] += s.quantity
        sales_by_product[key]["revenue"] += s.total_price
        sales_by_product[key]["taxable"] += (s.taxable_amount or 0)

    # Daily sales trend
    daily = {}
    for s in sales:
        day = s.date.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "quantity": 0, "revenue": 0, "taxable": 0}
        daily[day]["quantity"] += s.quantity
        daily[day]["revenue"] += s.total_price
        daily[day]["taxable"] += (s.taxable_amount or 0)

    # Sales by variant (for preform gram and cap color charts)
    by_variant = {}
    for s in sales:
        key = f"{s.product.type}:{s.product.variant}"
        if key not in by_variant:
            by_variant[key] = {"type": s.product.type, "variant": s.product.variant, "quantity": 0, "revenue": 0, "taxable": 0}
        by_variant[key]["quantity"] += s.quantity
        by_variant[key]["revenue"] += s.total_price
        by_variant[key]["taxable"] += (s.taxable_amount or 0)

    return {
        "total_revenue": round(total_revenue, 2),
        "total_taxable": round(total_taxable, 2),
        "total_tax": round(total_revenue - total_taxable, 2),
        "total_units_sold": total_units_sold,
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "wastage_pct": wastage_pct,
        "total_wastage_kg": round(total_wastage, 2),
        "expenses": round(float(expenses), 2),
        "low_stock_products": [{"id": p.id, "name": p.name, "stock": p.stock} for p in low_stock_products],
        "low_stock_materials": [{"id": m.id, "name": m.name, "stock": m.current_stock, "unit": m.unit} for m in low_stock_materials],
        "sales_by_product": list(sales_by_product.values()),
        "daily_trend": sorted(daily.values(), key=lambda x: x["date"]),
        "sales_by_variant": list(by_variant.values()),
    }


@router.get("/profit")
def profit_report(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()

    product_profits = {}
    for s in sales:
        key = s.product.name
        if key not in product_profits:
            product_profits[key] = {"name": key, "revenue": 0, "cost": 0, "profit": 0, "margin_pct": 0}
        product_profits[key]["revenue"] += s.total_price
        product_profits[key]["cost"] += s.quantity * s.product.cost_price

    for v in product_profits.values():
        v["profit"] = round(v["revenue"] - v["cost"], 2)
        v["margin_pct"] = round(v["profit"] / v["revenue"] * 100, 2) if v["revenue"] else 0
        v["revenue"] = round(v["revenue"], 2)
        v["cost"] = round(v["cost"], 2)

    return list(product_profits.values())


@router.get("/stock")
def stock_overview(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    materials = db.query(RawMaterial).all()
    return {
        "products": [{"id": p.id, "name": p.name, "type": p.type, "variant": p.variant, "stock": p.stock, "sell_price": p.sell_price, "cost_price": p.cost_price} for p in products],
        "materials": [{"id": m.id, "name": m.name, "unit": m.unit, "current_stock": m.current_stock, "price_per_unit": m.price_per_unit, "reorder_level": m.reorder_level} for m in materials],
    }


def _avg_material_cost(db: Session) -> float:
    materials = db.query(RawMaterial).all()
    if not materials:
        return 0
    return sum(m.price_per_unit for m in materials) / len(materials)


@router.get("/chart-data/{data_source}")
def chart_data(data_source: str, days: int = Query(30), db: Session = Depends(get_db)):
    """Return data for a custom chart by data_source type."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    if data_source == "sales_by_product":
        sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()
        buckets = {}
        for s in sales:
            key = s.product.name
            if key not in buckets:
                buckets[key] = {"name": key, "quantity": 0, "revenue": 0, "taxable": 0}
            buckets[key]["quantity"] += s.quantity
            buckets[key]["revenue"] += s.total_price
            buckets[key]["taxable"] += (s.taxable_amount or 0)
        return list(buckets.values())

    elif data_source == "sales_by_variant":
        sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()
        buckets = {}
        for s in sales:
            key = f"{s.product.type}:{s.product.variant}"
            if key not in buckets:
                buckets[key] = {"type": s.product.type, "variant": s.product.variant, "name": f"{s.product.variant} ({s.product.type})", "quantity": 0, "revenue": 0, "taxable": 0}
            buckets[key]["quantity"] += s.quantity
            buckets[key]["revenue"] += s.total_price
            buckets[key]["taxable"] += (s.taxable_amount or 0)
        return list(buckets.values())

    elif data_source == "daily_trend":
        sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()
        daily = {}
        for s in sales:
            day = s.date.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"date": day, "name": day, "quantity": 0, "revenue": 0, "taxable": 0}
            daily[day]["quantity"] += s.quantity
            daily[day]["revenue"] += s.total_price
            daily[day]["taxable"] += (s.taxable_amount or 0)
        return sorted(daily.values(), key=lambda x: x["date"])

    elif data_source == "profit_by_product":
        sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()
        buckets = {}
        for s in sales:
            key = s.product.name
            if key not in buckets:
                buckets[key] = {"name": key, "revenue": 0, "cost": 0, "profit": 0}
            buckets[key]["revenue"] += s.total_price
            buckets[key]["cost"] += s.quantity * s.product.cost_price
        for v in buckets.values():
            v["profit"] = round(v["revenue"] - v["cost"], 2)
            v["margin_pct"] = round(v["profit"] / v["revenue"] * 100, 2) if v["revenue"] else 0
        return list(buckets.values())

    elif data_source == "stock_overview":
        products = db.query(Product).all()
        return [{"name": p.name, "stock": p.stock, "type": p.type, "variant": p.variant} for p in products]

    elif data_source == "material_stock":
        materials = db.query(RawMaterial).all()
        return [{"name": m.name, "current_stock": m.current_stock, "unit": m.unit, "reorder_level": m.reorder_level} for m in materials]

    elif data_source == "expense_by_category":
        expenses = db.query(Expense).filter(Expense.date >= since).all()
        buckets = {}
        for e in expenses:
            if e.category not in buckets:
                buckets[e.category] = {"name": e.category, "category": e.category, "amount": 0}
            buckets[e.category]["amount"] += e.amount
        return list(buckets.values())

    elif data_source == "production_summary":
        prods = db.query(Production).filter(Production.date >= since).all()
        buckets = {}
        for p in prods:
            key = p.product.name
            if key not in buckets:
                buckets[key] = {"name": key, "product": key, "quantity_produced": 0, "raw_material_used": 0, "wastage": 0}
            buckets[key]["quantity_produced"] += p.quantity_produced
            buckets[key]["raw_material_used"] += p.raw_material_used
            buckets[key]["wastage"] += p.wastage
        return list(buckets.values())

    return []

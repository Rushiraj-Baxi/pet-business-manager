from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import get_db
from models import Sale, Product

router = APIRouter(prefix="/api/sales", tags=["sales"])


class SaleCreate(BaseModel):
    product_id: int
    quantity: int
    price_per_unit: float
    customer: str = ""
    date: Optional[str] = None


@router.get("")
def get_sales(
    product_type: Optional[str] = None,
    variant: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Sale).join(Product)
    if product_type:
        q = q.filter(Product.type == product_type)
    if variant:
        q = q.filter(Product.variant == variant)
    if start_date:
        q = q.filter(Sale.date >= datetime.fromisoformat(start_date))
    if end_date:
        q = q.filter(Sale.date <= datetime.fromisoformat(end_date))
    rows = q.order_by(Sale.date.desc()).all()
    result = []
    for s in rows:
        result.append({
            "id": s.id,
            "product_id": s.product_id,
            "product_name": s.product.name,
            "product_type": s.product.type,
            "product_variant": s.product.variant,
            "quantity": s.quantity,
            "price_per_unit": s.price_per_unit,
            "taxable_amount": s.taxable_amount or 0,
            "total_price": s.total_price,
            "customer": s.customer,
            "invoice_no": s.invoice_no or "",
            "date": s.date.isoformat() if s.date else None,
        })
    return result


@router.post("")
def create_sale(data: SaleCreate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == data.product_id).first()
    if not prod:
        raise HTTPException(404, "Product not found")
    if prod.stock < data.quantity:
        raise HTTPException(400, f"Insufficient stock. Available: {prod.stock}")
    d = datetime.fromisoformat(data.date) if data.date else datetime.now(timezone.utc)
    s = Sale(
        product_id=data.product_id,
        quantity=data.quantity,
        price_per_unit=data.price_per_unit,
        total_price=data.quantity * data.price_per_unit,
        customer=data.customer,
        date=d,
    )
    prod.stock -= data.quantity
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/trends")
def sales_trends(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    product_type: Optional[str] = None,
    variant: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(Sale).join(Product).filter(Sale.date >= since)
    if product_type:
        q = q.filter(Product.type == product_type)
    if variant:
        q = q.filter(Product.variant == variant)
    rows = q.order_by(Sale.date.asc()).all()

    buckets = {}
    for s in rows:
        if period == "daily":
            key = s.date.strftime("%Y-%m-%d")
        elif period == "weekly":
            key = s.date.strftime("%Y-W%W")
        else:
            key = s.date.strftime("%Y-%m")
        if key not in buckets:
            buckets[key] = {"period": key, "total_quantity": 0, "total_revenue": 0, "total_taxable": 0}
        buckets[key]["total_quantity"] += s.quantity
        buckets[key]["total_revenue"] += s.total_price
        buckets[key]["total_taxable"] += (s.taxable_amount or 0)

    return list(buckets.values())


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    s = db.query(Sale).filter(Sale.id == sale_id).first()
    if not s:
        raise HTTPException(404, "Sale not found")
    prod = db.query(Product).filter(Product.id == s.product_id).first()
    if prod:
        prod.stock += s.quantity
    db.delete(s)
    db.commit()
    return {"ok": True}

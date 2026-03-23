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
    invoice_no: Optional[str] = None
    taxable_amount: Optional[float] = None
    total_price: Optional[float] = None


class SaleUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    price_per_unit: Optional[float] = None
    customer: Optional[str] = None
    date: Optional[str] = None
    invoice_no: Optional[str] = None
    taxable_amount: Optional[float] = None
    total_price: Optional[float] = None


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
    total = data.total_price if data.total_price is not None else data.quantity * data.price_per_unit
    s = Sale(
        product_id=data.product_id,
        quantity=data.quantity,
        price_per_unit=data.price_per_unit,
        total_price=total,
        taxable_amount=data.taxable_amount,
        customer=data.customer,
        invoice_no=data.invoice_no or "",
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


@router.put("/{sale_id}")
def update_sale(sale_id: int, data: SaleUpdate, db: Session = Depends(get_db)):
    s = db.query(Sale).filter(Sale.id == sale_id).first()
    if not s:
        raise HTTPException(404, "Sale not found")
    if data.product_id is not None and data.product_id != s.product_id:
        old_prod = db.query(Product).filter(Product.id == s.product_id).first()
        new_prod = db.query(Product).filter(Product.id == data.product_id).first()
        if not new_prod:
            raise HTTPException(404, "New product not found")
        if old_prod:
            old_prod.stock += s.quantity
        s.product_id = data.product_id
    if data.quantity is not None:
        prod = db.query(Product).filter(Product.id == s.product_id).first()
        if prod:
            prod.stock += s.quantity - data.quantity
        s.quantity = data.quantity
        if data.total_price is None:
            s.total_price = data.quantity * s.price_per_unit
    if data.price_per_unit is not None:
        s.price_per_unit = data.price_per_unit
        if data.total_price is None:
            s.total_price = s.quantity * data.price_per_unit
    if data.total_price is not None:
        s.total_price = data.total_price
    if data.customer is not None:
        s.customer = data.customer
    if data.date is not None:
        s.date = datetime.fromisoformat(data.date)
    if data.invoice_no is not None:
        s.invoice_no = data.invoice_no
    if data.taxable_amount is not None:
        s.taxable_amount = data.taxable_amount
    db.commit()
    db.refresh(s)
    return {
        "id": s.id, "product_id": s.product_id,
        "product_name": s.product.name, "product_type": s.product.type,
        "product_variant": s.product.variant,
        "quantity": s.quantity, "price_per_unit": s.price_per_unit,
        "taxable_amount": s.taxable_amount or 0, "total_price": s.total_price,
        "customer": s.customer, "invoice_no": s.invoice_no or "",
        "date": s.date.isoformat() if s.date else None,
    }

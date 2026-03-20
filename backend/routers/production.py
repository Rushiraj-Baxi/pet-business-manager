from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models import Production, Product, RawMaterial, Machine

router = APIRouter(prefix="/api/production", tags=["production"])


class ProductionCreate(BaseModel):
    product_id: int
    raw_material_id: int
    quantity_produced: int
    raw_material_used: float
    wastage: float = 0
    machine_id: Optional[int] = None
    hours_run: float = 0
    date: Optional[str] = None


@router.get("")
def get_productions(db: Session = Depends(get_db)):
    rows = db.query(Production).order_by(Production.date.desc()).all()
    result = []
    for p in rows:
        result.append({
            "id": p.id,
            "product_id": p.product_id,
            "product_name": p.product.name,
            "product_variant": p.product.variant,
            "raw_material_id": p.raw_material_id,
            "raw_material_name": p.raw_material.name,
            "quantity_produced": p.quantity_produced,
            "raw_material_used": p.raw_material_used,
            "wastage": p.wastage,
            "wastage_pct": round(p.wastage / p.raw_material_used * 100, 2) if p.raw_material_used else 0,
            "machine_id": p.machine_id,
            "machine_name": p.machine.name if p.machine else None,
            "hours_run": p.hours_run or 0,
            "date": p.date.isoformat() if p.date else None,
        })
    return result


@router.post("")
def create_production(data: ProductionCreate, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == data.product_id).first()
    if not prod:
        raise HTTPException(404, "Product not found")
    mat = db.query(RawMaterial).filter(RawMaterial.id == data.raw_material_id).first()
    if not mat:
        raise HTTPException(404, "Raw material not found")
    if mat.current_stock < data.raw_material_used:
        raise HTTPException(400, f"Insufficient raw material. Available: {mat.current_stock} {mat.unit}")
    d = datetime.fromisoformat(data.date) if data.date else datetime.now(timezone.utc)
    p = Production(
        product_id=data.product_id,
        raw_material_id=data.raw_material_id,
        quantity_produced=data.quantity_produced,
        raw_material_used=data.raw_material_used,
        wastage=data.wastage,
        machine_id=data.machine_id,
        hours_run=data.hours_run,
        date=d,
    )
    mat.current_stock -= data.raw_material_used
    prod.stock += data.quantity_produced
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{prod_id}")
def delete_production(prod_id: int, db: Session = Depends(get_db)):
    p = db.query(Production).filter(Production.id == prod_id).first()
    if not p:
        raise HTTPException(404, "Production record not found")
    db.delete(p)
    db.commit()
    return {"ok": True}

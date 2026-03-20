from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import RawMaterial, Purchase

router = APIRouter(prefix="/api/materials", tags=["materials"])


class MaterialCreate(BaseModel):
    name: str
    unit: str = "kg"
    current_stock: float = 0
    price_per_unit: float = 0
    reorder_level: float = 0


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    current_stock: Optional[float] = None
    price_per_unit: Optional[float] = None
    reorder_level: Optional[float] = None


class PurchaseCreate(BaseModel):
    raw_material_id: int
    quantity: float
    price_per_unit: float
    supplier: str = ""
    date: Optional[str] = None


@router.get("")
def get_materials(db: Session = Depends(get_db)):
    return db.query(RawMaterial).order_by(RawMaterial.created_at.desc()).all()


@router.post("")
def create_material(data: MaterialCreate, db: Session = Depends(get_db)):
    m = RawMaterial(**data.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/{material_id}")
def update_material(material_id: int, data: MaterialUpdate, db: Session = Depends(get_db)):
    m = db.query(RawMaterial).filter(RawMaterial.id == material_id).first()
    if not m:
        raise HTTPException(404, "Material not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db)):
    m = db.query(RawMaterial).filter(RawMaterial.id == material_id).first()
    if not m:
        raise HTTPException(404, "Material not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


@router.get("/purchases")
def get_purchases(db: Session = Depends(get_db)):
    return db.query(Purchase).order_by(Purchase.date.desc()).all()


@router.post("/purchases")
def create_purchase(data: PurchaseCreate, db: Session = Depends(get_db)):
    mat = db.query(RawMaterial).filter(RawMaterial.id == data.raw_material_id).first()
    if not mat:
        raise HTTPException(404, "Material not found")
    from datetime import datetime, timezone
    d = datetime.fromisoformat(data.date) if data.date else datetime.now(timezone.utc)
    p = Purchase(
        raw_material_id=data.raw_material_id,
        quantity=data.quantity,
        price_per_unit=data.price_per_unit,
        total_price=data.quantity * data.price_per_unit,
        supplier=data.supplier,
        date=d,
    )
    mat.current_stock += data.quantity
    mat.price_per_unit = data.price_per_unit
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

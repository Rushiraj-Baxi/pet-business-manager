from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models import Product

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str
    type: str  # 'preform' or 'cap'
    variant: str  # gram weight or color
    sell_price: float = 0
    cost_price: float = 0
    stock: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sell_price: Optional[float] = None
    cost_price: Optional[float] = None
    stock: Optional[int] = None


@router.get("")
def get_products(type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Product)
    if type:
        q = q.filter(Product.type == type)
    return q.order_by(Product.created_at.desc()).all()


@router.post("")
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    p = Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{product_id}")
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    db.delete(p)
    db.commit()
    return {"ok": True}

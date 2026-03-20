from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models import BusinessEntry

router = APIRouter(prefix="/api/business-entries", tags=["business_entries"])

# Default entries to seed if table is empty
DEFAULT_COSTS = [
    "PET Resin Cost",
    "Electricity",
    "Labor",
    "Packaging",
    "Machine Maintenance",
]

DEFAULT_LIABILITIES = [
    "Supplier Payables",
    "Loans",
    "Other Liabilities",
]


def _ensure_defaults(db: Session):
    """Seed default entries if table is empty."""
    if db.query(BusinessEntry).count() > 0:
        return
    for label in DEFAULT_COSTS:
        db.add(BusinessEntry(category="cost", label=label, amount=0))
    for label in DEFAULT_LIABILITIES:
        db.add(BusinessEntry(category="liability", label=label, amount=0))
    db.commit()


class EntryUpdate(BaseModel):
    amount: float


class EntryCreate(BaseModel):
    category: str
    label: str
    amount: float = 0


@router.get("")
def get_entries(db: Session = Depends(get_db)):
    _ensure_defaults(db)
    rows = db.query(BusinessEntry).all()
    return [
        {"id": r.id, "category": r.category, "label": r.label, "amount": r.amount}
        for r in rows
    ]


@router.put("/{entry_id}")
def update_entry(entry_id: int, data: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.query(BusinessEntry).filter(BusinessEntry.id == entry_id).first()
    if not entry:
        return {"error": "Not found"}
    entry.amount = data.amount
    entry.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": entry.id, "category": entry.category, "label": entry.label, "amount": entry.amount}


@router.post("")
def create_entry(data: EntryCreate, db: Session = Depends(get_db)):
    entry = BusinessEntry(category=data.category, label=data.label, amount=data.amount)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "category": entry.category, "label": entry.label, "amount": entry.amount}


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(BusinessEntry).filter(BusinessEntry.id == entry_id).first()
    if not entry:
        return {"error": "Not found"}
    db.delete(entry)
    db.commit()
    return {"ok": True}

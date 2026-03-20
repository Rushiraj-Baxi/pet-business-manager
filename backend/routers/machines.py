from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models import Machine

router = APIRouter(prefix="/api/machines", tags=["machines"])


class MachineCreate(BaseModel):
    name: str
    machine_type: str = ""
    capacity_per_hour: int = 0
    status: str = "active"


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    machine_type: Optional[str] = None
    capacity_per_hour: Optional[int] = None
    status: Optional[str] = None


@router.get("")
def get_machines(db: Session = Depends(get_db)):
    machines = db.query(Machine).order_by(Machine.name).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "machine_type": m.machine_type,
            "capacity_per_hour": m.capacity_per_hour,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in machines
    ]


@router.post("")
def create_machine(data: MachineCreate, db: Session = Depends(get_db)):
    m = Machine(
        name=data.name,
        machine_type=data.machine_type,
        capacity_per_hour=data.capacity_per_hour,
        status=data.status,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "name": m.name, "machine_type": m.machine_type, "capacity_per_hour": m.capacity_per_hour, "status": m.status}


@router.put("/{machine_id}")
def update_machine(machine_id: int, data: MachineUpdate, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(404, "Machine not found")
    if data.name is not None:
        m.name = data.name
    if data.machine_type is not None:
        m.machine_type = data.machine_type
    if data.capacity_per_hour is not None:
        m.capacity_per_hour = data.capacity_per_hour
    if data.status is not None:
        m.status = data.status
    db.commit()
    db.refresh(m)
    return {"id": m.id, "name": m.name, "machine_type": m.machine_type, "capacity_per_hour": m.capacity_per_hour, "status": m.status}


@router.delete("/{machine_id}")
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(404, "Machine not found")
    db.delete(m)
    db.commit()
    return {"ok": True}

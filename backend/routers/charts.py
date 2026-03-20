from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import CustomChart
import json

router = APIRouter(prefix="/api/charts", tags=["charts"])


class ChartCreate(BaseModel):
    title: str
    chart_type: str = "bar"
    data_source: str = "sales_by_product"
    config: dict = {}
    position: int = 0
    page: str = "dashboard"


class ChartUpdate(BaseModel):
    title: Optional[str] = None
    chart_type: Optional[str] = None
    data_source: Optional[str] = None
    config: Optional[dict] = None
    position: Optional[int] = None
    page: Optional[str] = None


@router.get("")
def get_charts(page: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(CustomChart)
    if page:
        q = q.filter(CustomChart.page == page)
    rows = q.order_by(CustomChart.position.asc(), CustomChart.id.asc()).all()
    result = []
    for c in rows:
        result.append({
            "id": c.id,
            "title": c.title,
            "chart_type": c.chart_type,
            "data_source": c.data_source,
            "config": json.loads(c.config) if c.config else {},
            "position": c.position,
            "page": c.page,
        })
    return result


@router.post("")
def create_chart(data: ChartCreate, db: Session = Depends(get_db)):
    c = CustomChart(
        title=data.title,
        chart_type=data.chart_type,
        data_source=data.data_source,
        config=json.dumps(data.config),
        position=data.position,
        page=data.page,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "title": c.title, "chart_type": c.chart_type, "data_source": c.data_source, "config": data.config, "position": c.position, "page": c.page}


@router.put("/{chart_id}")
def update_chart(chart_id: int, data: ChartUpdate, db: Session = Depends(get_db)):
    c = db.query(CustomChart).filter(CustomChart.id == chart_id).first()
    if not c:
        raise HTTPException(404, "Chart not found")
    if data.title is not None:
        c.title = data.title
    if data.chart_type is not None:
        c.chart_type = data.chart_type
    if data.data_source is not None:
        c.data_source = data.data_source
    if data.config is not None:
        c.config = json.dumps(data.config)
    if data.position is not None:
        c.position = data.position
    if data.page is not None:
        c.page = data.page
    db.commit()
    db.refresh(c)
    return {"id": c.id, "title": c.title, "chart_type": c.chart_type, "data_source": c.data_source, "config": json.loads(c.config) if c.config else {}, "position": c.position, "page": c.page}


@router.delete("/{chart_id}")
def delete_chart(chart_id: int, db: Session = Depends(get_db)):
    c = db.query(CustomChart).filter(CustomChart.id == chart_id).first()
    if not c:
        raise HTTPException(404, "Chart not found")
    db.delete(c)
    db.commit()
    return {"ok": True}

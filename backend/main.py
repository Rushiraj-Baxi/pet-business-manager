import os
import sys

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import products, materials, sales, production, analytics, chat, upload, charts, business_entries, invoices, reports, machines

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PET Business Manager", version="1.0.0")

# CORS: allow local dev + production Azure Static Web App
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(materials.router)
app.include_router(sales.router)
app.include_router(production.router)
app.include_router(analytics.router)
app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(charts.router)
app.include_router(business_entries.router)
app.include_router(invoices.router)
app.include_router(reports.router)
app.include_router(machines.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "PET Business Manager is running"}


@app.post("/api/clear-all")
def clear_all_data():
    from sqlalchemy.orm import Session
    from database import SessionLocal
    from models import Sale, Production, Purchase, Expense, Product, RawMaterial, ChatHistory, CustomChart, BusinessEntry, Machine
    db: Session = SessionLocal()
    try:
        db.query(Sale).delete()
        db.query(Production).delete()
        db.query(Purchase).delete()
        db.query(Expense).delete()
        db.query(ChatHistory).delete()
        db.query(CustomChart).delete()
        db.query(BusinessEntry).delete()
        db.query(Product).delete()
        db.query(RawMaterial).delete()
        db.query(Machine).delete()
        db.commit()
    finally:
        db.close()
    return {"ok": True, "message": "All data cleared"}

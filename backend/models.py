from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'preform', 'cap', or 'bottle'
    variant = Column(String, nullable=False)  # gram weight, color, or size
    sell_price = Column(Float, default=0)
    cost_price = Column(Float, default=0)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sales = relationship("Sale", back_populates="product")
    productions = relationship("Production", back_populates="product")


class RawMaterial(Base):
    __tablename__ = "raw_materials"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    unit = Column(String, default="kg")
    material_category = Column(String, default="other")  # pet_resin, hdpe, masterbatch, packing, other
    current_stock = Column(Float, default=0)
    price_per_unit = Column(Float, default=0)
    reorder_level = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    purchases = relationship("Purchase", back_populates="raw_material")
    productions = relationship("Production", back_populates="raw_material")


class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    supplier = Column(String, default="")
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_material = relationship("RawMaterial", back_populates="purchases")


class Machine(Base):
    __tablename__ = "machines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    machine_type = Column(String, default="")  # injection_molding, blow_molding, capping, etc.
    capacity_per_hour = Column(Integer, default=0)
    status = Column(String, default="active")  # active, maintenance, inactive
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    productions = relationship("Production", back_populates="machine")


class Production(Base):
    __tablename__ = "production"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=True)
    quantity_produced = Column(Integer, nullable=False)
    raw_material_used = Column(Float, nullable=False)
    wastage = Column(Float, default=0)
    hours_run = Column(Float, default=0)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    product = relationship("Product", back_populates="productions")
    raw_material = relationship("RawMaterial", back_populates="productions")
    machine = relationship("Machine", back_populates="productions")


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    taxable_amount = Column(Float, default=0)
    igst = Column(Float, default=0)
    sgst = Column(Float, default=0)
    cgst = Column(Float, default=0)
    customer = Column(String, default="")
    invoice_no = Column(String, default="")
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    product = relationship("Product", back_populates="sales")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, default="")
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CustomChart(Base):
    __tablename__ = "custom_charts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    chart_type = Column(String, nullable=False)  # 'bar', 'line', 'area', 'pie', 'composed'
    data_source = Column(String, nullable=False)  # 'sales_by_product', 'sales_by_variant', 'daily_trend', 'profit_by_product', 'stock_overview', 'production_trend', 'expense_by_category', 'custom'
    config = Column(Text, default="{}")  # JSON config: filters, colors, data_keys, etc.
    position = Column(Integer, default=0)  # ordering
    page = Column(String, default="dashboard")  # which page to display on
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BusinessEntry(Base):
    __tablename__ = "business_entries"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)  # 'cost' or 'liability'
    label = Column(String, nullable=False)
    amount = Column(Float, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

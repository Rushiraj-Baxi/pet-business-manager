from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone, timedelta
from calendar import monthrange
from database import get_db
from models import Sale, Product, RawMaterial, Production, Purchase, Expense, Machine, BusinessEntry

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ─── 1. Monthly Sales Report ──────────────────────────────────────
@router.get("/monthly-sales")
def monthly_sales(
    months: int = Query(12, description="Number of months to look back"),
    db: Session = Depends(get_db),
):
    """Monthly sales by product + combined totals."""
    since = datetime.now(timezone.utc) - timedelta(days=months * 31)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()

    monthly = {}
    for s in sales:
        month_key = s.date.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"month": month_key, "products": {}, "total_qty": 0, "total_revenue": 0, "total_taxable": 0, "total_tax": 0}
        m = monthly[month_key]
        pname = s.product.name
        if pname not in m["products"]:
            m["products"][pname] = {"name": pname, "type": s.product.type, "variant": s.product.variant, "qty": 0, "revenue": 0, "taxable": 0}
        m["products"][pname]["qty"] += s.quantity
        m["products"][pname]["revenue"] += s.total_price
        m["products"][pname]["taxable"] += (s.taxable_amount or 0)
        m["total_qty"] += s.quantity
        m["total_revenue"] += s.total_price
        m["total_taxable"] += (s.taxable_amount or 0)
        m["total_tax"] += (s.total_price - (s.taxable_amount or 0))

    result = []
    for mk in sorted(monthly.keys()):
        entry = monthly[mk]
        entry["products"] = sorted(entry["products"].values(), key=lambda x: x["revenue"], reverse=True)
        entry["total_revenue"] = round(entry["total_revenue"], 2)
        entry["total_taxable"] = round(entry["total_taxable"], 2)
        entry["total_tax"] = round(entry["total_tax"], 2)
        result.append(entry)
    return result


# ─── 2. Top 5 Performers ──────────────────────────────────────────
@router.get("/top-performers")
def top_performers(
    days: int = Query(90),
    metric: str = Query("revenue", description="revenue or quantity"),
    db: Session = Depends(get_db),
):
    """Top 5 performers by product type (preform, cap, bottle)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()

    by_type = {}
    for s in sales:
        ptype = s.product.type
        pname = s.product.name
        if ptype not in by_type:
            by_type[ptype] = {}
        if pname not in by_type[ptype]:
            by_type[ptype][pname] = {"name": pname, "variant": s.product.variant, "quantity": 0, "revenue": 0}
        by_type[ptype][pname]["quantity"] += s.quantity
        by_type[ptype][pname]["revenue"] += s.total_price

    result = {}
    for ptype, products in by_type.items():
        sorted_prods = sorted(products.values(), key=lambda x: x[metric], reverse=True)[:5]
        for p in sorted_prods:
            p["revenue"] = round(p["revenue"], 2)
        result[ptype] = sorted_prods
    return result


# ─── 4. FY Comparison ─────────────────────────────────────────────
@router.get("/fy-comparison")
def fy_comparison(db: Session = Depends(get_db)):
    """Compare current financial year vs previous. Indian FY: Apr-Mar."""
    now = datetime.now(timezone.utc)
    if now.month >= 4:
        current_fy_start = datetime(now.year, 4, 1, tzinfo=timezone.utc)
        prev_fy_start = datetime(now.year - 1, 4, 1, tzinfo=timezone.utc)
        prev_fy_end = datetime(now.year, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:
        current_fy_start = datetime(now.year - 1, 4, 1, tzinfo=timezone.utc)
        prev_fy_start = datetime(now.year - 2, 4, 1, tzinfo=timezone.utc)
        prev_fy_end = datetime(now.year - 1, 3, 31, 23, 59, 59, tzinfo=timezone.utc)

    def _fy_metrics(start, end, db):
        sales = db.query(Sale).join(Product).filter(Sale.date >= start, Sale.date <= end).all()
        revenue = sum(s.total_price for s in sales)
        units = sum(s.quantity for s in sales)
        cogs = sum(s.quantity * s.product.cost_price for s in sales)
        expenses = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.date >= start, Expense.date <= end).scalar()
        purchases = db.query(func.coalesce(func.sum(Purchase.total_price), 0)).filter(Purchase.date >= start, Purchase.date <= end).scalar()
        productions = db.query(Production).filter(Production.date >= start, Production.date <= end).all()
        wastage = sum(p.wastage for p in productions)
        produced = sum(p.quantity_produced for p in productions)
        return {
            "revenue": round(float(revenue), 2),
            "units_sold": units,
            "cogs": round(float(cogs), 2),
            "gross_profit": round(float(revenue - cogs), 2),
            "expenses": round(float(expenses), 2),
            "net_profit": round(float(revenue - cogs - float(expenses)), 2),
            "purchases": round(float(purchases), 2),
            "units_produced": produced,
            "wastage_kg": round(float(wastage), 2),
        }

    current = _fy_metrics(current_fy_start, now, db)
    previous = _fy_metrics(prev_fy_start, prev_fy_end, db)

    # Growth percentages
    growth = {}
    for key in current:
        prev_val = previous.get(key, 0)
        curr_val = current.get(key, 0)
        if prev_val and prev_val != 0:
            growth[key] = round((curr_val - prev_val) / abs(prev_val) * 100, 1)
        else:
            growth[key] = 0

    fy_label_current = f"FY {current_fy_start.year}-{current_fy_start.year + 1}"
    fy_label_prev = f"FY {prev_fy_start.year}-{prev_fy_start.year + 1}"

    return {
        "current_fy": fy_label_current,
        "previous_fy": fy_label_prev,
        "current": current,
        "previous": previous,
        "growth": growth,
    }


# ─── 5. Product Type Breakdown ────────────────────────────────────
@router.get("/type-breakdown")
def type_breakdown(days: int = Query(30), db: Session = Depends(get_db)):
    """Units sold and revenue broken down by product type (preform/cap/bottle)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()

    breakdown = {}
    for s in sales:
        ptype = s.product.type
        if ptype not in breakdown:
            breakdown[ptype] = {"type": ptype, "units": 0, "revenue": 0, "taxable": 0, "orders": 0}
        breakdown[ptype]["units"] += s.quantity
        breakdown[ptype]["revenue"] += s.total_price
        breakdown[ptype]["taxable"] += (s.taxable_amount or 0)
        breakdown[ptype]["orders"] += 1

    for v in breakdown.values():
        v["revenue"] = round(v["revenue"], 2)
        v["taxable"] = round(v["taxable"], 2)
    return list(breakdown.values())


# ─── 6. Customer Analysis (Most Repeated Customer Per Product) ────
@router.get("/customer-analysis")
def customer_analysis(days: int = Query(365), db: Session = Depends(get_db)):
    """Most repeated customer per product + overall customer rankings."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since, Sale.customer != "").all()

    # Per product: top customer
    by_product = {}
    for s in sales:
        pname = s.product.name
        cust = s.customer.strip()
        if not cust:
            continue
        if pname not in by_product:
            by_product[pname] = {}
        if cust not in by_product[pname]:
            by_product[pname][cust] = {"customer": cust, "orders": 0, "total_qty": 0, "total_revenue": 0}
        by_product[pname][cust]["orders"] += 1
        by_product[pname][cust]["total_qty"] += s.quantity
        by_product[pname][cust]["total_revenue"] += s.total_price

    top_per_product = {}
    for pname, customers in by_product.items():
        sorted_custs = sorted(customers.values(), key=lambda x: x["orders"], reverse=True)
        top_per_product[pname] = sorted_custs[:5]
        for c in top_per_product[pname]:
            c["total_revenue"] = round(c["total_revenue"], 2)

    # Overall customer rankings
    overall = {}
    for s in sales:
        cust = s.customer.strip()
        if not cust:
            continue
        if cust not in overall:
            overall[cust] = {"customer": cust, "orders": 0, "total_qty": 0, "total_revenue": 0, "products": set()}
        overall[cust]["orders"] += 1
        overall[cust]["total_qty"] += s.quantity
        overall[cust]["total_revenue"] += s.total_price
        overall[cust]["products"].add(s.product.name)

    overall_list = sorted(overall.values(), key=lambda x: x["total_revenue"], reverse=True)
    for c in overall_list:
        c["products"] = list(c["products"])
        c["total_revenue"] = round(c["total_revenue"], 2)

    return {"top_per_product": top_per_product, "overall": overall_list[:20]}


# ─── 8 & 17. Purchase Breakdown by Material Category ─────────────
@router.get("/purchase-breakdown")
def purchase_breakdown(days: int = Query(365), db: Session = Depends(get_db)):
    """Purchase bifurcation by material category (PET resin, HDPE, etc.)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    purchases = db.query(Purchase).join(RawMaterial).filter(Purchase.date >= since).all()

    by_category = {}
    by_material = {}
    for p in purchases:
        cat = getattr(p.raw_material, 'material_category', 'other') or 'other'
        mname = p.raw_material.name

        if cat not in by_category:
            by_category[cat] = {"category": cat, "total_qty": 0, "total_cost": 0, "purchases": 0, "materials": set()}
        by_category[cat]["total_qty"] += p.quantity
        by_category[cat]["total_cost"] += p.total_price
        by_category[cat]["purchases"] += 1
        by_category[cat]["materials"].add(mname)

        if mname not in by_material:
            by_material[mname] = {"name": mname, "category": cat, "total_qty": 0, "total_cost": 0, "avg_rate": 0, "purchases": 0, "unit": p.raw_material.unit}
        by_material[mname]["total_qty"] += p.quantity
        by_material[mname]["total_cost"] += p.total_price
        by_material[mname]["purchases"] += 1

    for v in by_category.values():
        v["materials"] = list(v["materials"])
        v["total_cost"] = round(v["total_cost"], 2)
    for v in by_material.values():
        v["total_cost"] = round(v["total_cost"], 2)
        v["avg_rate"] = round(v["total_cost"] / v["total_qty"], 2) if v["total_qty"] else 0

    return {
        "by_category": sorted(by_category.values(), key=lambda x: x["total_cost"], reverse=True),
        "by_material": sorted(by_material.values(), key=lambda x: x["total_cost"], reverse=True),
    }


# ─── 10. Machine Efficiency ───────────────────────────────────────
@router.get("/machine-efficiency")
def machine_efficiency(days: int = Query(30), db: Session = Depends(get_db)):
    """Machine performance and efficiency metrics."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    machines = db.query(Machine).all()
    productions = db.query(Production).filter(Production.date >= since).all()

    machine_data = {}
    for m in machines:
        machine_data[m.id] = {
            "id": m.id,
            "name": m.name,
            "type": m.machine_type,
            "capacity_per_hour": m.capacity_per_hour,
            "status": m.status,
            "total_produced": 0,
            "total_hours": 0,
            "total_wastage": 0,
            "total_rm_used": 0,
            "runs": 0,
            "efficiency_pct": 0,
            "utilization_pct": 0,
        }

    unassigned = {"id": None, "name": "Unassigned", "total_produced": 0, "total_hours": 0, "total_wastage": 0, "total_rm_used": 0, "runs": 0}
    for p in productions:
        mid = p.machine_id
        if mid and mid in machine_data:
            d = machine_data[mid]
        else:
            d = unassigned
        d["total_produced"] += p.quantity_produced
        d["total_hours"] += (p.hours_run or 0)
        d["total_wastage"] += p.wastage
        d["total_rm_used"] += p.raw_material_used
        d["runs"] += 1

    result = []
    for d in machine_data.values():
        if d["total_hours"] > 0 and d["capacity_per_hour"] > 0:
            d["efficiency_pct"] = round(d["total_produced"] / (d["total_hours"] * d["capacity_per_hour"]) * 100, 1)
        if d["total_rm_used"] > 0:
            d["wastage_pct"] = round(d["total_wastage"] / d["total_rm_used"] * 100, 2)
        else:
            d["wastage_pct"] = 0
        available_hours = days * 16  # assuming 16 hrs/day capacity
        if d["total_hours"] > 0:
            d["utilization_pct"] = round(d["total_hours"] / available_hours * 100, 1)
        result.append(d)

    if unassigned["runs"] > 0:
        result.append(unassigned)

    return result


# ─── 11. Financial Statements (P&L, Balance Sheet, Ledger) ───────
@router.get("/financial-statements")
def financial_statements(
    fy: Optional[str] = Query(None, description="FY year e.g. 2025 for FY 2025-26"),
    db: Session = Depends(get_db),
):
    """Generate P&L, Balance Sheet summary, and Ledger."""
    now = datetime.now(timezone.utc)
    if fy:
        year = int(fy)
        start = datetime(year, 4, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:
        if now.month >= 4:
            start = datetime(now.year, 4, 1, tzinfo=timezone.utc)
            end = now
        else:
            start = datetime(now.year - 1, 4, 1, tzinfo=timezone.utc)
            end = now

    sales = db.query(Sale).join(Product).filter(Sale.date >= start, Sale.date <= end).all()
    purchases = db.query(Purchase).join(RawMaterial).filter(Purchase.date >= start, Purchase.date <= end).all()
    expenses = db.query(Expense).filter(Expense.date >= start, Expense.date <= end).all()
    productions = db.query(Production).filter(Production.date >= start, Production.date <= end).all()
    business_entries = db.query(BusinessEntry).all()

    # P&L
    revenue = sum(s.total_price for s in sales)
    taxable = sum((s.taxable_amount or 0) for s in sales)
    gst_collected = revenue - taxable
    cogs = sum(s.quantity * s.product.cost_price for s in sales)
    gross_profit = revenue - cogs

    expense_breakdown = {}
    for e in expenses:
        if e.category not in expense_breakdown:
            expense_breakdown[e.category] = 0
        expense_breakdown[e.category] += e.amount
    total_expenses = sum(expense_breakdown.values())

    net_profit = gross_profit - total_expenses

    pnl = {
        "revenue": round(revenue, 2),
        "taxable_revenue": round(taxable, 2),
        "gst_collected": round(gst_collected, 2),
        "cogs": round(cogs, 2),
        "gross_profit": round(gross_profit, 2),
        "expenses": {k: round(v, 2) for k, v in sorted(expense_breakdown.items(), key=lambda x: x[1], reverse=True)},
        "total_expenses": round(total_expenses, 2),
        "net_profit": round(net_profit, 2),
        "net_margin_pct": round(net_profit / revenue * 100, 2) if revenue else 0,
    }

    # Balance Sheet summary
    products = db.query(Product).all()
    materials = db.query(RawMaterial).all()
    inventory_value = sum(p.stock * p.cost_price for p in products) + sum(m.current_stock * m.price_per_unit for m in materials)
    total_purchases = sum(p.total_price for p in purchases)

    costs = [e for e in business_entries if e.category == "cost"]
    liabilities = [e for e in business_entries if e.category == "liability"]

    balance_sheet = {
        "assets": {
            "inventory_value": round(inventory_value, 2),
            "product_inventory": round(sum(p.stock * p.cost_price for p in products), 2),
            "material_inventory": round(sum(m.current_stock * m.price_per_unit for m in materials), 2),
            "total_assets": round(inventory_value, 2),
        },
        "liabilities": {
            "items": [{"label": l.label, "amount": l.amount} for l in liabilities],
            "total_liabilities": round(sum(l.amount for l in liabilities), 2),
        },
        "equity": {
            "retained_earnings": round(net_profit, 2),
        },
    }

    # Ledger (monthly summary)
    ledger = {}
    for s in sales:
        mk = s.date.strftime("%Y-%m")
        if mk not in ledger:
            ledger[mk] = {"month": mk, "sales": 0, "purchases": 0, "expenses": 0, "net": 0}
        ledger[mk]["sales"] += s.total_price
    for p in purchases:
        mk = p.date.strftime("%Y-%m")
        if mk not in ledger:
            ledger[mk] = {"month": mk, "sales": 0, "purchases": 0, "expenses": 0, "net": 0}
        ledger[mk]["purchases"] += p.total_price
    for e in expenses:
        mk = e.date.strftime("%Y-%m")
        if mk not in ledger:
            ledger[mk] = {"month": mk, "sales": 0, "purchases": 0, "expenses": 0, "net": 0}
        ledger[mk]["expenses"] += e.amount

    ledger_list = []
    for mk in sorted(ledger.keys()):
        entry = ledger[mk]
        entry["net"] = round(entry["sales"] - entry["purchases"] - entry["expenses"], 2)
        entry["sales"] = round(entry["sales"], 2)
        entry["purchases"] = round(entry["purchases"], 2)
        entry["expenses"] = round(entry["expenses"], 2)
        ledger_list.append(entry)

    return {"pnl": pnl, "balance_sheet": balance_sheet, "ledger": ledger_list}


# ─── 12. Rate Fluctuation Trends ──────────────────────────────────
@router.get("/rate-trends")
def rate_trends(days: int = Query(365), db: Session = Depends(get_db)):
    """Track purchase rate and sale price fluctuations over time."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Purchase rate trends (raw materials)
    purchases = db.query(Purchase).join(RawMaterial).filter(Purchase.date >= since).order_by(Purchase.date).all()
    purchase_trends = {}
    for p in purchases:
        mname = p.raw_material.name
        if mname not in purchase_trends:
            purchase_trends[mname] = []
        purchase_trends[mname].append({
            "date": p.date.strftime("%Y-%m-%d"),
            "rate": p.price_per_unit,
            "qty": p.quantity,
            "supplier": p.supplier,
        })

    # Sale price trends
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).order_by(Sale.date).all()
    sale_trends = {}
    for s in sales:
        pname = s.product.name
        if pname not in sale_trends:
            sale_trends[pname] = []
        sale_trends[pname].append({
            "date": s.date.strftime("%Y-%m-%d"),
            "rate": s.price_per_unit,
            "qty": s.quantity,
        })

    # Summary: current vs first price
    rate_summary = []
    for mname, entries in purchase_trends.items():
        if len(entries) >= 2:
            first = entries[0]["rate"]
            last = entries[-1]["rate"]
            change_pct = round((last - first) / first * 100, 1) if first else 0
            rate_summary.append({"name": mname, "type": "purchase", "first_rate": first, "latest_rate": last, "change_pct": change_pct, "data_points": len(entries)})
    for pname, entries in sale_trends.items():
        if len(entries) >= 2:
            first = entries[0]["rate"]
            last = entries[-1]["rate"]
            change_pct = round((last - first) / first * 100, 1) if first else 0
            rate_summary.append({"name": pname, "type": "sale", "first_rate": first, "latest_rate": last, "change_pct": change_pct, "data_points": len(entries)})

    return {"purchase_trends": purchase_trends, "sale_trends": sale_trends, "summary": rate_summary}


# ─── 13. Projected Revenue ────────────────────────────────────────
@router.get("/projections")
def revenue_projections(db: Session = Depends(get_db)):
    """Project next 3 months revenue based on trend analysis."""
    now = datetime.now(timezone.utc)

    # Get last 6 months of data
    monthly_rev = {}
    for i in range(6, 0, -1):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        mk = f"{y}-{m:02d}"
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        _, last_day = monthrange(y, m)
        end = datetime(y, m, last_day, 23, 59, 59, tzinfo=timezone.utc)
        sales = db.query(Sale).filter(Sale.date >= start, Sale.date <= end).all()
        monthly_rev[mk] = {
            "month": mk,
            "revenue": round(sum(s.total_price for s in sales), 2),
            "units": sum(s.quantity for s in sales),
        }

    # Simple linear projection
    months_data = sorted(monthly_rev.values(), key=lambda x: x["month"])
    revenues = [m["revenue"] for m in months_data]
    units = [m["units"] for m in months_data]

    def _project(values, n=3):
        if len(values) < 2:
            avg = values[0] if values else 0
            return [round(avg, 2)] * n
        # Weighted avg growth
        growths = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                growths.append((values[i] - values[i - 1]) / values[i - 1])
        if not growths:
            avg = sum(values) / len(values)
            return [round(avg, 2)] * n
        # Weight more recent months
        weighted = sum(g * (i + 1) for i, g in enumerate(growths)) / sum(range(1, len(growths) + 1))
        projected = []
        last = values[-1]
        for _ in range(n):
            last = max(0, last * (1 + weighted))
            projected.append(round(last, 2))
        return projected

    proj_rev = _project(revenues)
    proj_units = _project(units)

    projections = []
    for i in range(3):
        m = now.month + i + 1
        y = now.year
        if m > 12:
            m -= 12
            y += 1
        projections.append({
            "month": f"{y}-{m:02d}",
            "projected_revenue": proj_rev[i],
            "projected_units": int(proj_units[i]),
        })

    return {"historical": months_data, "projections": projections}


# ─── 14. Wastage Analysis ─────────────────────────────────────────
@router.get("/wastage-analysis")
def wastage_analysis(days: int = Query(90), db: Session = Depends(get_db)):
    """Detailed wastage breakdown by product and material."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    productions = db.query(Production).join(Product).filter(Production.date >= since).all()

    by_product = {}
    by_material = {}
    daily_wastage = {}

    for p in productions:
        pname = p.product.name
        mname = p.raw_material.name
        day = p.date.strftime("%Y-%m-%d")

        if pname not in by_product:
            by_product[pname] = {"name": pname, "type": p.product.type, "total_produced": 0, "total_rm_used": 0, "total_wastage": 0}
        by_product[pname]["total_produced"] += p.quantity_produced
        by_product[pname]["total_rm_used"] += p.raw_material_used
        by_product[pname]["total_wastage"] += p.wastage

        if mname not in by_material:
            by_material[mname] = {"name": mname, "total_used": 0, "total_wastage": 0}
        by_material[mname]["total_used"] += p.raw_material_used
        by_material[mname]["total_wastage"] += p.wastage

        if day not in daily_wastage:
            daily_wastage[day] = {"date": day, "wastage": 0, "rm_used": 0}
        daily_wastage[day]["wastage"] += p.wastage
        daily_wastage[day]["rm_used"] += p.raw_material_used

    for v in by_product.values():
        v["wastage_pct"] = round(v["total_wastage"] / v["total_rm_used"] * 100, 2) if v["total_rm_used"] else 0
        v["total_wastage"] = round(v["total_wastage"], 2)
    for v in by_material.values():
        v["wastage_pct"] = round(v["total_wastage"] / v["total_used"] * 100, 2) if v["total_used"] else 0
        v["total_wastage"] = round(v["total_wastage"], 2)

    daily = sorted(daily_wastage.values(), key=lambda x: x["date"])
    for d in daily:
        d["wastage_pct"] = round(d["wastage"] / d["rm_used"] * 100, 2) if d["rm_used"] else 0

    total_rm = sum(v["total_rm_used"] for v in by_product.values())
    total_waste = sum(v["total_wastage"] for v in by_product.values())

    return {
        "summary": {
            "total_rm_used": round(total_rm, 2),
            "total_wastage": round(total_waste, 2),
            "overall_pct": round(total_waste / total_rm * 100, 2) if total_rm else 0,
        },
        "by_product": sorted(by_product.values(), key=lambda x: x["total_wastage"], reverse=True),
        "by_material": sorted(by_material.values(), key=lambda x: x["total_wastage"], reverse=True),
        "daily_trend": daily,
    }


# ─── 15. Customer Loyalty / Duration Tracking ─────────────────────
@router.get("/customer-loyalty")
def customer_loyalty(db: Session = Depends(get_db)):
    """Customer list with first/last purchase, total orders, loyalty duration."""
    sales = db.query(Sale).join(Product).filter(Sale.customer != "").all()

    customers = {}
    for s in sales:
        cust = s.customer.strip()
        if not cust:
            continue
        if cust not in customers:
            customers[cust] = {
                "customer": cust,
                "first_order": s.date,
                "last_order": s.date,
                "total_orders": 0,
                "total_qty": 0,
                "total_revenue": 0,
                "products": set(),
            }
        c = customers[cust]
        if s.date < c["first_order"]:
            c["first_order"] = s.date
        if s.date > c["last_order"]:
            c["last_order"] = s.date
        c["total_orders"] += 1
        c["total_qty"] += s.quantity
        c["total_revenue"] += s.total_price
        c["products"].add(s.product.name)

    result = []
    for c in customers.values():
        duration_days = (c["last_order"] - c["first_order"]).days
        result.append({
            "customer": c["customer"],
            "first_order": c["first_order"].strftime("%Y-%m-%d"),
            "last_order": c["last_order"].strftime("%Y-%m-%d"),
            "duration_days": duration_days,
            "duration_label": f"{duration_days // 30}m {duration_days % 30}d" if duration_days > 30 else f"{duration_days}d",
            "total_orders": c["total_orders"],
            "total_qty": c["total_qty"],
            "total_revenue": round(c["total_revenue"], 2),
            "products": list(c["products"]),
            "avg_order_value": round(c["total_revenue"] / c["total_orders"], 2) if c["total_orders"] else 0,
        })

    return sorted(result, key=lambda x: x["total_revenue"], reverse=True)


# ─── 16. GST Report ───────────────────────────────────────────────
@router.get("/gst-report")
def gst_report(
    months: int = Query(12),
    db: Session = Depends(get_db),
):
    """GST breakdown — IGST, SGST, CGST by month and overall."""
    since = datetime.now(timezone.utc) - timedelta(days=months * 31)
    sales = db.query(Sale).join(Product).filter(Sale.date >= since).all()

    monthly = {}
    totals = {"taxable": 0, "igst": 0, "sgst": 0, "cgst": 0, "total_gst": 0, "total_invoice": 0}

    for s in sales:
        mk = s.date.strftime("%Y-%m")
        if mk not in monthly:
            monthly[mk] = {"month": mk, "taxable": 0, "igst": 0, "sgst": 0, "cgst": 0, "total_gst": 0, "invoice_value": 0, "sales_count": 0}
        m = monthly[mk]
        taxable = s.taxable_amount or 0
        igst = s.igst or 0
        sgst = s.sgst or 0
        cgst = s.cgst or 0
        explicit_gst = igst + sgst + cgst
        # If individual GST fields are 0 but we have taxable vs total, derive total GST
        if explicit_gst == 0 and taxable > 0 and s.total_price > taxable:
            gst = s.total_price - taxable
        else:
            gst = explicit_gst
        m["taxable"] += taxable
        m["igst"] += igst
        m["sgst"] += sgst
        m["cgst"] += cgst
        m["total_gst"] += gst
        m["invoice_value"] += s.total_price
        m["sales_count"] += 1

        totals["taxable"] += taxable
        totals["igst"] += igst
        totals["sgst"] += sgst
        totals["cgst"] += cgst
        totals["total_gst"] += gst
        totals["total_invoice"] += s.total_price

    for v in monthly.values():
        for k in ["taxable", "igst", "sgst", "cgst", "total_gst", "invoice_value"]:
            v[k] = round(v[k], 2)
    for k in totals:
        totals[k] = round(totals[k], 2)

    return {
        "monthly": sorted(monthly.values(), key=lambda x: x["month"]),
        "totals": totals,
    }


# ─── 3. AI Production Planning ────────────────────────────────────
@router.get("/production-planning")
def production_planning(db: Session = Depends(get_db)):
    """Smart production planning based on stock, demand, and capacity."""
    # Gather data for AI analysis
    products = db.query(Product).all()
    materials = db.query(RawMaterial).all()

    # Last 30 days sales for demand analysis
    since_30 = datetime.now(timezone.utc) - timedelta(days=30)
    since_90 = datetime.now(timezone.utc) - timedelta(days=90)
    sales_30 = db.query(Sale).join(Product).filter(Sale.date >= since_30).all()
    sales_90 = db.query(Sale).join(Product).filter(Sale.date >= since_90).all()
    productions_30 = db.query(Production).filter(Production.date >= since_30).all()

    # Demand per product (last 30 days)
    demand_30 = {}
    for s in sales_30:
        pname = s.product.name
        if pname not in demand_30:
            demand_30[pname] = 0
        demand_30[pname] += s.quantity

    # Demand per product (last 90 days, averaged monthly)
    demand_90 = {}
    for s in sales_90:
        pname = s.product.name
        if pname not in demand_90:
            demand_90[pname] = 0
        demand_90[pname] += s.quantity
    for k in demand_90:
        demand_90[k] = round(demand_90[k] / 3)

    # Production efficiency
    prod_efficiency = {}
    for p in productions_30:
        pname = p.product.name
        if pname not in prod_efficiency:
            prod_efficiency[pname] = {"produced": 0, "rm_used": 0, "wastage": 0}
        prod_efficiency[pname]["produced"] += p.quantity_produced
        prod_efficiency[pname]["rm_used"] += p.raw_material_used
        prod_efficiency[pname]["wastage"] += p.wastage

    suggestions = []
    for prod in products:
        d30 = demand_30.get(prod.name, 0)
        d90_avg = demand_90.get(prod.name, 0)
        stock = prod.stock
        days_of_stock = round(stock / (d30 / 30), 1) if d30 > 0 else 999

        eff = prod_efficiency.get(prod.name, {})
        wastage_pct = round(eff.get("wastage", 0) / eff.get("rm_used", 1) * 100, 1) if eff.get("rm_used") else 0

        # Suggest production if stock < 15 days of demand
        suggested_qty = 0
        urgency = "normal"
        if days_of_stock < 7:
            suggested_qty = max(d30, d90_avg) * 2  # produce 2 months worth
            urgency = "critical"
        elif days_of_stock < 15:
            suggested_qty = max(d30, d90_avg)
            urgency = "high"
        elif days_of_stock < 30:
            suggested_qty = round(d30 * 0.5)
            urgency = "medium"

        suggestions.append({
            "product": prod.name,
            "type": prod.type,
            "variant": prod.variant,
            "current_stock": stock,
            "demand_30d": d30,
            "demand_avg_monthly": d90_avg,
            "days_of_stock": days_of_stock if days_of_stock < 999 else None,
            "suggested_production": suggested_qty,
            "urgency": urgency,
            "wastage_pct": wastage_pct,
        })

    # Material availability check
    material_status = []
    for mat in materials:
        material_status.append({
            "name": mat.name,
            "category": getattr(mat, 'material_category', 'other') or 'other',
            "stock": mat.current_stock,
            "unit": mat.unit,
            "reorder_level": mat.reorder_level,
            "needs_reorder": mat.current_stock <= mat.reorder_level,
        })

    return {
        "suggestions": sorted(suggestions, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "normal": 3}[x["urgency"]]),
        "material_status": material_status,
    }

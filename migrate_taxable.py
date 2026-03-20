"""Add taxable_amount column and backfill existing sales data."""
import sqlite3
import os

db_path = "data/business.db"
print(f"DB exists: {os.path.exists(db_path)}, size: {os.path.getsize(db_path)} bytes")

conn = sqlite3.connect(db_path)
c = conn.cursor()

# List tables and counts
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
for t in tables:
    cnt = c.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
    print(f"  {t[0]}: {cnt} rows")

# Check sales columns
cols = [r[1] for r in c.execute("PRAGMA table_info(sales)").fetchall()]
print(f"\nSales columns: {cols}")

# Add column if needed
if "taxable_amount" not in cols:
    c.execute("ALTER TABLE sales ADD COLUMN taxable_amount REAL DEFAULT 0")
    conn.commit()
    print("Added taxable_amount column")

# Backfill all rows: taxable = total_price / 1.18 (18% GST)
c.execute("UPDATE sales SET taxable_amount = ROUND(total_price / 1.18, 2) WHERE taxable_amount IS NULL OR taxable_amount = 0")
updated = c.rowcount
conn.commit()
print(f"Backfilled {updated} rows")

# Verify
row = c.execute("SELECT COUNT(*), COALESCE(SUM(total_price),0), COALESCE(SUM(taxable_amount),0) FROM sales").fetchone()
print(f"\nSales count: {row[0]}")
if row[0] > 0:
    print(f"Total revenue (with tax): {row[1]:,.2f}")
    print(f"Total taxable (before tax): {row[2]:,.2f}")
    print(f"Total GST: {row[1] - row[2]:,.2f}")

conn.close()
print("\nDone!")

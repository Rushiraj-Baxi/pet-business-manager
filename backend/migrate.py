import sqlite3
import os

# On Azure, use /home/data/; locally, use ../data/
if os.environ.get("WEBSITE_SITE_NAME"):
    db_path = "/home/data/business.db"
else:
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "business.db")

conn = sqlite3.connect(db_path)
c = conn.cursor()

def get_cols(table):
    c.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in c.fetchall()]

sales_cols = get_cols("sales")
rm_cols = get_cols("raw_materials")
prod_cols = get_cols("production")

alters = []

if "igst" not in sales_cols:
    alters.append("ALTER TABLE sales ADD COLUMN igst REAL DEFAULT 0")
if "sgst" not in sales_cols:
    alters.append("ALTER TABLE sales ADD COLUMN sgst REAL DEFAULT 0")
if "cgst" not in sales_cols:
    alters.append("ALTER TABLE sales ADD COLUMN cgst REAL DEFAULT 0")
if "invoice_no" not in sales_cols:
    alters.append("ALTER TABLE sales ADD COLUMN invoice_no TEXT DEFAULT ''")
if "material_category" not in rm_cols:
    alters.append("ALTER TABLE raw_materials ADD COLUMN material_category TEXT DEFAULT 'other'")
if "machine_id" not in prod_cols:
    alters.append("ALTER TABLE production ADD COLUMN machine_id INTEGER")
if "hours_run" not in prod_cols:
    alters.append("ALTER TABLE production ADD COLUMN hours_run REAL DEFAULT 0")

# Create machines table if it doesn't exist
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='machines'")
if not c.fetchone():
    alters.append("""CREATE TABLE machines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        machine_type TEXT DEFAULT '',
        capacity_per_hour INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

for sql in alters:
    print(f"Running: {sql[:70]}...")
    c.execute(sql)

conn.commit()
conn.close()
print(f"Done! Applied {len(alters)} migrations.")

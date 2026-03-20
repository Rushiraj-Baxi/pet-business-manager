import pandas as pd
import sqlite3

# ---- EXCEL TOTALS ----
df = pd.read_excel(r'C:\Users\rushirajbaxi\Downloads\PP.xlsx', sheet_name='Pet Preforms', header=None)
data = df.iloc[5:667].copy()
data.columns = range(len(data.columns))
data[7] = pd.to_numeric(data[7], errors='coerce')
data[10] = pd.to_numeric(data[10], errors='coerce')
data[13] = pd.to_numeric(data[13], errors='coerce')
data[14] = pd.to_numeric(data[14], errors='coerce')
non_empty = data[data[0].notna() & (data[0] != '')]

print("=== EXCEL SUMMARY ===")
print("Total data rows:", len(non_empty))
print("Total Qty (kgs):", round(non_empty[7].sum(), 2))
print("Total Taxable Amount:", round(non_empty[10].sum(), 2))
print("Total GST Amount:", round(non_empty[13].sum(), 2))
print("Total Invoice Value:", round(non_empty[14].sum(), 2))

print("\n=== EXCEL BY PRODUCT ===")
for name, grp in non_empty.groupby(5):
    print("  %s: qty=%.2f kgs, taxable=%.2f, invoice_val=%.2f, rows=%d" % (
        name, grp[7].sum(), grp[10].sum(), grp[14].sum(), len(grp)))

bottom = df.iloc[674]
print("\n=== EXCEL BOTTOM ROW TOTALS ===")
print("  Qty (kgs):", bottom[7])
print("  Taxable Amount:", bottom[10])
print("  Invoice Value:", bottom[14])

# ---- DATABASE ----
conn = sqlite3.connect(r'data\business.db')

products = pd.read_sql('SELECT * FROM products', conn)
print("\n=== DATABASE PRODUCTS ===")
for _, p in products.iterrows():
    print("  id=%d name=%s type=%s variant=%s stock=%s sell=%.2f cost=%.2f" % (
        p['id'], p['name'], p['type'], p['variant'], p['stock'],
        p['sell_price'], p['cost_price']))

sales = pd.read_sql(
    'SELECT s.*, p.name as product_name FROM sales s JOIN products p ON s.product_id = p.id',
    conn)
print("\n=== DATABASE SALES SUMMARY ===")
print("Total sales records:", len(sales))
print("Total sales revenue:", round(sales['total_price'].sum(), 2))
print("Total sales quantity:", int(sales['quantity'].sum()))

print("\n=== DATABASE SALES BY PRODUCT ===")
for name, grp in sales.groupby('product_name'):
    print("  %s: qty=%d, revenue=%.2f, rows=%d" % (
        name, grp['quantity'].sum(), grp['total_price'].sum(), len(grp)))

# ---- COMPARISON ----
print("\n" + "="*60)
print("=== DISCREPANCY ANALYSIS ===")
print("="*60)

excel_rows = len(non_empty)
db_rows = len(sales)
excel_qty = non_empty[7].sum()
db_qty = sales['quantity'].sum()
excel_taxable = non_empty[10].sum()
db_revenue = sales['total_price'].sum()
excel_invoice = non_empty[14].sum()

print("\n  Metric              | Excel        | Database     | Difference")
print("  --------------------|--------------|--------------|------------")
print("  # Records           | %12d | %12d | %d" % (excel_rows, db_rows, excel_rows - db_rows))
print("  Qty (kgs)           | %12.2f | %12.0f | %.2f" % (excel_qty, db_qty, excel_qty - db_qty))
print("  Taxable/Revenue     | %12.2f | %12.2f | %.2f" % (excel_taxable, db_revenue, excel_taxable - db_revenue))
print("  Invoice Value       | %12.2f |     N/A      | (not in DB)" % excel_invoice)

# Check if DB used taxable or invoice value
print("\nNote: Excel has both Taxable Amount and Invoice Value (taxable + GST).")
print("  Excel Taxable Total:  %.2f" % excel_taxable)
print("  Excel Invoice Total:  %.2f" % excel_invoice)
print("  DB Revenue Total:     %.2f" % db_revenue)
diff_taxable = abs(excel_taxable - db_revenue)
diff_invoice = abs(excel_invoice - db_revenue)
if diff_taxable < diff_invoice:
    print("  -> DB revenue is closer to TAXABLE amount (diff=%.2f)" % diff_taxable)
else:
    print("  -> DB revenue is closer to INVOICE VALUE (diff=%.2f)" % diff_invoice)

conn.close()

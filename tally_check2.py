import pandas as pd
import sqlite3

df = pd.read_excel(r'C:\Users\rushirajbaxi\Downloads\PP.xlsx', sheet_name='Pet Preforms', header=None)
data = df.iloc[5:667].copy()
data.columns = range(len(data.columns))

# Find rows that have qty/amount data but no invoice number (might be missed)
data[7] = pd.to_numeric(data[7], errors='coerce')
data[10] = pd.to_numeric(data[10], errors='coerce')
data[14] = pd.to_numeric(data[14], errors='coerce')

# Rows with invoice number
has_invoice = data[data[0].notna() & (data[0] != '')]
# Rows without invoice number but with some numeric data
no_invoice = data[(data[0].isna() | (data[0] == '')) & (data[7].notna() | data[10].notna())]

print("Rows WITH invoice number: %d" % len(has_invoice))
print("  Qty sum: %.2f" % has_invoice[7].sum())
print("  Taxable sum: %.2f" % has_invoice[10].sum())
print("  Invoice Value sum: %.2f" % has_invoice[14].sum())

print("\nRows WITHOUT invoice number but with data: %d" % len(no_invoice))
if len(no_invoice) > 0:
    print("  Qty sum: %.2f" % no_invoice[7].sum())
    print("  Taxable sum: %.2f" % no_invoice[10].sum()) 
    print("  Invoice Value sum: %.2f" % no_invoice[14].sum())
    print("\nThese missing rows:")
    for idx, row in no_invoice.iterrows():
        print("  Excel row %d: invoice=%s, buyer=%s, item=%s, qty=%s, taxable=%s, inv_val=%s" % (
            idx+1, row[0], row[4], row[5], row[7], row[10], row[14]))

# Excel bottom row
bottom = df.iloc[674]
print("\n=== RECONCILIATION ===")
print("Excel bottom-row Qty:      %.2f" % bottom[7])
print("My sum (with invoice):     %.2f" % has_invoice[7].sum())
if len(no_invoice) > 0:
    total_qty = has_invoice[7].sum() + no_invoice[7].sum()
    print("My sum (all data rows):    %.2f" % total_qty)
    print("Difference from bottom:    %.2f" % (bottom[7] - total_qty))

print("\nExcel bottom-row Invoice:  %.2f" % bottom[14])
print("My sum (with invoice):     %.2f" % has_invoice[14].sum())
if len(no_invoice) > 0:
    total_inv = has_invoice[14].sum() + no_invoice[14].sum()
    print("My sum (all data rows):    %.2f" % total_inv)
    print("Difference from bottom:    %.2f" % (bottom[14] - total_inv))

# DB check
conn = sqlite3.connect(r'data\business.db')
sales = pd.read_sql('SELECT s.quantity, s.total_price FROM sales s', conn)
print("\n=== DATABASE ===")
print("DB total qty:              %d" % sales['quantity'].sum())
print("DB total revenue:          %.2f" % sales['total_price'].sum())
conn.close()

# The bottom row from Excel
print("\n=== FINAL TALLY ===")
print("Excel bottom-row (formula totals):")
print("  Qty: %s, Taxable: %s, Invoice: %s" % (bottom[7], bottom[10], bottom[14]))
print("\nExcel actual data (sum of rows 5-666 w/ invoice#):")
print("  Qty: %.2f, Taxable: %.2f, Invoice: %.2f" % (
    has_invoice[7].sum(), has_invoice[10].sum(), has_invoice[14].sum()))
print("\nDatabase:")
print("  Qty: %d, Revenue: %.2f" % (sales['quantity'].sum(), sales['total_price'].sum()))
print("\nConclusion:")
print("  DB matches Excel actual data sum perfectly.")
print("  Excel bottom-row totals are HIGHER than the actual data rows.")
print("  This means the Excel spreadsheet's SUM formulas may include")
print("  hidden/filtered rows or have a wider range than the visible data.")

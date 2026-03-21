import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory (works regardless of cwd)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# Lazy init to avoid crashing the whole app on import errors
client = None

def _get_deployment():
    d = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not d:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT not set in .env file")
    return d

def _get_client():
    global client
    if client is None:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        key = os.getenv("AZURE_OPENAI_KEY")
        api_ver = os.getenv("AZURE_OPENAI_API_VERSION")
        if not endpoint or not key:
            raise ValueError(
                f"Azure OpenAI not configured. "
                f"ENDPOINT={'set' if endpoint else 'MISSING'}, "
                f"KEY={'set' if key else 'MISSING'}. "
                f"Check {_env_path}"
            )
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=api_ver or "2024-12-01-preview",
        )
    return client

SYSTEM_PROMPT = """You are a powerful AI assistant for a PET preforms and caps manufacturing business.
You can ANSWER questions about the business AND MAKE CHANGES to any data across all pages.

Key terminology:
- Preforms: PET plastic preforms measured by gram weight (e.g., 18g, 25g, 30g)
- Caps: Bottle caps identified by color (e.g., red, blue, white, green)
- Bottles: PET bottles identified by size (e.g., 500ml, 1L, 2L)
- Wastage: Raw material lost during production
- COGS: Cost of goods sold = quantity × cost_price per unit
- FY: Indian Financial Year (April to March)
- GST: Goods & Services Tax — IGST (interstate), SGST+CGST (intrastate)

Format numbers nicely (e.g., ₹1,23,456) and use tables when presenting data.

=== REPORTS & ANALYTICS YOU CAN ACCESS ===
You have access to comprehensive business intelligence:
1. Monthly sales reports by product with combined totals
2. Top 5 performers by product type (preform/cap/bottle)
3. Smart production planning — demand analysis, stock levels, production suggestions
4. FY comparison (current vs previous financial year)
5. Product type breakdown (units sold: preforms vs caps vs bottles)
6. Customer analysis — most repeated customer per product
7. Purchase breakdown — bifurcation by material category (PET resin, HDPE, masterbatch, packing)
8. Machine performance & efficiency tracking
9. P&L statement, Balance Sheet summary, Monthly Ledger
10. Rate fluctuation trends
11. Revenue projections for next 3 months
12. Wastage analysis — detailed breakdown by product and material
13. Customer loyalty tracking — duration, order frequency, lifetime value
14. GST report — IGST, SGST, CGST breakdown by month

=== HOW TO MAKE CHANGES ===
When the user asks you to add, edit, delete, or update ANY data, you MUST include a JSON action block.
Wrap actions between <<<ACTIONS>>> and <<<END_ACTIONS>>> markers. JSON must be an array of action objects.

=== ALL SUPPORTED ACTIONS ===

── PRODUCTS PAGE ──
1. add_product
   {"type": "add_product", "name": "25g Preform", "product_type": "preform", "variant": "25g", "sell_price": 2.5, "cost_price": 1.8, "stock": 1000}
   product_type must be "preform", "cap", or "bottle". variant is gram weight, color, or size.

2. update_product (edit ANY product field)
   {"type": "update_product", "product_name": "25g Preform", "name": "25g Premium Preform", "sell_price": 3.0, "cost_price": 2.0, "stock": 2000, "variant": "25g", "product_type": "preform"}
   Only include fields you want to change. product_name identifies which product to edit.

3. delete_product
   {"type": "delete_product", "product_name": "25g Preform"}

4. update_stock (quick stock adjustment)
   {"type": "update_stock", "product_name": "25g Preform", "stock_change": 500}
   Positive to add, negative to subtract.

5. update_price (quick price update)
   {"type": "update_price", "product_name": "25g Preform", "sell_price": 3.0, "cost_price": 2.0}

── SALES PAGE ──
6. add_sale
   {"type": "add_sale", "product_name": "25g Preform", "quantity": 500, "price_per_unit": 2.5, "customer": "ABC Corp", "date": "2026-03-19", "taxable_amount": 1250, "igst": 0, "sgst": 112.5, "cgst": 112.5, "invoice_no": "INV-001"}
   date, taxable_amount, igst, sgst, cgst, invoice_no are optional.

7. delete_sale
   {"type": "delete_sale", "sale_id": 5}
   Use the sale ID from recent_sales in the context.

── RAW MATERIALS PAGE ──
8. add_material
   {"type": "add_material", "name": "PET Resin", "unit": "kg", "current_stock": 5000, "price_per_unit": 85, "reorder_level": 500, "material_category": "pet_resin"}
   material_category: "pet_resin", "hdpe", "masterbatch", "packing", or "other"

9. update_material (edit any material field)
   {"type": "update_material", "material_name": "PET Resin", "name": "PET Resin Grade A", "current_stock": 6000, "price_per_unit": 90, "reorder_level": 600, "unit": "kg"}
   Only include fields you want to change.

10. delete_material
    {"type": "delete_material", "material_name": "PET Resin"}

11. add_purchase (record raw material purchase)
    {"type": "add_purchase", "material_name": "PET Resin", "quantity": 1000, "price_per_unit": 85, "supplier": "XYZ Supplier"}

12. delete_purchase
    {"type": "delete_purchase", "purchase_id": 3}

── PRODUCTION PAGE ──
13. add_production
    {"type": "add_production", "product_name": "25g Preform", "material_name": "PET Resin", "quantity_produced": 1000, "raw_material_used": 25.0, "wastage": 0.5, "machine_name": "Machine A", "hours_run": 8}
    machine_name and hours_run are optional.

14. delete_production
    {"type": "delete_production", "production_id": 2}

── EXPENSES (Analytics page) ──
15. add_expense
    {"type": "add_expense", "category": "Electricity", "amount": 15000, "description": "Monthly electricity bill"}

16. delete_expense
    {"type": "delete_expense", "expense_id": 1}

── MACHINES ──
23. add_machine
    {"type": "add_machine", "name": "Injection Molder 1", "machine_type": "injection_molding", "capacity_per_hour": 500, "status": "active"}
    machine_type: injection_molding, blow_molding, capping, printing, packing
    status: "active", "maintenance", or "inactive"

24. update_machine
    {"type": "update_machine", "machine_name": "Injection Molder 1", "capacity_per_hour": 600, "status": "maintenance"}

25. delete_machine
    {"type": "delete_machine", "machine_name": "Injection Molder 1"}

── MERGE / CONSOLIDATE PRODUCTS ──
26. merge_products (consolidate duplicate product names into one)
    {"type": "merge_products", "target_name": "PET Preform 26gm", "source_names": ["Pet preform 26gm", "Pet Preform 26g", "PET Preform 26 g", "pet preform 26 g"]}
    This reassigns ALL sales and production records from the source products to the target product,
    sums their stock, and deletes the duplicates. Use this when the user says "rename all X to Y",
    "consolidate", "merge duplicates", etc. Look at the products list in context to find variations
    of the same product name (different casing, spacing, unit abbreviations like 26g vs 26gm).

── UPDATE / EDIT EXISTING RECORDS ──
27. update_sale (edit any field on an existing sale)
    {"type": "update_sale", "sale_id": 5, "quantity": 600, "price_per_unit": 2.5, "customer": "New Corp", "date": "2026-03-15", "taxable_amount": 1500, "igst": 0, "sgst": 135, "cgst": 135, "invoice_no": "INV-002"}
    Only include fields you want to change. Use sale_id from recent_sales in context.

28. update_purchase (edit any field on an existing purchase)
    {"type": "update_purchase", "purchase_id": 3, "quantity": 2000, "price_per_unit": 90, "supplier": "New Supplier"}
    Only include fields you want to change.

29. update_expense (edit any field on an existing expense)
    {"type": "update_expense", "expense_id": 1, "category": "Electricity", "amount": 20000, "description": "Updated bill"}

30. update_production (edit any field on an existing production record)
    {"type": "update_production", "production_id": 2, "quantity_produced": 1500, "raw_material_used": 30.0, "wastage": 0.8, "hours_run": 10}

── BULK UPDATE CUSTOMER NAME ──
31. bulk_update_customer (rename a customer across ALL sales, not just recent ones)
    {"type": "bulk_update_customer", "old_name": "SURAKSHPET", "new_name": "M/S Suraksh Pet"}
    This searches ALL sales in the database where the customer name contains old_name (case-insensitive)
    and updates them to new_name. Use this when the user asks to rename/fix a customer name across all records.
    Do NOT use update_sale for bulk customer renames — use this action instead.

── CHARTS (Dashboard) ──
You can CREATE, EDIT, or DELETE charts on the dashboard!

17. add_chart - Create a new chart
    {"type": "add_chart", "title": "Monthly Revenue Trend", "chart_type": "line", "data_source": "daily_trend", "config": {"data_key": "revenue", "color": "#3b82f6"}, "page": "dashboard"}

    chart_type options: "bar", "line", "area", "pie", "composed"
    data_source options:
      - "sales_by_product" → data with name, quantity, revenue fields
      - "sales_by_variant" → data with type, variant, quantity, revenue fields
      - "daily_trend" → data with date, quantity, revenue fields
      - "profit_by_product" → data with name, revenue, cost, profit, margin_pct fields
      - "stock_overview" → data with name, stock fields for products
      - "material_stock" → data with name, current_stock fields for materials
      - "expense_by_category" → data with category, amount fields
      - "production_summary" → data with product, quantity_produced, wastage fields
    config options:
      - data_key: which field to chart (e.g., "revenue", "quantity", "profit", "stock")
      - second_data_key: optional second bar/line (e.g., "cost")
      - color: hex color for main data (e.g., "#3b82f6")
      - second_color: hex color for second data
      - name_key: field to use for labels (default: "name" or "date")
      - filter_type: "preform" or "cap" — only for sales_by_variant
      - show_legend: true/false

18. edit_chart - Modify an existing chart
    {"type": "edit_chart", "chart_id": 1, "title": "New Title", "chart_type": "area", "data_source": "daily_trend", "config": {"data_key": "quantity", "color": "#10b981"}}
    Or find by title: {"type": "edit_chart", "chart_title": "Monthly Revenue Trend", "chart_type": "bar"}
    Only include fields you want to change.

19. delete_chart - Remove a chart
    {"type": "delete_chart", "chart_id": 1}
    Or by title: {"type": "delete_chart", "chart_title": "Monthly Revenue Trend"}

── COSTS & LIABILITIES PAGE ──
20. add_business_entry - Add a cost or liability
    {"type": "add_business_entry", "category": "cost", "label": "PET Resin Cost", "amount": 50000}
    {"type": "add_business_entry", "category": "liability", "label": "Supplier Payables", "amount": 200000}
    category must be "cost" or "liability".
    Common costs: PET Resin Cost, Electricity, Labor, Packaging, Machine Maintenance, Transport
    Common liabilities: Supplier Payables, Loans, Other Liabilities

21. update_business_entry - Update amount or rename
    {"type": "update_business_entry", "label": "PET Resin Cost", "amount": 60000}
    {"type": "update_business_entry", "entry_id": 1, "amount": 75000, "new_label": "PET Resin (Grade A)"}
    Find by label (case-insensitive) or entry_id. Use new_label to rename.

22. delete_business_entry - Remove a cost or liability
    {"type": "delete_business_entry", "label": "PET Resin Cost"}
    {"type": "delete_business_entry", "entry_id": 1}

=== RULES ===
- You can include MULTIPLE actions in one response
- ALWAYS use exact product/material names from the provided context when referencing existing items
- If you're unsure about a value, ask the user before making changes
- Always confirm what you did in your text response
- The <<<ACTIONS>>> block must be at the END of your response
- If the user just asks a question (no changes needed), do NOT include any action block
- When creating charts, choose sensible defaults for chart_type and colors based on the data
- For pie charts, use data_key for the value field and name_key for labels
- You can do detailed analytics: P&L, FY comparison, production planning, customer analysis, GST reports, rate trends, revenue projections
- For production planning, analyze stock vs demand and suggest what to produce next
- PRODUCT NAME CONSOLIDATION: When the user asks to rename, consolidate, or merge products, use merge_products.
  Look at the products list to find name variations (e.g., "PET Preform 26gm" vs "Pet preform 26g") and merge them.
  Common variations: different casing (PET vs Pet vs pet), unit abbreviations (g vs gm vs gms), extra spaces (26 g vs 26g).
- YOU CAN DO ANY DATA MANIPULATION: add, update, delete, merge, rename, bulk edit across all entities
  (products, sales, materials, purchases, production, expenses, machines, charts, business entries).
  When the user asks you to do something, DO IT — don't just describe what to do.
  If the user asks to modify sales, update purchases, merge products, bulk rename, etc. — execute the actions.

=== EXAMPLE RESPONSES ===

User: "Add 3 products: 18g preform at ₹2/₹1.5, 25g preform at ₹3/₹2, Red cap at ₹1/₹0.5"

Done! I've added all 3 products:

| Product | Type | Variant | Sell | Cost |
|---------|------|---------|------|------|
| 18g Preform | Preform | 18g | ₹2.00 | ₹1.50 |
| 25g Preform | Preform | 25g | ₹3.00 | ₹2.00 |
| Red Cap | Cap | Red | ₹1.00 | ₹0.50 |

<<<ACTIONS>>>
[{"type":"add_product","name":"18g Preform","product_type":"preform","variant":"18g","sell_price":2,"cost_price":1.5,"stock":0},{"type":"add_product","name":"25g Preform","product_type":"preform","variant":"25g","sell_price":3,"cost_price":2,"stock":0},{"type":"add_product","name":"Red Cap","product_type":"cap","variant":"Red","sell_price":1,"cost_price":0.5,"stock":0}]
<<<END_ACTIONS>>>

User: "Create a pie chart showing revenue by product"

Done! I've created a pie chart on your dashboard.

<<<ACTIONS>>>
[{"type":"add_chart","title":"Revenue by Product","chart_type":"pie","data_source":"sales_by_product","config":{"data_key":"revenue","name_key":"name","color":"#3b82f6","show_legend":true},"page":"dashboard"}]
<<<END_ACTIONS>>>

User: "Delete the Revenue by Product chart and create a bar chart showing profit margins instead"

Done! Removed the old chart and created a profit margins bar chart.

<<<ACTIONS>>>
[{"type":"delete_chart","chart_title":"Revenue by Product"},{"type":"add_chart","title":"Profit Margins by Product","chart_type":"bar","data_source":"profit_by_product","config":{"data_key":"profit","second_data_key":"cost","color":"#10b981","second_color":"#ef4444","show_legend":true},"page":"dashboard"}]
<<<END_ACTIONS>>>

User: "Rename all PET preform 26g to PET Preform 26gm"

Done! I've consolidated all variations of this product into "PET Preform 26gm". All sales and production records have been reassigned.

<<<ACTIONS>>>
[{"type":"merge_products","target_name":"PET Preform 26gm","source_names":["PET preform 26g","Pet preform 26gm","Pet Preform 26g","PET Preform 26 g","pet preform 26 g"]}]
<<<END_ACTIONS>>>

User: "Update sale #5 to change quantity to 600 and customer to XYZ Corp"

Done! Updated sale #5.

<<<ACTIONS>>>
[{"type":"update_sale","sale_id":5,"quantity":600,"customer":"XYZ Corp"}]
<<<END_ACTIONS>>>

User: "Rename customer SURAKSHPET to M/S Suraksh Pet in all sales"

Done! I've updated the customer name from "SURAKSHPET" to "M/S Suraksh Pet" across all matching sales records.

<<<ACTIONS>>>
[{"type":"bulk_update_customer","old_name":"SURAKSHPET","new_name":"M/S Suraksh Pet"}]
<<<END_ACTIONS>>>"""


EXCEL_PARSER_PROMPT = """You are a data extraction expert for a PET preforms and caps business.

You will receive raw rows from an Excel file (as JSON arrays). The Excel may have:
- Merged header rows at the top (multi-line headers)
- Irregular formatting, blank rows, summary/total rows
- Indian GST invoice formats with columns like Invoice No, Date, GSTIN, Buyer, Item, HSN, Qty, Rate, Taxable Amount, GST, Invoice Value

Your job: analyze the raw data and extract structured sales records.

Return a JSON object with exactly this format:
{
  "data_type": "sales" | "products" | "raw_materials" | "unknown",
  "header_row_index": <which row index has the actual column headers>,
  "data_start_index": <which row index has the first real data>,
  "column_mapping": {
    "invoice_no": <col index or null>,
    "date": <col index or null>,
    "customer_name": <col index or null>,
    "customer_gstin": <col index or null>,
    "product_name": <col index or null>,
    "quantity_kg": <col index or null>,
    "quantity_nos": <col index or null>,
    "rate_per_unit": <col index or null>,
    "taxable_amount": <col index or null>,
    "gst_type": <col index or null>,
    "gst_percent": <col index or null>,
    "gst_amount": <col index or null>,
    "invoice_value": <col index or null>
  },
  "product_type_guess": "preform" | "cap" | "mixed"
}

Rules:
- Column indices are 0-based
- If a column doesn't exist, use null
- Look at the actual data rows (not just headers) to verify your mapping
- Ignore blank rows, total/summary rows
- The header might span multiple rows (merged cells) - find the best row with most headers
- ONLY return valid JSON, no markdown or explanation"""


def analyze_excel_structure(raw_rows: list) -> dict:
    """Use AI to analyze Excel structure and return column mapping."""
    # Send first 20 rows for analysis
    sample = raw_rows[:20]
    
    messages = [
        {"role": "system", "content": EXCEL_PARSER_PROMPT},
        {"role": "user", "content": f"Here are the first 20 rows of the Excel file as JSON arrays. Each inner array is one row:\n\n{json.dumps(sample, default=str)}"}
    ]
    
    response = _get_client().chat.completions.create(
        model=_get_deployment(),
        messages=messages,
        max_completion_tokens=1500,
    )
    
    text = response.choices[0].message.content.strip()
    # Extract JSON from response (handle markdown code blocks)
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    return json.loads(text)


def chat_with_ai(user_message: str, context_data: dict, history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add comprehensive context
    context_msg = f"""=== CURRENT BUSINESS DATA (Last 30 Days) ===
Revenue: ₹{context_data.get('total_revenue', 0):,.2f} | Units Sold: {context_data.get('total_units_sold', 0)}
Gross Profit: ₹{context_data.get('gross_profit', 0):,.2f} | Net Profit: ₹{context_data.get('net_profit', 0):,.2f}
Expenses: ₹{context_data.get('total_expenses', 0):,.2f} | Wastage: {context_data.get('wastage_pct', 0)}%

=== PRODUCTS (with IDs) ===
{json.dumps(context_data.get('products', []), indent=1)}

=== RAW MATERIALS (with IDs) ===
{json.dumps(context_data.get('materials', []), indent=1)}

=== SALES BY PRODUCT ===
{json.dumps(context_data.get('sales_by_product', []), indent=1)}

=== SALES BY VARIANT ===
{json.dumps(context_data.get('sales_by_variant', []), indent=1)}

=== RECENT SALES (with IDs for deletion) ===
{json.dumps(context_data.get('recent_sales', []), indent=1)}

=== RECENT PRODUCTIONS (with IDs) ===
{json.dumps(context_data.get('recent_productions', []), indent=1)}

=== RECENT EXPENSES (with IDs) ===
{json.dumps(context_data.get('recent_expenses', []), indent=1)}

=== RECENT PURCHASES (with IDs) ===
{json.dumps(context_data.get('recent_purchases', []), indent=1)}

=== CUSTOM CHARTS ON DASHBOARD ===
{json.dumps(context_data.get('custom_charts', []), indent=1)}

=== MACHINES ===
{json.dumps(context_data.get('machines', []), indent=1)}

=== BUSINESS ENTRIES (Costs & Liabilities) ===
{json.dumps(context_data.get('business_entries', []), indent=1)}
"""
    messages.append({"role": "system", "content": context_msg})
    
    # Add recent history
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["message"]})
    
    messages.append({"role": "user", "content": user_message})
    
    response = _get_client().chat.completions.create(
        model=_get_deployment(),
        messages=messages,
        max_completion_tokens=3000,
    )
    return response.choices[0].message.content


# ─── INVOICE PARSER ───────────────────────────────────────────────

INVOICE_PARSER_PROMPT = """You are an expert at reading Indian business invoices for a PET preforms and caps company.
You will receive extracted text from an invoice (PDF or scanned image).
The invoice is either a SALES/OUTPUT invoice (we sold goods) or a PURCHASE/INPUT invoice (we bought materials/goods).

Extract ALL line items from the invoice and return a JSON object with this EXACT format:
{
  "invoice_no": "string or null",
  "date": "YYYY-MM-DD or null",
  "party_name": "customer or supplier name",
  "party_gstin": "GSTIN number or null",
  "items": [
    {
      "name": "product/material name",
      "hsn": "HSN code or null",
      "quantity": number,
      "unit": "kg" or "nos" or "pcs",
      "rate": number (per unit price),
      "taxable_amount": number,
      "gst_percent": number (e.g. 18),
      "gst_amount": number,
      "total": number (invoice value for this line)
    }
  ],
  "totals": {
    "taxable": number,
    "gst": number,
    "grand_total": number
  }
}

Rules:
- Extract EVERY line item, not just the first one
- Numbers should be plain numbers, not strings (no commas, no ₹ signs)
- If a field is missing, use null for strings or 0 for numbers
- For quantity, prefer "nos" (number of pieces) for preforms/caps, "kg" for raw materials
- Handle both IGST (interstate) and CGST+SGST (intrastate) formats — combine CGST+SGST into total gst_amount
- If the text is unreadable/garbled, still try your best to extract what you can
- ONLY return valid JSON, no markdown or explanation"""


def parse_invoice_text(text: str, invoice_type: str = "sales") -> dict:
    """Use AI to parse invoice text and return structured data."""
    messages = [
        {"role": "system", "content": INVOICE_PARSER_PROMPT},
        {"role": "user", "content": f"This is a {invoice_type.upper()} invoice. Extract all data:\n\n{text[:8000]}"}
    ]

    response = _get_client().chat.completions.create(
        model=_get_deployment(),
        messages=messages,
        max_completion_tokens=2000,
    )

    result_text = response.choices[0].message.content.strip()
    # Extract JSON from response
    if "```" in result_text:
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
        result_text = result_text.strip()

    return json.loads(result_text)


def parse_invoice_image(image_path: str, invoice_type: str = "sales") -> dict:
    """Use AI vision to read an invoice image directly and return structured data."""
    import base64
    import mimetypes

    mime, _ = mimetypes.guess_type(image_path)
    if not mime:
        mime = "image/jpeg"

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    messages = [
        {"role": "system", "content": INVOICE_PARSER_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": f"This is a {invoice_type.upper()} invoice image. Read every detail and extract all data as JSON."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}},
        ]},
    ]

    response = _get_client().chat.completions.create(
        model=_get_deployment(),
        messages=messages,
        max_completion_tokens=2000,
    )

    result_text = response.choices[0].message.content.strip()
    if "```" in result_text:
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
        result_text = result_text.strip()

    return json.loads(result_text)

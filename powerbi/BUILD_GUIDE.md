# Build the Power BI dashboard (reproducible, no `.pbix` supplied)

The repo includes a dashboard preview (`charts/procurement_dashboard_preview.png`), ready-to-import CSV tables and DAX measures, **not an actual `.pbix` file**. Power BI Desktop is required to produce the native report.

> **Always place this visible text in every report page:** `SIMULATED procurement demonstration | source-based inventory, hypothetical purchase orders and costs`.

## 1. Generate the dataset

```powershell
python -m pip install -r requirements.txt
python -m src.pipeline
```

## 2. Import with Power BI Desktop

Open Power BI Desktop → **Home** → **Get data** → **Text/CSV** and import these four CSVs:

| CSV | Name in Power BI | Grain |
|---|---|---|
| `data/processed/purchase_orders_SIMULATED.csv` | `FactPO` | One simulated purchase order |
| `data/processed/inventory_clean.csv` | `FactInventory` | One source inventory/product line |
| `data/processed/dim_supplier.csv` | `DimSupplier` | One supplier name-derived key |
| `data/processed/dim_product.csv` | `DimProduct` | One product ID |

In **Transform data** (Power Query): change `Order_Date`, `Promised_Date`, `Receipt_Date` to `Date`; numeric money columns to Decimal Number, count columns to Whole Number, and `FactInventory[Below_Reorder_Level]` to True/False. Use **Close & Apply**.

## 3. Star model relationships

Model view → create relationships (**Single** cross-filter direction, dimensions filter facts):

- `DimSupplier[Supplier_Key]` (1) → `FactPO[Supplier_Key]` (*)
- `DimSupplier[Supplier_Key]` (1) → `FactInventory[Supplier_Key]` (*)
- `DimProduct[Product_ID]` (1) → `FactPO[Product_ID]` (*)
- `DimProduct[Product_ID]` (1) → `FactInventory[Product_ID]` (*)
- Create the `DimDate` table from `measures.dax`, then `DimDate[Date]` (1) → `FactPO[Order_Date]` (*)

Mark `DimDate` as a Date table. **Do not** link supplier directly to product or activate additional date relationships; those can create ambiguous filter paths. `DimSupplier` is based on names because the source Supplier_ID is not stable.

## 4. Add measures

Use **Modeling → New measure** for every measure in `measures.dax`. The `DimDate` definition is **Modeling → New table** instead. For percentage measures choose the Percentage format (one decimal place); format spend as Currency.

## 5. Report page 1: Procurement overview

1. Add a **Text box** banner: `SIMULATED DATA — NOT ACTUAL PROCUREMENT PERFORMANCE`.
2. Add five **Card** visuals: `[Modeled Purchase Value]`, `[Simulated PO Count]`, `[Simulated OTIF %]`, `[Simulated Unit Fill %]`, `[Simulated Open POs]`.
3. Add **Clustered column chart**: axis `DimDate[YearMonth]`, values `[Modeled Purchase Value]`.
4. Add **Bar chart**: axis `DimProduct[Category]`, values `[Modeled Purchase Value]`, sort descending.
5. Add **Donut chart**: legend `FactPO[Fulfillment_Status]`, values `[Simulated PO Count]`.
6. Add **Slicers**: `DimSupplier[Supplier_Name]`, `DimProduct[Category]`, `DimDate[YearMonth]`.
7. Add Card for `[Hypothetical 5% Top10 Savings]` labeled **Hypothetical, not realized**.

## 6. Report page 2: Supplier scorecards

1. Create **Table** visual with `DimSupplier[Supplier_Name]` and measures `[Simulated PO Count]`, `[Modeled Purchase Value]`, `[Simulated On Time %]`, `[Simulated OTIF %]`, `[Simulated Unit Fill %]`, `[Simulated Open POs]`, `[Simulated Risk Band]`.
2. In visual filters, restrict `[Simulated PO Count] >= 5` to avoid misreading very small samples.
3. Sort by `[Simulated OTIF %]` ascending.
4. Add **Bar chart** supplier vs `[Simulated OTIF %]` and apply Top N / Bottom N as useful.
5. Apply conditional formatting to the OTIF column (red under 65%, amber 65–under 85%, green 85%+).
6. Add a caption explaining risk thresholds are **illustrative**, not operationally validated.

## 7. Report page 3: Procurement and inventory action list

1. Add a **Table** for `FactPO[PO_ID]`, `DimSupplier[Supplier_Name]`, `FactPO[Promised_Date]`, `FactPO[Ordered_Qty]`, `FactPO[Received_Qty]`, `FactPO[Fulfillment_Status]`.
2. Filter fulfillment status to **Open** or **Partial**, optionally sorted by unreceived value.
3. Add **Card** `[Observed Low Stock Lines]` and `[Observed Inventory Value at List Price]`.
4. Add a source-backed inventory table showing `DimProduct[Product_Name]`, `DimSupplier[Supplier_Name]`, `FactInventory[Stock_Quantity]`, `FactInventory[Reorder_Level]`, and `FactInventory[Suggested_Order_Units]`.
5. Apply a visual filter `FactInventory[Suggested_Order_Units] > 0`.
6. Note that inventory is a single snapshot and **must not respond to simulated order-month slicing**. Consider disabling that slicer's interactions with inventory visuals (Format → Edit interactions).

## 8. Baseline reconciliation

With **all filters cleared**, validate against `outputs/kpi_summary.json`:
- Simulated PO Count = 2,990
- Modeled Purchase Value = $912,896.42
- Simulated OTIF % = 59.50%
- Simulated Unit Fill % = 91.15%
- Simulated Open POs = 171
- Observed Low Stock Lines = 292 (excluding discontinued)
- Hypothetical 5% Top10 Savings = $7,153.66

These are **simulation outputs** except the inventory count. Actual purchase order data must replace the simulated fact table before any operational conclusions are drawn.

## 9. Save

File → Save As → `Supplier_Procurement_Analytics.pbix`. Keep screenshots in `charts/` and include the actual `.pbix` in your own GitHub repository if its file size and licensing permit.

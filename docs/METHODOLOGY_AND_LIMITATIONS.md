# Methodology, assumptions and limitations

## Real fields versus modeled fields

| Layer | Available facts | Source |
|---|---|---|
| Observed source | Product name, category, supplier name, stock quantity, reorder level, reorder quantity, listed unit price, inventory status and dates | Uploaded grocery inventory CSV |
| Derived source | Below-reorder flag, reorder gap, suggested order units, listed-price stock value proxy | Calculated exclusively from source |
| **Simulated procurement** | PO IDs, order dates, order quantities, promised/receipt dates, simulated wholesale cost, received quantities, delays and fulfillment | Seeded generator in `src/pipeline.py` |
| Hypothetical opportunity | 5% modeled negotiation savings on top ten modeled suppliers | What-if calculation, **not realized** |

## Why we do NOT compute observed OTIF from the original file

- There is no PO identifier or one-to-one receipt/order linkage.
- `Date_Received` occurs before `Last_Order_Date` in **514 / 990 source rows**.
- There is no promised or expected receipt date.
- There is no received PO quantity or actual purchase unit cost.
- All **990 original Supplier_ID values are distinct**, even though there are only 350 distinct names; supplier IDs cannot be trusted for entity joins without a master-data investigation.

Therefore, actual historical on-time delivery, actual procurement spend, fulfillment and cost-saving achievement cannot be established from the source.

## Simulation design

- Seed: `2026`, so reruns produce identical data with identical package behavior.
- Each source inventory row generates **2 to 4** modeled POs between 2024-02-25 and 2025-02-20.
- PO quantities loosely scale with source reorder quantities; unit costs are **modeled estimates** based on source listed prices and supplier-specific adjustment factors. Prices are not claimed to be acquisition cost.
- Delivery probabilities differ by supplier-specific modeled profiles to support meaningful demonstration segmentation. The profiles are not inferred supplier quality.
- Promised delivery is 4 to 18 days after simulated order date; modeled receipt is 0–3 days early or 1–10 days late if delivered.
- POs can be fully received, partially received or open. All POs have promise dates before scenario evaluation date `2025-03-31`. Open orders count as failed OTIF.
- Source inventory statuses are not imputed as purchase-order statuses.

## Definitions and interpretations

**Simulated On-time %:** Count of modeled POs with receipt date ≤ promised date / count of due modeled POs.

**Simulated In-full %:** Count of modeled POs with modeled received quantity ≥ modeled ordered quantity / count of due modeled POs.

**Simulated OTIF %:** Count of modeled POs meeting both on-time and in-full conditions / count of due modeled POs. Does not count undelivered POs as successful.

**Simulated Unit Fill %:** SUM(received modeled units) / SUM(ordered modeled units). This is not the same as in-full PO count rate.

**Modeled Order Value:** Quantity × simulated unit cost. Use the wording *modeled purchase commitments*; do not call this actual company spend.

**Observed Reorder Gap:** MAX(reorder level − stock quantity, 0). Suggested order units are MAX(original reorder quantity, reorder gap) for non-discontinued products with stock below reorder point; zero otherwise. This is a rule-of-thumb demonstration, not safety-stock optimization.

**Observed Inventory Value Proxy:** Stock × listed unit price. The uploaded `Unit_Price` is not identified as cost, so this should not be treated as GAAP inventory valuation.

**Risk bands:** On modeled OTIF with threshold High (<65%), Medium (≥65% and <85%), Low (≥85%), subject to **at least 5 POs**. Thresholds are chosen for the demo, not benchmarked to real company targets.

## Analytics validation

- Input completeness, observed date-sequence issue and source-id uniqueness are asserted or documented.
- Purchase order ID uniqueness and ordered/received quantity bounds are asserted.
- Supplier counts, ordered values and OTIF reconcile from detailed facts to aggregated scorecards.
- Source and simulation labels are embedded in filenames, tables, KPIs and UI.

## What real data would be needed to extend this professionally

A reliable `Suppliers` master (`supplier_id`, name), `PurchaseOrders` (`PO_ID`, `Supplier_ID`, `SKU`, `order_date`, `promised_date`, `ordered_qty`, `unit_cost`, currency), `Receipts` (`PO_ID`, receipt date, received quantity), `Invoices` (invoiced amount, discounts, adjustments) and preferably `SupplierContracts` (contracted prices, SLA targets). Multiple receipts must be aggregated against the corresponding PO lines before calculating on-time/in-full performance.

## Known caveats

- Suppliers are grouped by exact normalized name, not a verified master identifier. Name collisions/variants could misgroup suppliers.
- All original products have unique Product_ID, and some share names; product-level substitution analysis is not supported.
- Source snapshot dates are 2024–2025; it is **not** a current 2026 supplier dashboard.
- A simulated benchmark is good for demonstrating methods, **not** evidence of operational improvement or cost-saving achievements.

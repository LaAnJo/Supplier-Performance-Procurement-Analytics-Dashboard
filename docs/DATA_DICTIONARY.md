# Data dictionary

## `data/processed/inventory_clean.csv` — observed and derived inventory

| Field | Meaning | Provenance |
|---|---|---|
| `Product_ID`, `Product_Name` | Inventory row product identifiers and names | Source |
| `Supplier_Name`, `Supplier_ID` | Reported supplier details; Supplier_ID **not stable** across records | Source |
| `Supplier_Key` | Derived SHA1-based key from normalized supplier name | Derived; grouping only |
| `Category` | Corrected/filled spelling from source `Catagory` (missing becomes Unknown) | Derived |
| `Status` | Inventory status (Active, Backordered, Discontinued), **not PO status** | Source |
| `Date_Received`, `Last_Order_Date`, `Expiration_Date` | Dates from source, not valid paired PO events | Source |
| `Stock_Quantity`, `Reorder_Level`, `Reorder_Quantity` | Quantities | Source |
| `Unit_Price_USD` | Parsed numerical listed unit price | Derived from source currency string |
| `Inventory_Value_Price_Proxy_USD` | Stock × listed price; not necessarily accounting cost | Derived from source |
| `Below_Reorder_Level` | Whether current stock is strictly below reorder level | Derived |
| `Reorder_Gap_Units` | max(reorder level − stock, 0) | Derived |
| `Suggested_Order_Units` | Rule-of-thumb quantity if below threshold and not discontinued | Derived |
| `Date_Sequence_Invalid` | Received date is earlier than last order date | Data-quality flag |
| `Source_Type` | `OBSERVED_INVENTORY` | Explicit provenance |
| `percentage` | Ambiguous source field, **not used in metrics** | Source |

## `data/processed/purchase_orders_SIMULATED.csv` — **100% synthetic procurement PO event table**

| Field | Meaning |
|---|---|
| `PO_ID` | Unique generated order ID |
| `Product_ID`, `Product_Name`, `Category`, `Supplier_Key`, `Supplier_Name` | Joined back to observed inventory identities |
| `Order_Date`, `Order_Month` | Random modeled PO date / YYYY-MM |
| `Promised_Date`, `Receipt_Date` | Modeled promise and modeled receipt; null receipt means open PO |
| `Planned_Lead_Days`, `Modeled_Actual_Lead_Days`, `Modeled_Delay_Days` | Duration calculations **on simulated dates only** |
| `Ordered_Qty`, `Received_Qty` | Synthetic ordered and received units |
| `Unit_Cost_Model_USD` | Synthetic estimated procurement unit cost |
| `Ordered_Value_Model_USD`, `Received_Value_Model_USD` | Derived from synthetic quantities and modeled unit cost |
| `Fulfillment_Status` | `Received`, `Partial`, `Open` (modeled) |
| `On_Time_Flag`, `In_Full_Flag`, `OTIF_Flag`, `Late_Flag` | Synthetic KPI flags (0/1) |
| `Simulated`, `Scenario` | Explicit synthetic provenance markers |

## Data marts and other outputs

- `dim_supplier.csv`: distinct derived supplier name keys (350 supplier names).
- `dim_product.csv`: distinct source Product_ID with product, category and derived supplier key (990 products).
- `outputs/supplier_scorecards_SIMULATED.csv`: supplier-level PO counts, ordered and received units, modeled spend, OTIF and risk bands; also source-backed count of inventory lines.
- `outputs/monthly_spend_SIMULATED.csv`: modeled order value and PO events by order month and category.
- `outputs/category_performance_SIMULATED.csv`: modeled spending and simulated OTIF by category.
- `outputs/suppliers_to_review_SIMULATED.csv`: suppliers with at least 5 modeled POs and illustrative High risk band.
- `outputs/kpi_summary.json`: aggregate source/derived metrics and modeled scenario KPIs.
- `outputs/data_quality_report.json`: source quality warning counts and interpretation notes.
- `procurement_analytics.sqlite`: joinable tables `inventory_lines`, `simulated_purchase_orders`, `supplier_scorecards`.

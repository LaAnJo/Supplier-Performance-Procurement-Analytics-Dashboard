-- SQLite 3. All purchase order facts are SIMULATED demonstration data.
-- Run using: sqlite3 procurement_analytics.sqlite < sql/analytics_queries.sql

-- 1. Supplier scorecard: open POs count as OTIF failures once promised dates are past.
SELECT
  Supplier_Name,
  COUNT(*) AS simulated_po_count,
  ROUND(SUM(Ordered_Value_Model_USD), 2) AS modeled_order_value_usd,
  ROUND(100.0 * SUM(On_Time_Flag) / COUNT(*), 2) AS on_time_pct,
  ROUND(100.0 * SUM(In_Full_Flag) / COUNT(*), 2) AS in_full_pct,
  ROUND(100.0 * SUM(OTIF_Flag) / COUNT(*), 2) AS otif_pct,
  ROUND(100.0 * SUM(Received_Qty) / NULLIF(SUM(Ordered_Qty), 0), 2) AS unit_fill_pct
FROM simulated_purchase_orders
WHERE Promised_Date <= '2025-03-31'
GROUP BY Supplier_Key, Supplier_Name
HAVING COUNT(*) >= 5
ORDER BY otif_pct ASC, modeled_order_value_usd DESC
LIMIT 25;

-- 2. Modeled spend by category.
SELECT Category, COUNT(*) AS po_count,
       ROUND(SUM(Ordered_Value_Model_USD), 2) AS modeled_order_value_usd
FROM simulated_purchase_orders
GROUP BY Category
ORDER BY modeled_order_value_usd DESC;

-- 3. Monthly purchase order trends (hypothetical commitments, not realized spend).
SELECT Order_Month, COUNT(*) AS po_count,
       ROUND(SUM(Ordered_Value_Model_USD), 2) AS modeled_order_value_usd,
       ROUND(100.0 * SUM(OTIF_Flag) / COUNT(*), 2) AS otif_pct
FROM simulated_purchase_orders
GROUP BY Order_Month
ORDER BY Order_Month;

-- 4. Open/partial orders for investigation.
SELECT PO_ID, Supplier_Name, Product_Name, Promised_Date,
       Ordered_Qty, Received_Qty, Fulfillment_Status,
       ROUND(Ordered_Value_Model_USD - Received_Value_Model_USD, 2) AS modeled_unreceived_value
FROM simulated_purchase_orders
WHERE Fulfillment_Status IN ('Open','Partial')
ORDER BY modeled_unreceived_value DESC
LIMIT 25;

-- 5. Source-backed replenishment priority (not simulated).
SELECT Supplier_Name, Product_Name, Category, Stock_Quantity, Reorder_Level,
       Reorder_Quantity, Reorder_Gap_Units, Suggested_Order_Units
FROM inventory_lines
WHERE Below_Reorder_Level = 1 AND Status <> 'Discontinued'
ORDER BY Reorder_Gap_Units DESC, Suggested_Order_Units DESC
LIMIT 25;

-- 6. Source quality check: original Supplier_ID is not a usable supplier master ID.
SELECT Supplier_Name, COUNT(DISTINCT Supplier_ID) AS distinct_original_ids
FROM inventory_lines
GROUP BY Supplier_Name
HAVING COUNT(DISTINCT Supplier_ID) > 1
ORDER BY distinct_original_ids DESC
LIMIT 20;

-- 7. Modeled supplier spend ranking for a hypothetical 5% negotiation scenario.
WITH ranked AS (
 SELECT Supplier_Name, SUM(Ordered_Value_Model_USD) AS modeled_value
 FROM simulated_purchase_orders
 GROUP BY Supplier_Key, Supplier_Name
 ORDER BY modeled_value DESC
 LIMIT 10
)
SELECT ROUND(SUM(modeled_value),2) AS top10_modeled_order_value_usd,
       ROUND(SUM(modeled_value) * 0.05,2) AS hypothetical_5pct_savings_usd
FROM ranked;

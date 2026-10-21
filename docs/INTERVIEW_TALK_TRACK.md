# Interview walkthrough (about 2 minutes)

**Business problem:** I built a demonstration procurement visibility system for a grocery supply chain team that would need supplier delivery performance, modeled spend concentration, and replenishment risk monitoring.

**Data preparation:** The provided 990-line inventory dataset contained supplier names and inventory measures, but no valid paired purchase orders/receipts. I found 514 date-sequence inconsistencies and an unstable Supplier_ID field, so I did not calculate supplier lead time or OTIF from those records. Instead I separated observed inventory metrics from an explicitly simulated procurement fact table of 2,990 records.

**Engineering:** I built a reproducible seeded Python pipeline and stored modeled POs and supplier analytics in SQLite. I built SQL supplier scorecards and calculated OTIF, unit-weighted fill rate, delivery rates, top supplier modeled spend, reorder flags, and a hypothetical negotiation savings scenario. The repository includes tests and a data dictionary.

**BI and analysis:** I designed a three-page Power BI report specification with DAX measures and a dimensional model, built an interactive Streamlit dashboard, and exported an Excel supplier scorecard and KPI report.

**Findings, with honest framing:** From the **observed data**, 292 non-discontinued inventory lines are below their reorder points. In the **simulation**, 59.5% of POs meet OTIF and a 5% reduction applied to the modeled top-ten supplier commitments represents a hypothetical $7.15K cost scenario—not actual historical savings.

**Next step for an operational deployment:** Obtain real supplier master IDs, purchase-order lines, promised dates, receipts, contractual terms and invoice amounts; audit the entities and run OTIF/SLA reconciliation using historical data.

## Questions you may be asked

**Why not use Date_Received minus Last_Order_Date?** They do not represent reliably paired events: 514 source rows would imply a receipt before its own order. Computing lead time from these would be misleading.

**Why aren't you claiming cost reduction?** The savings is a scenario estimate using simulated spend, not a measured before-after improvement.

**Why is fill rate different from OTIF?** Fill rate weights the number of units received. OTIF weights each due purchase order equally and requires both on-time and in-full completion.

**What would you do with sparse supplier history?** Avoid rankings on very low PO counts; this demo requires at least five modeled orders per supplier for risk labels, and I'd use confidence intervals or minimum exposure thresholds on real data.

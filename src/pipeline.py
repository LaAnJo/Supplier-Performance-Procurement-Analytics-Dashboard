"""Supplier performance analytics: source-backed inventory + clearly simulated PO scenario.

Run: python -m src.pipeline
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'grocery_inventory_source.csv'
PROCESSED = ROOT / 'data' / 'processed'
OUTPUTS = ROOT / 'outputs'
DB_PATH = ROOT / 'procurement_analytics.sqlite'
SEED = 2026
AS_OF = pd.Timestamp('2025-03-31')
SIMULATED_DISCOUNT = 0.05


def supplier_key(name: str) -> str:
    """Stable *derived* ID for descriptive grouping; not a validated supplier master ID."""
    norm = ' '.join(str(name).strip().casefold().split())
    return 'SUP-' + hashlib.sha1(norm.encode('utf-8')).hexdigest()[:10].upper()


def load_inventory(path: Path = RAW) -> tuple[pd.DataFrame, dict]:
    source = pd.read_csv(path, dtype={'Product_ID': str, 'Supplier_ID': str})
    fields = ['Product_Name','Catagory','Supplier_Name','Product_ID','Supplier_ID',
              'Status','Date_Received','Last_Order_Date','Expiration_Date',
              'Stock_Quantity','Reorder_Level','Reorder_Quantity','Unit_Price']
    missing = sorted(set(fields) - set(source.columns))
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    inventory = source.copy()
    inventory['Category'] = inventory['Catagory'].fillna('Unknown').astype(str).str.strip().replace('', 'Unknown')
    inventory['Supplier_Name'] = inventory['Supplier_Name'].astype(str).str.strip()
    inventory['Supplier_Key'] = inventory['Supplier_Name'].map(supplier_key)
    for column in ['Date_Received','Last_Order_Date','Expiration_Date']:
        inventory[column] = pd.to_datetime(inventory[column], errors='coerce', format='%m/%d/%Y')
    inventory['Unit_Price_USD'] = pd.to_numeric(inventory['Unit_Price'].astype(str).str.replace('$','',regex=False).str.replace(',','',regex=False), errors='coerce')
    for col in ['Stock_Quantity','Reorder_Level','Reorder_Quantity','Sales_Volume','Inventory_Turnover_Rate']:
        inventory[col] = pd.to_numeric(inventory[col],errors='coerce')
    if inventory['Unit_Price_USD'].isna().any() or inventory[['Stock_Quantity','Reorder_Level','Reorder_Quantity']].isna().any().any():
        raise ValueError('Failed to parse required prices or quantities')
    inventory['Inventory_Value_Price_Proxy_USD'] = (inventory['Stock_Quantity'] * inventory['Unit_Price_USD']).round(2)
    inventory['Below_Reorder_Level'] = inventory['Stock_Quantity'] < inventory['Reorder_Level']
    inventory['Reorder_Gap_Units'] = (inventory['Reorder_Level'] - inventory['Stock_Quantity']).clip(lower=0)
    inventory['Suggested_Order_Units'] = np.where(
        inventory['Below_Reorder_Level'] & inventory['Status'].ne('Discontinued'),
        np.maximum(inventory['Reorder_Quantity'], inventory['Reorder_Gap_Units']), 0).astype(int)
    inventory['Date_Sequence_Invalid'] = inventory['Date_Received'] < inventory['Last_Order_Date']
    inventory['Source_Type'] = 'OBSERVED_INVENTORY'
    quality = {
        'source_rows': int(len(source)),
        'distinct_supplier_names': int(source['Supplier_Name'].nunique()),
        'distinct_source_supplier_ids': int(source['Supplier_ID'].nunique()),
        'missing_category_rows': int(source['Catagory'].isna().sum()),
        'date_received_before_last_order_rows': int(inventory['Date_Sequence_Invalid'].sum()),
        'price_parse_failed': int(inventory['Unit_Price_USD'].isna().sum()),
        'duplicate_product_ids': int(inventory['Product_ID'].duplicated().sum()),
        'supplier_names_with_multiple_original_ids': int((source.groupby('Supplier_Name')['Supplier_ID'].nunique() > 1).sum()),
        'date_quality_note': 'Date_Received and Last_Order_Date are not confirmed as paired PO events; no real delivery lead time or on-time KPI is inferred.',
        'identifier_quality_note': 'Source Supplier_ID varies by row. Supplier_Key is derived from Supplier_Name for illustrative grouping only.',
        'percentage_quality_note': 'The ambiguous percentage column is carried through unchanged and not used as a KPI.'
    }
    return inventory, quality


def generate_simulated_orders(inventory: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """A deterministic, explicitly hypothetical purchase-order dataset.

    Dates, units, estimated costs, promises, delivery and fill outcomes are simulated.
    Original inventory fields are used to anchor products, supplier names and approximate quantity scale.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    # Scenario spans one full year; all promised delivery dates precede the as-of date.
    min_date = pd.Timestamp('2024-02-25')
    max_date = pd.Timestamp('2025-02-20')
    date_span = (max_date-min_date).days
    # Supplier-specific modeled lead-time profiles produce coherent scorecard variation.
    profiles = {}
    for supplier_name in sorted(inventory['Supplier_Name'].unique()):
        profiles[supplier_name] = {
            'delay_probability': float(rng.uniform(0.09, 0.42)),
            'partial_probability': float(rng.uniform(0.03, 0.26)),
            'nonreceipt_probability': float(rng.uniform(0.01, 0.09)),
            'modeled_cost_factor': float(rng.uniform(0.58, 0.86)),
        }
    for record in inventory.itertuples(index=False):
        profile = profiles[record.Supplier_Name]
        n = int(rng.integers(2,5))
        order_days = sorted(rng.choice(date_span+1, size=n, replace=False).tolist())
        for day in order_days:
            order_date = min_date + pd.Timedelta(days=int(day))
            ordered_qty = max(1, int(round(float(record.Reorder_Quantity) * float(rng.uniform(.7, 2.0)))))
            cost_estimate = round(float(record.Unit_Price_USD) * profile['modeled_cost_factor'] * float(rng.uniform(.94, 1.06)), 2)
            cost_estimate = max(0.01,cost_estimate)
            planned_days = int(rng.integers(4,19))
            promised = order_date + pd.Timedelta(days=planned_days)
            event = float(rng.random())
            if event < profile['nonreceipt_probability']:
                received_qty = 0
                receipt_date = pd.NaT
                status = 'Open'
            else:
                is_partial = float(rng.random()) < profile['partial_probability']
                received_qty = max(1, int(np.floor(ordered_qty * float(rng.uniform(.52, .94))))) if is_partial and ordered_qty > 1 else ordered_qty
                is_late = float(rng.random()) < profile['delay_probability']
                arrival_shift = int(rng.integers(1,11)) if is_late else -int(rng.integers(0,4))
                receipt_date = promised + pd.Timedelta(days=arrival_shift)
                status = 'Partial' if received_qty < ordered_qty else 'Received'
            on_time = int(pd.notna(receipt_date) and receipt_date <= promised)
            in_full = int(received_qty >= ordered_qty)
            rows.append({
                'PO_ID': f'PO-{len(rows)+1:06d}',
                'Product_ID': record.Product_ID,
                'Product_Name': record.Product_Name,
                'Supplier_Key': record.Supplier_Key,
                'Supplier_Name': record.Supplier_Name,
                'Category': record.Category,
                'Order_Date': order_date,
                'Order_Month': order_date.strftime('%Y-%m'),
                'Promised_Date': promised,
                'Receipt_Date': receipt_date,
                'Planned_Lead_Days': planned_days,
                'Modeled_Actual_Lead_Days': int((receipt_date-order_date).days) if pd.notna(receipt_date) else None,
                'Modeled_Delay_Days': max(0, int((receipt_date-promised).days)) if pd.notna(receipt_date) else None,
                'Ordered_Qty': ordered_qty,
                'Received_Qty': received_qty,
                'Unit_Cost_Model_USD': cost_estimate,
                'Ordered_Value_Model_USD': round(ordered_qty * cost_estimate, 2),
                'Received_Value_Model_USD': round(received_qty * cost_estimate, 2),
                'Fulfillment_Status': status,
                'On_Time_Flag': on_time,
                'In_Full_Flag': in_full,
                'OTIF_Flag': int(on_time and in_full),
                'Late_Flag': int(pd.notna(receipt_date) and receipt_date > promised),
                'Simulated': 1,
                'Scenario': 'DEMONSTRATION_ONLY_NOT_ACTUAL_PO_RECORDS',
            })
    po = pd.DataFrame.from_records(rows)
    assert len(po) > 0
    assert po['PO_ID'].is_unique
    assert (po['Ordered_Qty'] >= po['Received_Qty']).all()
    assert (po['Promised_Date'] >= po['Order_Date']).all()
    assert (po.loc[po['Receipt_Date'].notna(),'Receipt_Date'] >= po.loc[po['Receipt_Date'].notna(),'Order_Date']).all()
    return po


def supplier_scorecards(orders: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    # Each supplier's denominator covers ALL modeled orders due by the as-of date,
    # including open orders: a missing delivery is counted as not OTIF.
    eligible = orders.loc[orders['Promised_Date'] <= AS_OF].copy()
    summary = eligible.groupby(['Supplier_Key','Supplier_Name'],as_index=False).agg(
        PO_Count=('PO_ID','size'),
        Ordered_Units=('Ordered_Qty','sum'),
        Received_Units=('Received_Qty','sum'),
        Modeled_Ordered_Value_USD=('Ordered_Value_Model_USD','sum'),
        Modeled_Received_Value_USD=('Received_Value_Model_USD','sum'),
        On_Time_Count=('On_Time_Flag','sum'),
        In_Full_Count=('In_Full_Flag','sum'),
        OTIF_Count=('OTIF_Flag','sum'),
        Late_Count=('Late_Flag','sum'),
        Open_Count=('Fulfillment_Status',lambda c: int((c=='Open').sum())),
        Partial_Count=('Fulfillment_Status',lambda c: int((c=='Partial').sum())),
    )
    for target,numerator in [('On_Time_Pct','On_Time_Count'),('In_Full_Pct','In_Full_Count'),('OTIF_Pct','OTIF_Count'),('Late_Delivery_Pct','Late_Count')]:
        summary[target] = (100*summary[numerator] / summary['PO_Count']).round(2)
    summary['Unit_Fill_Rate_Pct'] = (100*summary['Received_Units']/summary['Ordered_Units']).round(2)
    summary['Modeled_Ordered_Value_USD'] = summary['Modeled_Ordered_Value_USD'].round(2)
    inv_summary = inventory.groupby('Supplier_Key', as_index=False).agg(
        Inventory_Lines=('Product_ID','size'),
        Low_Stock_Lines=('Below_Reorder_Level','sum'),
        Inventory_Value_Price_Proxy_USD=('Inventory_Value_Price_Proxy_USD','sum'),
    )
    summary = summary.merge(inv_summary,on='Supplier_Key',how='left',validate='one_to_one')
    summary['Risk_Band'] = np.select(
        [summary['OTIF_Pct'] < 65,summary['OTIF_Pct'] < 85],
        ['High','Medium'], default='Low')
    summary['Scorecard_Eligible'] = summary['PO_Count'] >= 5
    return summary.sort_values('Modeled_Ordered_Value_USD',ascending=False).reset_index(drop=True)


def summary_metrics(orders: pd.DataFrame, inventory: pd.DataFrame, score: pd.DataFrame) -> dict:
    spend = float(orders['Ordered_Value_Model_USD'].sum())
    top_suppliers = score.nlargest(10,'Modeled_Ordered_Value_USD')
    return {
        'scenario_label':'ALL PROCUREMENT KPIS ARE SIMULATED / DEMONSTRATION ONLY',
        'data_as_of':str(AS_OF.date()),
        'observed_inventory_records':int(len(inventory)),
        'observed_supplier_names':int(inventory['Supplier_Name'].nunique()),
        'observed_below_reorder_lines':int(inventory['Below_Reorder_Level'].sum()),
        'observed_non_discontinued_reorder_lines':int(((inventory['Below_Reorder_Level']) & (inventory['Status']!='Discontinued')).sum()),
        'observed_stock_value_at_list_price_proxy_usd':round(float(inventory['Inventory_Value_Price_Proxy_USD'].sum()),2),
        'simulated_po_count':int(len(orders)),
        'simulated_order_value_usd':round(spend,2),
        'simulated_otif_percent':round(100 * float(orders['OTIF_Flag'].mean()),2),
        'simulated_on_time_percent':round(100 * float(orders['On_Time_Flag'].mean()),2),
        'simulated_unit_fill_percent':round(100 * float(orders['Received_Qty'].sum())/float(orders['Ordered_Qty'].sum()),2),
        'simulated_open_po_count':int(orders['Fulfillment_Status'].eq('Open').sum()),
        'simulated_top_10_spend_share_percent':round(100 * float(top_suppliers['Modeled_Ordered_Value_USD'].sum())/spend,2),
        'hypothetical_5pct_top10_negotiation_savings_usd':round(float(top_suppliers['Modeled_Ordered_Value_USD'].sum())*SIMULATED_DISCOUNT,2),
        'savings_assumption':'5% negotiated cost reduction on modeled ordered value for the 10 highest modeled-spend suppliers; NOT realized savings.',
        'supplier_scorecard_risk_note':'Risk_Band thresholds are illustrative (High <65%, Medium <85%, Low >=85% OTIF), not validated operational policy.'
    }


def export_database(inventory: pd.DataFrame, orders: pd.DataFrame, score: pd.DataFrame) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        for name, frame in [('inventory_lines', inventory), ('simulated_purchase_orders', orders), ('supplier_scorecards', score)]:
            frame.to_sql(name,connection,if_exists='replace',index=False)
        connection.executescript('''
          CREATE INDEX IF NOT EXISTS idx_po_supplier ON simulated_purchase_orders (Supplier_Key);
          CREATE INDEX IF NOT EXISTS idx_po_month ON simulated_purchase_orders (Order_Month);
          CREATE INDEX IF NOT EXISTS idx_po_category ON simulated_purchase_orders (Category);
          CREATE INDEX IF NOT EXISTS idx_inv_supplier ON inventory_lines (Supplier_Key);
        ''')


def export_charts(score: pd.DataFrame, orders: pd.DataFrame, metrics: dict) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    (ROOT / 'charts').mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(16,10),layout='constrained')
    top=score.nlargest(10,'Modeled_Ordered_Value_USD').sort_values('Modeled_Ordered_Value_USD')
    axes[0,0].barh(top['Supplier_Name'],top['Modeled_Ordered_Value_USD'],color='#2277a5')
    axes[0,0].set_title('Top 10 suppliers | MODELED order value')
    axes[0,0].xaxis.set_major_formatter(FuncFormatter(lambda x,_:f'${x/1000:.0f}k'))
    qualifying=score.loc[score.PO_Count>=5].nsmallest(10,'OTIF_Pct').sort_values('OTIF_Pct')
    axes[0,1].barh(qualifying['Supplier_Name'],qualifying['OTIF_Pct'],color='#c27030')
    axes[0,1].set_title('Lowest modeled OTIF | min. 5 POs')
    axes[0,1].set_xlim(0,105)
    axes[0,1].set_xlabel('OTIF % (simulated)')
    trend=orders.groupby('Order_Month',as_index=False)['Ordered_Value_Model_USD'].sum()
    axes[1,0].plot(trend['Order_Month'],trend['Ordered_Value_Model_USD'],marker='o',color='#28715f')
    axes[1,0].set_title('Monthly modeled purchase commitments')
    axes[1,0].tick_params(axis='x',labelrotation=50)
    axes[1,0].yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'${x/1000:.0f}k'))
    stat=orders['Fulfillment_Status'].value_counts().reindex(['Received','Partial','Open'],fill_value=0)
    axes[1,1].bar(stat.index,stat.values,color=['#28715f','#d5a245','#ab4956'])
    axes[1,1].set_title('Simulated PO fulfillment status')
    axes[1,1].set_ylabel('Number of POs')
    fig.suptitle('SUPPLIER & PROCUREMENT ANALYTICS  |  DEMONSTRATION DATA (NOT ACTUAL PROCUREMENT RECORDS)',fontsize=15,weight='bold')
    fig.savefig(ROOT/'charts'/'procurement_dashboard_preview.png',dpi=160,bbox_inches='tight')
    plt.close(fig)


def run() -> dict:
    PROCESSED.mkdir(parents=True,exist_ok=True)
    OUTPUTS.mkdir(parents=True,exist_ok=True)
    inventory, quality = load_inventory()
    orders = generate_simulated_orders(inventory)
    scorecards = supplier_scorecards(orders,inventory)
    kpis=summary_metrics(orders,inventory,scorecards)
    inv_for_export=inventory.copy()
    for c in ['Date_Received','Last_Order_Date','Expiration_Date']:
        inv_for_export[c]=inv_for_export[c].dt.strftime('%Y-%m-%d')
    inv_for_export.to_csv(PROCESSED/'inventory_clean.csv',index=False)
    orders.to_csv(PROCESSED/'purchase_orders_SIMULATED.csv',index=False,date_format='%Y-%m-%d')
    scorecards.to_csv(OUTPUTS/'supplier_scorecards_SIMULATED.csv',index=False)
    scorecards[['Supplier_Key','Supplier_Name']].drop_duplicates().to_csv(PROCESSED/'dim_supplier.csv',index=False)
    inv_for_export[['Product_ID','Product_Name','Category','Supplier_Key']].drop_duplicates('Product_ID').to_csv(PROCESSED/'dim_product.csv',index=False)
    orders.groupby(['Order_Month','Category'],as_index=False).agg(
        Simulated_Order_Value_USD=('Ordered_Value_Model_USD','sum'),
        PO_Count=('PO_ID','size'),OTIF_Count=('OTIF_Flag','sum')
    ).to_csv(OUTPUTS/'monthly_spend_SIMULATED.csv',index=False)
    cat=orders.groupby('Category',as_index=False).agg(
        PO_Count=('PO_ID','size'),Simulated_Order_Value_USD=('Ordered_Value_Model_USD','sum'),
        OTIF_Count=('OTIF_Flag','sum')
    )
    cat['OTIF_Pct'] = (100*cat['OTIF_Count']/cat['PO_Count']).round(2)
    cat.to_csv(OUTPUTS/'category_performance_SIMULATED.csv',index=False)
    risk=scorecards.loc[(scorecards['Scorecard_Eligible']) & (scorecards['Risk_Band']=='High')].copy()
    risk.to_csv(OUTPUTS/'suppliers_to_review_SIMULATED.csv',index=False)
    (OUTPUTS/'kpi_summary.json').write_text(json.dumps(kpis,indent=2),encoding='utf-8')
    (OUTPUTS/'data_quality_report.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    export_database(inventory,orders,scorecards)
    export_charts(scorecards, orders, kpis)
    return {**kpis,**{'data_quality':quality}}

if __name__ == '__main__':
    print(json.dumps(run(),indent=2))

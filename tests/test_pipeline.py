import pandas as pd
from src.pipeline import AS_OF, generate_simulated_orders, load_inventory, supplier_key, supplier_scorecards, summary_metrics


def _fixtures():
    inventory, quality = load_inventory()
    orders = generate_simulated_orders(inventory)
    return inventory,quality,orders


def test_original_inventory_has_expected_size_and_supplier_identity_quality():
    inventory,quality,orders=_fixtures()
    assert len(inventory) == 990
    assert quality['date_received_before_last_order_rows'] == 514
    assert quality['distinct_supplier_names'] == 350
    assert quality['distinct_source_supplier_ids'] == 990
    assert supplier_key('  Katz ') == supplier_key('katz')
    assert inventory['Source_Type'].eq('OBSERVED_INVENTORY').all()


def test_simulated_po_integrity_and_explicit_provenance():
    inventory,_,orders=_fixtures()
    assert orders['PO_ID'].is_unique
    assert orders['Simulated'].eq(1).all()
    assert orders['Scenario'].eq('DEMONSTRATION_ONLY_NOT_ACTUAL_PO_RECORDS').all()
    assert (orders['Received_Qty'] <= orders['Ordered_Qty']).all()
    assert (orders['Ordered_Qty'] > 0).all()
    assert (orders['Order_Date'] <= orders['Promised_Date']).all()
    assert (orders['Promised_Date'] <= AS_OF).all()
    assert orders['Product_ID'].isin(inventory['Product_ID']).all()
    assert orders.loc[orders['Receipt_Date'].isna(),'Received_Qty'].eq(0).all()
    assert (orders['OTIF_Flag'] <= orders['On_Time_Flag']).all()
    assert (orders['OTIF_Flag'] <= orders['In_Full_Flag']).all()


def test_kpis_reconcile_to_fact_table():
    inventory,quality,orders=_fixtures()
    score=supplier_scorecards(orders,inventory)
    kpis=summary_metrics(orders,inventory,score)
    assert score['PO_Count'].sum() == len(orders)
    assert abs(score['Modeled_Ordered_Value_USD'].sum() - orders['Ordered_Value_Model_USD'].sum()) < 0.01
    assert kpis['simulated_otif_percent'] == round(100 * orders['OTIF_Flag'].mean(),2)
    assert 0 <= kpis['simulated_unit_fill_percent'] <= 100
    assert kpis['hypothetical_5pct_top10_negotiation_savings_usd'] > 0


def test_reorder_flag_excludes_discontinued_from_recommendation():
    inventory,_,_= _fixtures()
    excluded=inventory[inventory['Status']=='Discontinued']
    assert excluded['Suggested_Order_Units'].eq(0).all()
    assert inventory['Unit_Price_USD'].notna().all()

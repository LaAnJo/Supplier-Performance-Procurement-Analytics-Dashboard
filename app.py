"""Interactive Streamlit demo. Usage: streamlit run app.py
Every procurement metric shown here comes from SIMULATED, NOT actual PO events.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Procurement Command Center | Demo',layout='wide',page_icon='📦')
st.markdown('''<style>
.block-container{padding-top:1.4rem;max-width:1450px}
[data-testid="stMetric"]{background:#eff4f9;border:1px solid #dce6ee;padding:14px 18px;border-radius:12px}
</style>''',unsafe_allow_html=True)
st.title('Supplier & Procurement Command Center')
st.warning('**SIMULATED DEMONSTRATION:** Purchase orders, order values, receipt dates, delivery and fulfillment metrics are synthetic. They are NOT historical supplier facts. Inventory fields are from the uploaded grocery inventory dataset.')

@st.cache_data
def get_data():
    po = pd.read_csv(ROOT/'data/processed/purchase_orders_SIMULATED.csv',parse_dates=['Order_Date','Promised_Date','Receipt_Date'])
    inv = pd.read_csv(ROOT/'data/processed/inventory_clean.csv')
    return po,inv

try:
    po,inventory = get_data()
except FileNotFoundError:
    st.error('Run `python -m src.pipeline` to generate the datasets first.')
    st.stop()

st.sidebar.header('Demo filters')
category=st.sidebar.multiselect('Product category',sorted(po['Category'].unique()),default=[])
supplier=st.sidebar.multiselect('Supplier',sorted(po['Supplier_Name'].unique()),default=[])
month=st.sidebar.multiselect('Order month',sorted(po['Order_Month'].unique()),default=[])
filtered=po.copy()
if category: filtered=filtered[filtered['Category'].isin(category)]
if supplier: filtered=filtered[filtered['Supplier_Name'].isin(supplier)]
if month: filtered=filtered[filtered['Order_Month'].isin(month)]
inv_filtered=inventory.copy()
if category: inv_filtered=inv_filtered[inv_filtered['Category'].isin(category)]
if supplier: inv_filtered=inv_filtered[inv_filtered['Supplier_Name'].isin(supplier)]
st.sidebar.caption('Inventory metrics ignore order-month filtering because the source is a snapshot, not a monthly time series.')

if filtered.empty:
    st.info('No simulated purchase orders match these filters.')
    st.stop()

def money(x): return '${:,.0f}'.format(x)
def pct(x): return '{:.1f}%'.format(x)

tabs=st.tabs(['Procurement overview','Supplier scorecards','Inventory signals','PO explorer & definitions'])
with tabs[0]:
    cols=st.columns(5)
    cols[0].metric('Modeled order value',money(filtered['Ordered_Value_Model_USD'].sum()))
    cols[1].metric('Simulated PO count',f'{len(filtered):,}')
    cols[2].metric('Simulated OTIF',pct(filtered['OTIF_Flag'].mean()*100))
    cols[3].metric('Modeled unit fill rate',pct(100*filtered['Received_Qty'].sum()/filtered['Ordered_Qty'].sum()))
    cols[4].metric('Open POs',f'{filtered.Fulfillment_Status.eq("Open").sum():,}')
    c1,c2=st.columns(2)
    with c1:
        monthly=filtered.groupby('Order_Month',as_index=False)['Ordered_Value_Model_USD'].sum()
        st.plotly_chart(px.bar(monthly,x='Order_Month',y='Ordered_Value_Model_USD',title='Simulated purchase commitments by month',labels={'Ordered_Value_Model_USD':'Modeled order value ($)','Order_Month':'Month'},color_discrete_sequence=['#26789d']),use_container_width=True)
    with c2:
        stat=filtered['Fulfillment_Status'].value_counts().reset_index()
        st.plotly_chart(px.pie(stat,names='Fulfillment_Status',values='count',hole=.55,title='Modeled PO fulfillment mix',color='Fulfillment_Status',color_discrete_map={'Received':'#238064','Partial':'#d2a245','Open':'#b24855'}),use_container_width=True)
    cat=filtered.groupby('Category',as_index=False)['Ordered_Value_Model_USD'].sum().sort_values('Ordered_Value_Model_USD')
    st.plotly_chart(px.bar(cat,x='Ordered_Value_Model_USD',y='Category',orientation='h',title='Modeled procurement value by product category',labels={'Ordered_Value_Model_USD':'Modeled order value ($)'},color_discrete_sequence=['#238064']),use_container_width=True)
with tabs[1]:
    supplier_df=filtered.groupby(['Supplier_Key','Supplier_Name'],as_index=False).agg(
        PO_Count=('PO_ID','count'),Value_USD=('Ordered_Value_Model_USD','sum'),On_Time_Count=('On_Time_Flag','sum'),
        OTIF_Count=('OTIF_Flag','sum'),Received_Units=('Received_Qty','sum'),Ordered_Units=('Ordered_Qty','sum'),
        Open_Count=('Fulfillment_Status',lambda s:(s=='Open').sum()))
    supplier_df['On_Time_Pct']=(supplier_df['On_Time_Count']/supplier_df['PO_Count']*100).round(1)
    supplier_df['OTIF_Pct']=(supplier_df['OTIF_Count']/supplier_df['PO_Count']*100).round(1)
    supplier_df['Unit_Fill_Pct']=(supplier_df['Received_Units']/supplier_df['Ordered_Units']*100).round(1)
    supplier_df['Risk_Band']=supplier_df.apply(lambda r: 'Insufficient data' if r.PO_Count < 5 else 'High' if r.OTIF_Pct < 65 else 'Medium' if r.OTIF_Pct < 85 else 'Low',axis=1)
    n=st.slider('Minimum simulated POs per supplier',1,20,5)
    scored=supplier_df[supplier_df.PO_Count>=n]
    if not scored.empty:
        st.dataframe(scored.sort_values(['OTIF_Pct','Value_USD'],ascending=[True,False])[['Supplier_Name','PO_Count','Value_USD','On_Time_Pct','OTIF_Pct','Unit_Fill_Pct','Open_Count','Risk_Band']],hide_index=True,use_container_width=True)
        bottom=scored.nsmallest(12,'OTIF_Pct').sort_values('OTIF_Pct')
        st.plotly_chart(px.bar(bottom,x='OTIF_Pct',y='Supplier_Name',orientation='h',title='Lowest modeled OTIF among selected suppliers',range_x=[0,100],labels={'OTIF_Pct':'OTIF (%)'},color_discrete_sequence=['#b95742']),use_container_width=True)
    st.caption('Risk thresholds (<65% High, 65–<85% Medium, ≥85% Low) are demonstration rules. Small PO counts should not be used to infer real supplier quality.')
with tabs[2]:
    left,right=st.columns(2)
    low=inv_filtered[(inv_filtered['Below_Reorder_Level']) & (inv_filtered['Status']!='Discontinued')].copy()
    left.metric('Observed inventory lines',f'{len(inv_filtered):,}')
    right.metric('Observed actionable low-stock lines',f'{len(low):,}')
    st.caption('Inventory metrics are observed snapshot fields. Stock value uses listed unit price, which may not be acquisition cost.')
    st.dataframe(low.sort_values('Reorder_Gap_Units',ascending=False)[['Product_Name','Supplier_Name','Category','Status','Stock_Quantity','Reorder_Level','Reorder_Gap_Units','Suggested_Order_Units']].head(100),hide_index=True,use_container_width=True)
with tabs[3]:
    st.dataframe(filtered.sort_values('Order_Date',ascending=False).head(500),hide_index=True,use_container_width=True)
    st.download_button('Download filtered simulated POs',filtered.to_csv(index=False).encode('utf-8'),file_name='filtered_SIMULATED_purchase_orders.csv',mime='text/csv')
    st.markdown('''**Metric definitions:** OTIF = on-time AND in-full orders / all simulated POs due. An open order counts as failed OTIF. Unit fill = received simulated units / ordered simulated units. Modeled value = ordered units × simulated unit cost. Savings scenario = 5% × modeled order value from the 10 largest suppliers, not realized savings.''')
    st.caption('Modeling reference date: 2025-03-31. Source inventory date fields were NOT used to calculate actual lead time due to contradictory sequences.')

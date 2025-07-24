import sys
import pandas as pd
from core.loader import load_csv_chunked
import streamlit as st

# Usage: streamlit run logic/dma_dashboard.py -- data/inventory_2025_07.csv

def load_data(file_path):
    columns = [
        'seller_name', 'mc_dealer_id', 'status_date', 'vin', 'make', 'model', 'body_type', 'city', 'state', 'zip', 'inventory_type', 'price'
    ]
    return load_csv_chunked(file_path, columns=columns)

def export_csvs(df):
    df.to_csv('export_all_sales.csv', index=False)
    df.groupby(['zip', 'city', 'state'])['vin'].nunique().reset_index(name='sales_count').to_csv('export_dma_sales.csv', index=False)
    df.groupby(['inventory_type', 'body_type'])['vin'].nunique().reset_index(name='sales_count').to_csv('export_segment_sales.csv', index=False)
    df.groupby(['make', 'model'])['vin'].nunique().reset_index(name='sales_count').to_csv('export_model_sales.csv', index=False)

def main(file_path):
    st.title('DMA-like Dealer Sales Dashboard')
    df = load_data(file_path)
    export_csvs(df)
    st.write(f"Loaded {len(df):,} rows.")

    # Sidebar filters
    zips = sorted(df['zip'].dropna().unique())
    cities = sorted(df['city'].dropna().unique())
    states = sorted(df['state'].dropna().unique())
    selected_zip = st.sidebar.selectbox('Filter by ZIP', ['All'] + zips)
    selected_city = st.sidebar.selectbox('Filter by City', ['All'] + cities)
    selected_state = st.sidebar.selectbox('Filter by State', ['All'] + states)

    filtered = df.copy()
    if selected_zip != 'All':
        filtered = filtered[filtered['zip'] == selected_zip]
    if selected_city != 'All':
        filtered = filtered[filtered['city'] == selected_city]
    if selected_state != 'All':
        filtered = filtered[filtered['state'] == selected_state]

    st.subheader('Top Dealers')
    top_dealers = filtered.groupby(['mc_dealer_id', 'seller_name'])['vin'].nunique().reset_index(name='sales_count')
    st.dataframe(top_dealers.sort_values('sales_count', ascending=False).head(10))

    st.subheader('Top Models')
    top_models = filtered.groupby(['make', 'model'])['vin'].nunique().reset_index(name='sales_count')
    st.dataframe(top_models.sort_values('sales_count', ascending=False).head(10))

    st.subheader('Sales by Inventory Type and Body Type')
    seg = filtered.groupby(['inventory_type', 'body_type'])['vin'].nunique().reset_index(name='sales_count')
    st.dataframe(seg.sort_values('sales_count', ascending=False))

    st.subheader('Sales by ZIP, City, State')
    dma = filtered.groupby(['zip', 'city', 'state'])['vin'].nunique().reset_index(name='sales_count')
    st.dataframe(dma.sort_values('sales_count', ascending=False).head(20))

    st.write('All results exported as CSVs in the current directory.')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = 'data/inventory_2025_07.csv'
    main(file_path) 
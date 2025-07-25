import streamlit as st
import pandas as pd
import os
from io import BytesIO

SUMMARY_PATH = "state/dealer_sales_summary.parquet"
BY_MODEL_PATH = "state/dealer_sales_by_model.parquet"
RAW_PATH = "state/main_record.parquet"

st.set_page_config(page_title="Dealer Competitor Analysis Dashboard", layout="wide")

@st.cache_data(show_spinner=False)
def load_data():
    summary = pd.read_parquet(SUMMARY_PATH) if os.path.exists(SUMMARY_PATH) else None
    by_model = pd.read_parquet(BY_MODEL_PATH) if os.path.exists(BY_MODEL_PATH) else None
    raw_df = pd.read_parquet(RAW_PATH) if os.path.exists(RAW_PATH) else None
    # Deduplicate for safety
    if summary is not None:
        summary = summary.drop_duplicates('mc_dealer_id', keep='first')
    if by_model is not None:
        by_model = by_model.drop_duplicates(['mc_dealer_id', 'neo_make', 'neo_model'], keep='first')
    if raw_df is not None:
        raw_df = raw_df.drop_duplicates('vin', keep='first')
    return summary, by_model, raw_df

def to_csv_download(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

def main():
    st.title("🚗 Dealer Competitor Analysis Dashboard")
    # Add refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.experimental_rerun()
    with st.spinner("Loading data..."):
        summary, by_model, raw_df = load_data()
    if summary is None or by_model is None or raw_df is None:
        st.error("Required summary or raw file not found. Run ETL first.")
        return

    tab1, tab2, tab3 = st.tabs(["Competitor Analysis", "Top 5 Dealers by Sales", "Summary Stats"])

    with tab1:
        st.sidebar.header("Filters")
        # Multi-select for makes/models
        makes = sorted(by_model['neo_make'].unique())
        selected_makes = st.sidebar.multiselect("Make(s)", makes, default=makes[:1] if makes else [])
        if selected_makes:
            models = sorted(by_model[by_model['neo_make'].isin(selected_makes)]['neo_model'].unique())
        else:
            models = sorted(by_model['neo_model'].unique())
        selected_models = st.sidebar.multiselect("Model(s)", models, default=models[:1] if models else [])
        zips = sorted(raw_df['zip'].unique())
        selected_zip = st.sidebar.selectbox("Zip Code", ["All"] + zips)
        zip_group = st.sidebar.slider("Zip Code Radius (+/-)", 0, 50, 10)
        dealers = sorted(raw_df['mc_dealer_id'].unique())
        selected_dealer = st.sidebar.selectbox("Your Dealer ID", ["All"] + dealers)
        min_sales = st.sidebar.number_input("Min Sales Count", min_value=0, value=0)
        max_sales = st.sidebar.number_input("Max Sales Count", min_value=0, value=1000000)
        top_n_options = [10, 20, 50, 100, "All"]
        top_n = st.sidebar.selectbox("Show Top N", top_n_options, index=0)

        # Filter logic
        filtered_by_model = by_model.copy()
        if selected_makes:
            filtered_by_model = filtered_by_model[filtered_by_model['neo_make'].isin(selected_makes)]
        if selected_models:
            filtered_by_model = filtered_by_model[filtered_by_model['neo_model'].isin(selected_models)]
        if selected_zip != "All":
            selected_zip = int(selected_zip)
            dealers_in_area = raw_df[(raw_df['zip'] >= selected_zip - zip_group) & (raw_df['zip'] <= selected_zip + zip_group)]['mc_dealer_id'].unique()
            filtered_by_model = filtered_by_model[filtered_by_model['mc_dealer_id'].isin(dealers_in_area)]
        # Sales count filter
        filtered_by_model = filtered_by_model[(filtered_by_model['sales_count'] >= min_sales) & (filtered_by_model['sales_count'] <= max_sales)]
        inv = raw_df.copy()
        if selected_makes:
            inv = inv[inv['neo_make'].isin(selected_makes)]
        if selected_models:
            inv = inv[inv['neo_model'].isin(selected_models)]
        if selected_zip != "All":
            inv = inv[inv['mc_dealer_id'].isin(dealers_in_area)]
        inv_counts = inv.groupby('mc_dealer_id').size().reset_index(name='current_inventory')
        dealer_info_cols = ['mc_dealer_id', 'seller_name', 'city', 'state', 'zip']
        for col in [
            'mc_dealership_group_name', 'dealer_type', 'source',
            'latitude', 'longitude', 'seller_phone', 'seller_email',
            'car_seller_name', 'car_address', 'photo_links']:
            if col in raw_df.columns:
                dealer_info_cols.append(col)
        dealer_info = raw_df.drop_duplicates('mc_dealer_id')[dealer_info_cols]
        merged = filtered_by_model.merge(dealer_info, on='mc_dealer_id', how='left').merge(inv_counts, on='mc_dealer_id', how='left')
        merged['current_inventory'] = merged['current_inventory'].fillna(0).astype(int)
        # Export filtered table
        st.download_button(
            label="Export Table to CSV",
            data=to_csv_download(merged),
            file_name="competitor_analysis.csv",
            mime="text/csv"
        )
        st.subheader(f"Top Dealers for {', '.join(selected_makes) if selected_makes else '[All Makes]'} {', '.join(selected_models) if selected_models else '[All Models]'}" + (f" in Zip {selected_zip} +/- {zip_group}" if selected_zip != 'All' else " (All Zips)"))
        display_cols = ['seller_name', 'city', 'state', 'zip', 'current_inventory', 'sales_count']
        for col in [
            'mc_dealership_group_name', 'dealer_type', 'source',
            'latitude', 'longitude', 'seller_phone', 'seller_email',
            'car_seller_name', 'car_address', 'photo_links']:
            if col in merged.columns:
                display_cols.append(col)
        if top_n == "All":
            st.dataframe(merged.sort_values('sales_count', ascending=False)[display_cols], use_container_width=True)
        else:
            st.dataframe(merged.sort_values('sales_count', ascending=False)[display_cols].head(int(top_n)), use_container_width=True)
        # Show client dealer's performance
        st.subheader("Your Dealership Performance")
        if selected_dealer != "All":
            client_row = merged[merged['mc_dealer_id'] == int(selected_dealer)]
            if not client_row.empty:
                st.metric("Current Inventory", client_row.iloc[0]['current_inventory'], help="Current inventory for your dealership.")
                st.metric("Total Sold", client_row.iloc[0]['sales_count'], help="Total new car sales for your dealership.")
                st.write(client_row[display_cols])
            else:
                st.info("Your dealership did not sell this make/model in this area in the selected period.")
        else:
            st.info("Select your dealer ID to see your performance.")
        # Show overall stats
        st.subheader("Market Overview")
        st.metric("Total Dealers in Area", len(merged), help="Number of dealers matching the current filters.")
        st.metric("Total Sales in Area", merged['sales_count'].sum(), help="Total new car sales in the filtered area.")
        st.metric("Total Inventory in Area", merged['current_inventory'].sum(), help="Current inventory in the filtered area.")

    with tab2:
        st.header("Top 5 Dealers by Total Sales (All Makes/Models)")
        top5 = summary.sort_values('total_sold', ascending=False).head(5)
        st.dataframe(top5[['mc_dealer_id', 'total_sold', 'active_inventory']], use_container_width=True)
        st.bar_chart(top5.set_index('mc_dealer_id')['total_sold'])

    with tab3:
        st.header("Summary Stats & KPIs")
        st.metric("Total Unique VINs", len(raw_df['vin'].unique()), help="Total unique vehicles in the main record.")
        st.metric("Total Dealers", len(summary['mc_dealer_id'].unique()), help="Total unique dealers in the summary.")
        st.metric("Total Makes", len(raw_df['neo_make'].unique()), help="Total unique makes in the main record.")
        st.metric("Total Models", len(raw_df['neo_model'].unique()), help="Total unique models in the main record.")
        st.write("#### Top 10 Makes by Inventory")
        st.dataframe(raw_df['neo_make'].value_counts().head(10).reset_index().rename(columns={'index': 'Make', 'neo_make': 'Inventory Count'}))
        st.write("#### Top 10 Models by Inventory")
        st.dataframe(raw_df['neo_model'].value_counts().head(10).reset_index().rename(columns={'index': 'Model', 'neo_model': 'Inventory Count'}))
        st.write("#### Top 10 Dealers by Inventory")
        st.dataframe(raw_df.groupby('mc_dealer_id').size().sort_values(ascending=False).head(10).reset_index().rename(columns={0: 'Inventory Count'}))

if __name__ == "__main__":
    main() 
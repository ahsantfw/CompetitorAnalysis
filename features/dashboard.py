import streamlit as st
import pandas as pd
import os

SUMMARY_PATH = "state/dealer_sales_summary.parquet"
BY_MODEL_PATH = "state/dealer_sales_by_model.parquet"
RAW_PATH = "state/main_record.parquet"

st.set_page_config(page_title="Dealer Competitor Analysis Dashboard", layout="wide")

@st.cache_data
def load_data():
    summary = pd.read_parquet(SUMMARY_PATH) if os.path.exists(SUMMARY_PATH) else None
    by_model = pd.read_parquet(BY_MODEL_PATH) if os.path.exists(BY_MODEL_PATH) else None
    raw_df = pd.read_parquet(RAW_PATH) if os.path.exists(RAW_PATH) else None
    return summary, by_model, raw_df

def main():
    st.title("🚗 Dealer Competitor Analysis Dashboard")
    summary, by_model, raw_df = load_data()
    if summary is None or by_model is None or raw_df is None:
        st.error("Required summary or raw file not found. Run ETL first.")
        return

    tab1, tab2 = st.tabs(["Competitor Analysis", "Top 5 Dealers by Sales"])

    with tab1:
        # Sidebar filters
        st.sidebar.header("Filters")
        makes = sorted(by_model['make'].unique())
        makes = ["All"] + makes
        selected_make = st.sidebar.selectbox("Make", makes)
        if selected_make == "All":
            models = sorted(by_model['model'].unique())
        else:
            models = sorted(by_model[by_model['make'] == selected_make]['model'].unique())
        models = ["All"] + models
        selected_model = st.sidebar.selectbox("Model", models)
        zips = sorted(raw_df['zip'].unique())
        zips = ["All"] + zips
        selected_zip = st.sidebar.selectbox("Zip Code", zips)
        zip_group = st.sidebar.slider("Zip Code Radius (+/-)", 0, 50, 10)
        dealers = sorted(raw_df['mc_dealer_id'].unique())
        dealers = ["All"] + dealers
        selected_dealer = st.sidebar.selectbox("Your Dealer ID", dealers)
        top_n_options = [10, 20, 50, 100, "All"]
        top_n = st.sidebar.selectbox("Show Top N", top_n_options, index=0)

        # Filter logic
        filtered_by_model = by_model.copy()
        if selected_make != "All":
            filtered_by_model = filtered_by_model[filtered_by_model['make'] == selected_make]
        if selected_model != "All":
            filtered_by_model = filtered_by_model[filtered_by_model['model'] == selected_model]
        if selected_zip != "All":
            selected_zip = int(selected_zip)
            dealers_in_area = raw_df[(raw_df['zip'] >= selected_zip - zip_group) & (raw_df['zip'] <= selected_zip + zip_group)]['mc_dealer_id'].unique()
            filtered_by_model = filtered_by_model[filtered_by_model['mc_dealer_id'].isin(dealers_in_area)]
        inv = raw_df.copy()
        if selected_make != "All":
            inv = inv[inv['make'] == selected_make]
        if selected_model != "All":
            inv = inv[inv['model'] == selected_model]
        if selected_zip != "All":
            inv = inv[inv['mc_dealer_id'].isin(dealers_in_area)]
        inv_counts = inv.groupby('mc_dealer_id').size().reset_index(name='current_inventory')
        dealer_info_cols = ['mc_dealer_id', 'seller_name', 'city', 'state', 'zip']
        for col in ['mc_dealership_group_name', 'dealer_type', 'source']:
            if col in raw_df.columns:
                dealer_info_cols.append(col)
        dealer_info = raw_df.drop_duplicates('mc_dealer_id')[dealer_info_cols]
        merged = filtered_by_model.merge(dealer_info, on='mc_dealer_id', how='left').merge(inv_counts, on='mc_dealer_id', how='left')
        merged['current_inventory'] = merged['current_inventory'].fillna(0).astype(int)

        st.subheader(f"Top Dealers for {selected_make if selected_make != 'All' else '[All Makes]'} {selected_model if selected_model != 'All' else '[All Models]'}" + (f" in Zip {selected_zip} +/- {zip_group}" if selected_zip != 'All' else " (All Zips)"))
        display_cols = ['seller_name', 'city', 'state', 'zip', 'current_inventory', 'sales_count']
        for col in ['mc_dealership_group_name', 'dealer_type', 'source']:
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
                st.metric("Current Inventory", client_row.iloc[0]['current_inventory'])
                st.metric("Total Sold", client_row.iloc[0]['sales_count'])
                st.write(client_row[display_cols])
            else:
                st.info("Your dealership did not sell this make/model in this area in the selected period.")
        else:
            st.info("Select your dealer ID to see your performance.")

        # Show overall stats
        st.subheader("Market Overview")
        st.metric("Total Dealers in Area", len(merged))
        st.metric("Total Sales in Area", merged['sales_count'].sum())
        st.metric("Total Inventory in Area", merged['current_inventory'].sum())

    with tab2:
        st.header("Top 5 Dealers by Total Sales (All Makes/Models)")
        top5 = summary.sort_values('total_sold', ascending=False).head(5)
        st.dataframe(top5[['mc_dealer_id', 'total_sold', 'active_inventory']], use_container_width=True)
        st.bar_chart(top5.set_index('mc_dealer_id')['total_sold'])

if __name__ == "__main__":
    main() 
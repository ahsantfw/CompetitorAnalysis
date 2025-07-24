import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from datetime import datetime, timedelta
import numpy as np

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loader import load_csv_chunked
from core.sales import precompute_dealer_stats
from core.db import engine

# Page configuration
st.set_page_config(
    page_title="Dealer Competitive Analysis Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .dealer-info {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and cache the sales data"""
    try:
        # Try to load from database first
        with engine.connect() as conn:
            from sqlalchemy import text
            # Check if we have aggregated data
            summary_query = text("SELECT COUNT(*) as count FROM dealer_sales_summary")
            result = conn.execute(summary_query).fetchone()
            if result and result[0] > 0:
                # Load from database using SQL Server syntax
                summary_df = pd.read_sql("SELECT * FROM dealer_sales_summary", conn)
                by_model_df = pd.read_sql("SELECT * FROM dealer_sales_by_model", conn)
                raw_df = pd.read_sql("SELECT * FROM sales_raw", conn)  # Load all data
                return summary_df, by_model_df, raw_df
        
        # Fallback to CSV loading
        csv_path = "data/inventory_2025_07.csv"
        if os.path.exists(csv_path):
            df = load_csv_chunked(csv_path, date_col='status_date')
            summary_df, by_model_df = precompute_dealer_stats(df)
            return summary_df, by_model_df, df  # Load all data
        else:
            st.error(f"Data file not found: {csv_path}")
            return None, None, None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None, None

def create_filters():
    """Create sidebar filters"""
    st.sidebar.header("🔍 Filters")
    
    # Outside DMA filter
    outside_dma = st.sidebar.selectbox(
        "Outside DMA",
        ["Include", "Exclude"],
        help="Include or exclude dealers outside the selected DMA"
    )
    
    # Year filter
    year_filter = st.sidebar.selectbox(
        "Year",
        ["Rolling 12", "YTD", "Calendar"],
        help="Time period for analysis"
    )
    
    # Vehicle type filter
    vehicle_type = st.sidebar.selectbox(
        "Vehicles",
        ["All", "New", "Used"],
        help="Filter by vehicle type"
    )
    
    # Sales range filter
    min_sales = st.sidebar.number_input("Min Sales", min_value=0, value=0)
    max_sales = st.sidebar.number_input("Max Sales", min_value=0, value=1000)
    
    # Dealers filter (multi-select)
    if 'summary_df' in st.session_state and st.session_state.summary_df is not None:
        dealers = st.session_state.summary_df['dealer_id'].unique()
        selected_dealers = st.sidebar.multiselect("Dealers", dealers)
    else:
        selected_dealers = []
    
    # Segments filter
    segments = st.sidebar.multiselect(
        "Segments",
        ["1-67", "68-134", "135-201", "202-268", "269-335", "336-403"],
        help="Sales volume segments"
    )
    
    # Makes filter
    if 'by_model_df' in st.session_state and st.session_state.by_model_df is not None:
        makes = st.session_state.by_model_df['make'].unique()
        selected_makes = st.sidebar.multiselect("Makes", makes)
    else:
        selected_makes = []
    
    # Models filter
    if 'by_model_df' in st.session_state and st.session_state.by_model_df is not None:
        models = st.session_state.by_model_df['model'].unique()
        selected_models = st.sidebar.multiselect("Models", models)
    else:
        selected_models = []
    
    # Zipcodes filter
    if 'raw_df' in st.session_state and st.session_state.raw_df is not None:
        zipcodes = st.session_state.raw_df['zip'].dropna().unique()
        selected_zipcodes = st.sidebar.multiselect("Zipcodes", zipcodes[:50])  # Limit to first 50
    else:
        selected_zipcodes = []
    
    return {
        'outside_dma': outside_dma,
        'year_filter': year_filter,
        'vehicle_type': vehicle_type,
        'min_sales': min_sales,
        'max_sales': max_sales,
        'selected_dealers': selected_dealers,
        'segments': segments,
        'selected_makes': selected_makes,
        'selected_models': selected_models,
        'selected_zipcodes': selected_zipcodes
    }

def create_dealer_table(summary_df, raw_df):
    """Create a comprehensive dealer table view"""
    if summary_df is None or raw_df is None:
        return None
    
    # Merge dealer info with sales data
    dealer_info = raw_df.groupby('mc_dealer_id').agg({
        'seller_name': 'first',
        'city': 'first',
        'state': 'first',
        'zip': 'first'
    }).reset_index()
    
    # Merge with sales summary
    dealer_table_data = dealer_info.merge(
        summary_df.groupby('dealer_id')['total_sales'].sum().reset_index(),
        left_on='mc_dealer_id',
        right_on='dealer_id',
        how='left'
    ).fillna(0)
    
    # Add new sales breakdown
    new_sales = summary_df.groupby('dealer_id')['new_sales'].sum()
    dealer_table_data['new_sales'] = dealer_table_data['dealer_id'].map(new_sales).fillna(0)
    
    # Calculate new sales share
    dealer_table_data['new_share'] = (dealer_table_data['new_sales'] / dealer_table_data['total_sales'] * 100).fillna(0)
    
    return dealer_table_data

def create_dealer_summary(dealer_id, summary_df, by_model_df, raw_df, tab_key=""):  # add tab_key for unique keys
    """Create detailed dealer summary section"""
    if summary_df is None or by_model_df is None:
        return
    
    # Get dealer info
    dealer_info = raw_df[raw_df['mc_dealer_id'] == dealer_id].iloc[0] if len(raw_df[raw_df['mc_dealer_id'] == dealer_id]) > 0 else None
    
    if dealer_info is not None:
        st.markdown(f"""
        <div class="dealer-info">
            <h3>🏢 {dealer_info['seller_name']}</h3>
            <p><strong>Address:</strong> {dealer_info['city']}, {dealer_info['state']} {dealer_info['zip']}</p>
            <p><strong>Dealer ID:</strong> {dealer_id}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Get dealer sales data
    dealer_summary = summary_df[summary_df['dealer_id'] == dealer_id]
    dealer_models = by_model_df[by_model_df['dealer_id'] == dealer_id]
    
    if not dealer_summary.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_sales = dealer_summary['total_sales'].sum()
            st.metric("Total Sales", f"{total_sales:,}")
        
        with col2:
            new_sales = dealer_summary['new_sales'].sum()
            st.metric("New Sales", f"{new_sales:,}")
        
        with col3:
            if total_sales > 0:
                new_share = (new_sales / total_sales) * 100
                st.metric("New Share", f"{new_share:.1f}%")
        
        # Sales by period
        st.subheader("📊 Sales by Period")
        period_data = dealer_summary[['period_start', 'period_end', 'total_sales', 'new_sales']].copy()
        
        # Convert period_start to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(period_data['period_start']):
            period_data['period_start'] = pd.to_datetime(period_data['period_start'])
        
        period_data['period'] = period_data['period_start'].dt.strftime('%Y-%m')
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=period_data['period'], y=period_data['total_sales'], name='Total Sales'))
        fig.add_trace(go.Bar(x=period_data['period'], y=period_data['new_sales'], name='New Sales'))
        
        fig.update_layout(
            title="Sales Trend",
            xaxis_title="Period",
            yaxis_title="Sales Count",
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True, key=f"dealer_sales_trend_{dealer_id}_{tab_key}")
        
        # Top models
        if not dealer_models.empty:
            st.subheader("🚗 Top Models")
            top_models = dealer_models.groupby(['make', 'model'])['sales_count'].sum().reset_index().sort_values('sales_count', ascending=False).head(10)
            
            fig = px.bar(
                top_models,
                x='sales_count',
                y='model',
                color='make',
                orientation='h',
                title="Top Models by Sales"
            )
            st.plotly_chart(fig, use_container_width=True, key=f"dealer_top_models_{dealer_id}_{tab_key}")

def create_competitive_analysis(dealer_id, summary_df, by_model_df, raw_df):
    """Create competitive analysis section"""
    if summary_df is None or by_model_df is None:
        return
    
    st.subheader("🎯 Competitive Analysis")
    
    # Get dealer's location
    dealer_location = raw_df[raw_df['mc_dealer_id'] == dealer_id]
    if dealer_location.empty:
        st.warning("Dealer location not found")
        return
    
    dealer_city = dealer_location.iloc[0]['city']
    dealer_state = dealer_location.iloc[0]['state']
    dealer_zip = dealer_location.iloc[0]['zip']
    
    # Find nearby dealers (same city/state for now, can be enhanced with zipcode radius later)
    nearby_dealers = raw_df[
        (raw_df['city'] == dealer_city) & 
        (raw_df['state'] == dealer_state) & 
        (raw_df['mc_dealer_id'] != dealer_id)
    ]['mc_dealer_id'].unique()
    
    if len(nearby_dealers) > 0:
        # Get nearby dealers' sales
        nearby_summary = summary_df[summary_df['dealer_id'].isin(nearby_dealers)]
        
        if not nearby_summary.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏆 Top Competitors")
                competitor_sales = nearby_summary.groupby('dealer_id')['total_sales'].sum().sort_values(ascending=False).head(5)
                
                for i, (comp_id, sales) in enumerate(competitor_sales.items(), 1):
                    comp_info = raw_df[raw_df['mc_dealer_id'] == comp_id].iloc[0]
                    st.metric(
                        f"#{i} {comp_info['seller_name']}",
                        f"{sales:,} sales",
                        f"{comp_info['city']}, {comp_info['state']} {comp_info['zip']}"
                    )
            
            with col2:
                st.subheader("📈 Market Share Analysis")
                total_market_sales = nearby_summary['total_sales'].sum() + summary_df[summary_df['dealer_id'] == dealer_id]['total_sales'].sum()
                dealer_sales = summary_df[summary_df['dealer_id'] == dealer_id]['total_sales'].sum()
                
                if total_market_sales > 0:
                    market_share = (dealer_sales / total_market_sales) * 100
                    st.metric("Your Market Share", f"{market_share:.1f}%")
                    st.metric("Total Market Sales", f"{total_market_sales:,}")
                    st.metric("Your Sales", f"{dealer_sales:,}")
    
    # Future DMA analysis placeholder
    st.subheader("🗺️ DMA Analysis (Coming Soon)")
    st.info(f"""
    **Future Enhancement**: 
    - DMA mapping by zipcode will be implemented
    - Radius-based competitor analysis
    - Geographic market share calculations
    - Current dealer zipcode: {dealer_zip}
    """)

def main():
    st.markdown('<h1 class="main-header">🚗 Dealer Competitive Analysis Dashboard</h1>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner("Loading data..."):
        summary_df, by_model_df, raw_df = load_data()
        
        if summary_df is not None:
            st.session_state.summary_df = summary_df
            st.session_state.by_model_df = by_model_df
            st.session_state.raw_df = raw_df
    
    if summary_df is None:
        st.error("Failed to load data. Please check your data files and database connection.")
        return
    
    # Create filters
    filters = create_filters()
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📋 Dealer Directory", "📊 Dealer Analysis", "🎯 Competitive Insights"])
    
    with tab1:
        st.subheader("📋 Dealer Directory")
        
        # Create dealer table
        dealer_table_data = create_dealer_table(summary_df, raw_df)
        if dealer_table_data is not None:
            # Add filtering options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                min_sales = st.number_input("Min Sales", min_value=0, value=0, key="table_min_sales")
            
            with col2:
                max_sales = st.number_input("Max Sales", min_value=0, value=1000, key="table_max_sales")
            
            with col3:
                selected_state = st.selectbox("State", ["All"] + list(dealer_table_data['state'].unique()), key="table_state")
            
            # Apply filters
            filtered_data = dealer_table_data.copy()
            if min_sales > 0:
                filtered_data = filtered_data[filtered_data['total_sales'] >= min_sales]
            if max_sales < 1000:
                filtered_data = filtered_data[filtered_data['total_sales'] <= max_sales]
            if selected_state != "All":
                filtered_data = filtered_data[filtered_data['state'] == selected_state]
            
            # Display dealer table
            st.dataframe(
                filtered_data[['seller_name', 'city', 'state', 'zip', 'total_sales', 'new_sales', 'new_share']].sort_values('total_sales', ascending=False),
                use_container_width=True,
                height=400
            )
            
            st.info(f"Showing {len(filtered_data)} dealers out of {len(dealer_table_data)} total")
        
        # Dealer selection for detailed analysis
        st.subheader("🔍 Select Dealer for Analysis")
        dealers = summary_df['dealer_id'].unique()
        selected_dealer = st.selectbox("Choose a dealer:", dealers, key="main_selected_dealer")
        
        if selected_dealer:
            create_dealer_summary(selected_dealer, summary_df, by_model_df, raw_df, tab_key="tab1")
    
    with tab2:
        st.info("Please select a dealer from the Dealer Directory tab to view detailed analysis")
    
    with tab3:
        # Only show competitive analysis if a dealer is selected in tab1
        if 'main_selected_dealer' in st.session_state and st.session_state.main_selected_dealer:
            create_competitive_analysis(st.session_state.main_selected_dealer, summary_df, by_model_df, raw_df)
        else:
            st.info("Please select a dealer from the Dealer Directory tab to view competitive analysis")

if __name__ == "__main__":
    main()

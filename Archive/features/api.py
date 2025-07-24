from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import engine
from core.sales import precompute_dealer_stats
from core.loader import load_csv_chunked

app = FastAPI(
    title="Dealer Competitive Analysis API",
    description="API for dealer sales analysis and competitive insights",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_data():
    """Get data from database or fallback to CSV"""
    try:
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
            return summary_df, by_model_df, df
        else:
            raise HTTPException(status_code=404, detail="No data available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Dealer Competitive Analysis API",
        "version": "1.0.0",
        "endpoints": [
            "/dealers",
            "/dealers/{dealer_id}",
            "/dealers/{dealer_id}/summary",
            "/dealers/{dealer_id}/models",
            "/dealers/{dealer_id}/competitors",
            "/market/overview",
            "/market/top-dealers"
        ]
    }

@app.get("/dealers")
async def get_dealers(
    limit: int = Query(100, description="Number of dealers to return"),
    min_sales: int = Query(0, description="Minimum sales filter"),
    max_sales: int = Query(None, description="Maximum sales filter"),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city")
):
    """Get list of dealers with basic info"""
    summary_df, _, raw_df = get_db_data()
    
    # Merge with dealer info
    dealer_info = raw_df.groupby('mc_dealer_id').agg({
        'seller_name': 'first',
        'city': 'first',
        'state': 'first',
        'zip': 'first'
    }).reset_index()
    
    dealer_data = dealer_info.merge(
        summary_df.groupby('dealer_id')['total_sales'].sum().reset_index(),
        left_on='mc_dealer_id',
        right_on='dealer_id',
        how='left'
    ).fillna(0)
    
    # Apply filters
    if min_sales > 0:
        dealer_data = dealer_data[dealer_data['total_sales'] >= min_sales]
    if max_sales:
        dealer_data = dealer_data[dealer_data['total_sales'] <= max_sales]
    if state:
        dealer_data = dealer_data[dealer_data['state'] == state]
    if city:
        dealer_data = dealer_data[dealer_data['city'] == city]
    
    # Sort by sales and limit
    dealer_data = dealer_data.sort_values('total_sales', ascending=False).head(limit)
    
    return {
        "dealers": dealer_data.to_dict('records'),
        "total_count": len(dealer_data)
    }

@app.get("/dealers/{dealer_id}")
async def get_dealer_info(dealer_id: str):
    """Get detailed information for a specific dealer"""
    summary_df, _, raw_df = get_db_data()
    
    # Get dealer info
    dealer_info = raw_df[raw_df['mc_dealer_id'] == int(dealer_id)]
    if dealer_info.empty:
        raise HTTPException(status_code=404, detail="Dealer not found")
    
    dealer_data = dealer_info.iloc[0]
    
    # Get sales summary
    dealer_summary = summary_df[summary_df['dealer_id'] == int(dealer_id)]
    
    return {
        "dealer_id": dealer_id,
        "name": dealer_data['seller_name'],
        "address": f"{dealer_data['city']}, {dealer_data['state']} {dealer_data['zip']}",
        "city": dealer_data['city'],
        "state": dealer_data['state'],
        "zip": dealer_data['zip'],
        "total_sales": dealer_summary['total_sales'].sum() if not dealer_summary.empty else 0,
        "new_sales": dealer_summary['new_sales'].sum() if not dealer_summary.empty else 0,
        "used_sales": dealer_summary['used_sales'].sum() if not dealer_summary.empty else 0,
        "sales_by_period": dealer_summary.to_dict('records') if not dealer_summary.empty else []
    }

@app.get("/dealers/{dealer_id}/summary")
async def get_dealer_summary(
    dealer_id: str,
    period_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    period_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get sales summary for a dealer with optional date filtering"""
    summary_df, _, raw_df = get_db_data()
    
    dealer_summary = summary_df[summary_df['dealer_id'] == int(dealer_id)]
    if dealer_summary.empty:
        raise HTTPException(status_code=404, detail="Dealer not found")
    
    # Apply date filters
    if period_start:
        dealer_summary = dealer_summary[dealer_summary['period_start'] >= period_start]
    if period_end:
        dealer_summary = dealer_summary[dealer_summary['period_end'] <= period_end]
    
    total_sales = dealer_summary['total_sales'].sum()
    new_sales = dealer_summary['new_sales'].sum()
    used_sales = dealer_summary['used_sales'].sum()
    
    return {
        "dealer_id": dealer_id,
        "total_sales": total_sales,
        "new_sales": new_sales,
        "used_sales": used_sales,
        "new_share": (new_sales / total_sales * 100) if total_sales > 0 else 0,
        "used_share": (used_sales / total_sales * 100) if total_sales > 0 else 0,
        "periods": dealer_summary.to_dict('records')
    }

@app.get("/dealers/{dealer_id}/models")
async def get_dealer_models(
    dealer_id: str,
    limit: int = Query(10, description="Number of top models to return")
):
    """Get top models for a dealer"""
    _, by_model_df, _ = get_db_data()
    
    dealer_models = by_model_df[by_model_df['dealer_id'] == int(dealer_id)]
    if dealer_models.empty:
        raise HTTPException(status_code=404, detail="No model data found for dealer")
    
    # Aggregate by make and model
    top_models = dealer_models.groupby(['make', 'model'])['sales_count'].sum().reset_index()
    top_models = top_models.sort_values('sales_count', ascending=False).head(limit)
    
    return {
        "dealer_id": dealer_id,
        "models": top_models.to_dict('records')
    }

@app.get("/dealers/{dealer_id}/competitors")
async def get_dealer_competitors(
    dealer_id: str,
    radius_miles: int = Query(50, description="Radius in miles for competitor search"),
    limit: int = Query(10, description="Number of competitors to return")
):
    """Get competitive analysis for a dealer"""
    summary_df, _, raw_df = get_db_data()
    
    # Get dealer location
    dealer_location = raw_df[raw_df['mc_dealer_id'] == int(dealer_id)]
    if dealer_location.empty:
        raise HTTPException(status_code=404, detail="Dealer not found")
    
    dealer_city = dealer_location.iloc[0]['city']
    dealer_state = dealer_location.iloc[0]['state']
    
    # Find nearby dealers (same city/state for now, can be enhanced with lat/lng)
    nearby_dealers = raw_df[
        (raw_df['city'] == dealer_city) & 
        (raw_df['state'] == dealer_state) & 
        (raw_df['mc_dealer_id'] != int(dealer_id))
    ]['mc_dealer_id'].unique()
    
    if len(nearby_dealers) == 0:
        return {
            "dealer_id": dealer_id,
            "competitors": [],
            "market_share": 100.0,
            "total_market_sales": 0
        }
    
    # Get competitor sales
    competitor_summary = summary_df[summary_df['dealer_id'].isin(nearby_dealers)]
    dealer_sales = summary_df[summary_df['dealer_id'] == int(dealer_id)]['total_sales'].sum()
    
    # Calculate market share
    total_market_sales = competitor_summary['total_sales'].sum() + dealer_sales
    market_share = (dealer_sales / total_market_sales * 100) if total_market_sales > 0 else 100
    
    # Get top competitors
    top_competitors = competitor_summary.groupby('dealer_id')['total_sales'].sum().sort_values(ascending=False).head(limit)
    
    competitors = []
    for comp_id, sales in top_competitors.items():
        comp_info = raw_df[raw_df['mc_dealer_id'] == comp_id].iloc[0]
        competitors.append({
            "dealer_id": comp_id,
            "name": comp_info['seller_name'],
            "address": f"{comp_info['city']}, {comp_info['state']} {comp_info['zip']}",
            "total_sales": int(sales),
            "distance": "Same city"  # Placeholder for future lat/lng calculation
        })
    
    return {
        "dealer_id": dealer_id,
        "competitors": competitors,
        "market_share": round(market_share, 2),
        "total_market_sales": int(total_market_sales),
        "your_sales": int(dealer_sales)
    }

@app.get("/market/overview")
async def get_market_overview(
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city")
):
    """Get market overview statistics"""
    summary_df, _, raw_df = get_db_data()
    
    # Apply location filters
    if state or city:
        location_filter = raw_df.copy()
        if state:
            location_filter = location_filter[location_filter['state'] == state]
        if city:
            location_filter = location_filter[location_filter['city'] == city]
        
        dealer_ids = location_filter['mc_dealer_id'].unique()
        summary_df = summary_df[summary_df['dealer_id'].isin(dealer_ids)]
    
    total_sales = summary_df['total_sales'].sum()
    total_new_sales = summary_df['new_sales'].sum()
    total_used_sales = summary_df['used_sales'].sum()
    total_dealers = summary_df['dealer_id'].nunique()
    
    return {
        "total_sales": int(total_sales),
        "total_new_sales": int(total_new_sales),
        "total_used_sales": int(total_used_sales),
        "total_dealers": int(total_dealers),
        "avg_sales_per_dealer": round(total_sales / total_dealers, 2) if total_dealers > 0 else 0,
        "new_share": round(total_new_sales / total_sales * 100, 2) if total_sales > 0 else 0,
        "used_share": round(total_used_sales / total_sales * 100, 2) if total_sales > 0 else 0
    }

@app.get("/market/top-dealers")
async def get_top_dealers(
    limit: int = Query(20, description="Number of top dealers to return"),
    by_sales_type: str = Query("total", description="Rank by: total, new, used")
):
    """Get top dealers by sales"""
    summary_df, _, raw_df = get_db_data()
    
    # Aggregate dealer sales
    if by_sales_type == "new":
        dealer_ranking = summary_df.groupby('dealer_id')['new_sales'].sum()
    elif by_sales_type == "used":
        dealer_ranking = summary_df.groupby('dealer_id')['used_sales'].sum()
    else:
        dealer_ranking = summary_df.groupby('dealer_id')['total_sales'].sum()
    
    top_dealers = dealer_ranking.sort_values(ascending=False).head(limit)
    
    # Get dealer info
    dealer_info = raw_df.groupby('mc_dealer_id').agg({
        'seller_name': 'first',
        'city': 'first',
        'state': 'first'
    }).reset_index()
    
    result = []
    for dealer_id, sales in top_dealers.items():
        dealer_data = dealer_info[dealer_info['mc_dealer_id'] == int(dealer_id)]
        if not dealer_data.empty:
            result.append({
                "dealer_id": dealer_id,
                "name": dealer_data.iloc[0]['seller_name'],
                "location": f"{dealer_data.iloc[0]['city']}, {dealer_data.iloc[0]['state']}",
                "sales": int(sales)
            })
    
    return {
        "ranking_by": by_sales_type,
        "top_dealers": result
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

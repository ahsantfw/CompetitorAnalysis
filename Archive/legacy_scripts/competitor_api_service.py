#!/usr/bin/env python3
"""
Competitor Analysis REST API Service
===================================

FastAPI service to expose competitor analysis functionality to C# backend.
Designed for Windows Server deployment with C# integration.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
import json
import os
import asyncio
import uuid
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Import your existing analysis modules
from competitor_analysis import CompetitorAnalyzer
from Archive.get_data import MarketCheckAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Competitor Analysis API",
    description="REST API for automotive competitor analysis integration with C# backend",
    version="1.0.0"
)

# Data models for API requests
class AnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    radius_miles: int = 25
    dealership_name: str = "Your Dealership"
    max_results: int = 1000
    use_live_data: bool = False
    filters: Optional[Dict[str, Any]] = None

class CompetitorFilter(BaseModel):
    makes: Optional[List[str]] = None
    models: Optional[List[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None

class AnalysisStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int
    message: str
    started_at: datetime
    completed_at: Optional[datetime] = None

# Global storage for analysis jobs
analysis_jobs = {}
results_cache = {}

# Initialize analyzer
analyzer = CompetitorAnalyzer()

@app.get("/")
async def root():
    """API health check endpoint."""
    return {
        "message": "Competitor Analysis API is running",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in analysis_jobs.values() if j.status in ["pending", "running"]]),
        "completed_jobs": len([j for j in analysis_jobs.values() if j.status == "completed"]),
        "cache_size": len(results_cache)
    }

@app.post("/analysis/start")
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start a new competitor analysis job."""
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job status
    job_status = AnalysisStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        message="Analysis job queued",
        started_at=datetime.now()
    )
    
    analysis_jobs[job_id] = job_status
    
    # Start analysis in background
    background_tasks.add_task(run_analysis, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "Analysis job started in background",
        "check_status_url": f"/analysis/status/{job_id}",
        "estimated_duration": "2-5 minutes"
    }

@app.get("/analysis/status/{job_id}")
async def get_analysis_status(job_id: str):
    """Get the status of an analysis job."""
    
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = analysis_jobs[job_id]
    
    response = {
        "job_id": job_id,
        "status": job_status.status,
        "progress": job_status.progress,
        "message": job_status.message,
        "started_at": job_status.started_at.isoformat(),
    }
    
    if job_status.completed_at:
        response["completed_at"] = job_status.completed_at.isoformat()
        response["duration_seconds"] = (job_status.completed_at - job_status.started_at).total_seconds()
    
    if job_status.status == "completed":
        response["results_url"] = f"/analysis/results/{job_id}"
        response["download_urls"] = {
            "csv": f"/analysis/download/{job_id}/csv",
            "excel": f"/analysis/download/{job_id}/excel",
            "json": f"/analysis/download/{job_id}/json"
        }
    
    return response

@app.get("/analysis/results/{job_id}")
async def get_analysis_results(job_id: str):
    """Get the results of a completed analysis job."""
    
    if job_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = analysis_jobs[job_id]
    
    if job_status.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job status is {job_status.status}, not completed")
    
    if job_id not in results_cache:
        raise HTTPException(status_code=404, detail="Results not found in cache")
    
    return results_cache[job_id]

@app.get("/analysis/download/{job_id}/{format}")
async def download_analysis_results(job_id: str, format: str):
    """Download analysis results in specified format."""
    
    if job_id not in analysis_jobs or analysis_jobs[job_id].status != "completed":
        raise HTTPException(status_code=404, detail="Job not found or not completed")
    
    if job_id not in results_cache:
        raise HTTPException(status_code=404, detail="Results not found")
    
    results = results_cache[job_id]
    filename_base = f"competitor_analysis_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format.lower() == "csv":
        # Convert to CSV
        df = pd.DataFrame(results['competitors'])
        filepath = f"temp/{filename_base}.csv"
        os.makedirs("temp", exist_ok=True)
        df.to_csv(filepath, index=False)
        return FileResponse(filepath, filename=f"{filename_base}.csv", media_type="text/csv")
    
    elif format.lower() == "excel":
        # Convert to Excel with multiple sheets
        filepath = f"temp/{filename_base}.xlsx"
        os.makedirs("temp", exist_ok=True)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            pd.DataFrame(results['competitors']).to_sheet(writer, sheet_name='Competitors', index=False)
            pd.DataFrame(results['summary']['dealers']).to_sheet(writer, sheet_name='Dealers', index=False)
            pd.DataFrame(results['summary']['brands']).to_sheet(writer, sheet_name='Brands', index=False)
        
        return FileResponse(filepath, filename=f"{filename_base}.xlsx", 
                          media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    elif format.lower() == "json":
        # Return as JSON file
        filepath = f"temp/{filename_base}.json"
        os.makedirs("temp", exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return FileResponse(filepath, filename=f"{filename_base}.json", media_type="application/json")
    
    else:
        raise HTTPException(status_code=400, detail="Format must be csv, excel, or json")

@app.get("/analysis/quick")
async def quick_analysis(
    latitude: float = Query(..., description="Latitude of target location"),
    longitude: float = Query(..., description="Longitude of target location"),
    radius: int = Query(25, description="Search radius in miles"),
    dealership_name: str = Query("Your Dealership", description="Name of your dealership")
):
    """Perform a quick synchronous analysis for small datasets."""
    
    try:
        # Load sample data for quick analysis
        sample_files = [
            "data/all_sales_data.xlsx",
            "sample_data/mc_us_used_sample.csv",
            "sample_data/mc_us_new_sample.csv"
        ]
        
        data_file = None
        for file in sample_files:
            if os.path.exists(file):
                data_file = file
                break
        
        if not data_file:
            raise HTTPException(status_code=404, detail="No data file found for analysis")
        
        # Run quick analysis
        analyzer.load_data(file_path=data_file)
        analyzer.set_target_location(latitude, longitude, dealership_name)
        
        analysis, competitors = analyzer.analyze_competitor_inventory(radius)
        
        # Format results
        results = {
            "analysis_summary": analysis,
            "competitor_count": len(competitors),
            "competitors": competitors.to_dict('records') if not competitors.empty else [],
            "generated_at": datetime.now().isoformat(),
            "parameters": {
                "latitude": latitude,
                "longitude": longitude,
                "radius": radius,
                "dealership_name": dealership_name
            }
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/data/status")
async def get_data_status():
    """Get status of available data files."""
    
    data_files = {
        "sales_data": [],
        "sample_data": [],
        "saved_api_data": []
    }
    
    # Check for sales data files
    if os.path.exists("data"):
        for file in os.listdir("data"):
            if file.endswith(('.json', '.xlsx', '.csv')):
                data_files["sales_data"].append({
                    "filename": file,
                    "size_mb": round(os.path.getsize(f"data/{file}") / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(os.path.getmtime(f"data/{file}")).isoformat()
                })
    
    # Check for sample data
    if os.path.exists("sample_data"):
        for file in os.listdir("sample_data"):
            if file.endswith(('.csv', '.json', '.xlsx')):
                data_files["sample_data"].append({
                    "filename": file,
                    "size_mb": round(os.path.getsize(f"sample_data/{file}") / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(os.path.getmtime(f"sample_data/{file}")).isoformat()
                })
    
    return {
        "data_files": data_files,
        "total_files": sum(len(files) for files in data_files.values()),
        "timestamp": datetime.now().isoformat()
    }

@app.delete("/analysis/cleanup")
async def cleanup_old_jobs():
    """Clean up old completed jobs and temporary files."""
    
    cutoff_time = datetime.now() - timedelta(hours=24)  # Keep jobs for 24 hours
    
    cleaned_jobs = 0
    cleaned_results = 0
    
    # Clean old jobs
    jobs_to_remove = []
    for job_id, job_status in analysis_jobs.items():
        if job_status.completed_at and job_status.completed_at < cutoff_time:
            jobs_to_remove.append(job_id)
    
    for job_id in jobs_to_remove:
        del analysis_jobs[job_id]
        if job_id in results_cache:
            del results_cache[job_id]
            cleaned_results += 1
        cleaned_jobs += 1
    
    # Clean temporary files
    if os.path.exists("temp"):
        for file in os.listdir("temp"):
            file_path = f"temp/{file}"
            if os.path.getmtime(file_path) < cutoff_time.timestamp():
                os.remove(file_path)
    
    return {
        "cleaned_jobs": cleaned_jobs,
        "cleaned_results": cleaned_results,
        "active_jobs": len(analysis_jobs),
        "cache_size": len(results_cache)
    }

async def run_analysis(job_id: str, request: AnalysisRequest):
    """Background task to run competitor analysis."""
    
    try:
        # Update job status
        analysis_jobs[job_id].status = "running"
        analysis_jobs[job_id].progress = 10
        analysis_jobs[job_id].message = "Loading data..."
        
        # Determine data source
        if request.use_live_data:
            # Use live API data
            api = MarketCheckAPI()
            analysis_jobs[job_id].progress = 20
            analysis_jobs[job_id].message = "Fetching live data from API..."
            
            # Get live inventory data
            inventory_data = api.get_all_inventory_in_radius(
                request.latitude, 
                request.longitude, 
                request.radius_miles,
                max_results=request.max_results
            )
            
            if inventory_data.empty:
                raise Exception("No live data available")
                
            # Save to temporary file for analysis
            temp_file = f"temp/live_data_{job_id}.csv"
            os.makedirs("temp", exist_ok=True)
            inventory_data.to_csv(temp_file, index=False)
            data_file = temp_file
        else:
            # Use existing data files
            analysis_jobs[job_id].message = "Using existing data files..."
            data_file = "data/all_sales_data.xlsx" if os.path.exists("data/all_sales_data.xlsx") else "sample_data/mc_us_used_sample.csv"
        
        # Load data into analyzer
        analysis_jobs[job_id].progress = 40
        analysis_jobs[job_id].message = "Loading data into analyzer..."
        
        analyzer.load_data(file_path=data_file)
        analyzer.set_target_location(request.latitude, request.longitude, request.dealership_name)
        
        # Run analysis
        analysis_jobs[job_id].progress = 60
        analysis_jobs[job_id].message = "Running competitor analysis..."
        
        analysis, competitors = analyzer.analyze_competitor_inventory(request.radius_miles)
        
        # Generate additional insights
        analysis_jobs[job_id].progress = 80
        analysis_jobs[job_id].message = "Generating insights and summaries..."
        
        # Create comprehensive results
        results = {
            "job_id": job_id,
            "analysis_summary": analysis,
            "competitors": competitors.to_dict('records') if not competitors.empty else [],
            "summary": {
                "total_competitors": len(competitors),
                "total_vehicles": len(competitors) if not competitors.empty else 0,
                "average_price": competitors['price'].mean() if not competitors.empty and 'price' in competitors.columns else 0,
                "price_range": {
                    "min": competitors['price'].min() if not competitors.empty and 'price' in competitors.columns else 0,
                    "max": competitors['price'].max() if not competitors.empty and 'price' in competitors.columns else 0
                },
                "dealers": analyzer.get_dealer_summary() if hasattr(analyzer, 'get_dealer_summary') else {},
                "brands": analyzer.get_brand_summary() if hasattr(analyzer, 'get_brand_summary') else {}
            },
            "parameters": {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius_miles": request.radius_miles,
                "dealership_name": request.dealership_name,
                "use_live_data": request.use_live_data,
                "max_results": request.max_results
            },
            "generated_at": datetime.now().isoformat(),
            "data_source": "live_api" if request.use_live_data else "cached_data"
        }
        
        # Store results
        results_cache[job_id] = results
        
        # Update job status to completed
        analysis_jobs[job_id].status = "completed"
        analysis_jobs[job_id].progress = 100
        analysis_jobs[job_id].message = "Analysis completed successfully"
        analysis_jobs[job_id].completed_at = datetime.now()
        
        logger.info(f"Analysis job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {e}")
        
        # Update job status to failed
        analysis_jobs[job_id].status = "failed"
        analysis_jobs[job_id].message = f"Analysis failed: {str(e)}"
        analysis_jobs[job_id].completed_at = datetime.now()

if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "competitor_api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
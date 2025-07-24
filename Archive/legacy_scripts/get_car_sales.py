#!/usr/bin/env python3
"""
Simple Car Sales Data Pipeline
=============================

Gets 100% raw sales data from MarketCheck /v2/sales/car endpoint 
and saves as raw JSON files with NO processing.
"""

import requests
import os
import json
from dotenv import load_dotenv
import time
import pandas as pd

# Load environment variables from .env file
load_dotenv()

def get_raw_sales_data(api_key, make):
    """Get 100% raw sales data for a specific make."""
    
    url = "https://mc-api.marketcheck.com/v2/sales/car"
    
    headers = {
        'Host': 'mc-api.marketcheck.com'
    }
    
    params = {
        'api_key': api_key,
        'make': make,
        'geography': 'national'
    }
    
    print(f"🔍 Getting raw data for {make}...")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
  
            print("✅ Successfully retrieved sales data")
            print(f"📊 Response keys: {list(data.keys())}")
            with open(f"data/{make}_sales_data.json", "w") as f:
                json.dump(data, f, indent=2)
            df = pd.DataFrame(data)
            df.to_excel(f"data/{make}_sales_data.xlsx", index=False)
            return data
        else:
            print(f"❌ API Error for {make}: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error for {make}: {e}")
        return None

def main():
    """Main function - get raw data and save as JSON."""
    
    print("🚗 GETTING 100% RAW SALES DATA")
    print("=" * 40)
    
    # Get API key from environment
    api_key = os.getenv('MARKETCHECK_API_KEY')
    
    if not api_key:
        print("❌ MARKETCHECK_API_KEY not found in environment")
        return
    
    # List of car makes
    makes = ['Toyota', 'Honda', 'Ford', 'Chevrolet']
    
    all_raw_data = {}
    
    for i, make in enumerate(makes, 1):
        # Get 100% raw data
        raw_data = get_raw_sales_data(api_key, make)
        
        if raw_data:
            # Save individual raw JSON file for each make
            filename = f"data/raw_{make.lower()}_sales.json"
            with open(filename, 'w') as f:
                json.dump(raw_data, f, indent=2)
            print(f"💾 Saved: {filename}")
            
            # Add to combined data
            all_raw_data[make] = raw_data
        
        # Small delay
        if i < len(makes):
            time.sleep(0.1)
        
        print(f"Progress: {i}/{len(makes)}")
    
    # Save combined raw data
    if all_raw_data:
        combined_filename = "data/all_raw_sales_data.json"
        with open(combined_filename, 'w') as f:
            json.dump(all_raw_data, f, indent=2)
        df = pd.DataFrame(all_raw_data)
        df.to_excel(f"data/all_sales_data.xlsx", index=False)
        
        print(f"\n✅ SUCCESS!")
        print(f"📁 Individual files: {len(all_raw_data)} JSON files in data/")
        print(f"📦 Combined file: {combined_filename}")
        print(f"🚫 NO processing - 100% raw API responses")
    else:
        print("❌ No data collected")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
API Data Management System
=========================

This script helps you organize, save, and work with MarketCheck API data
without wasting precious API calls. It creates a structured data archive
and provides tools to analyze saved data.
"""

import json
import pandas as pd
import os
from datetime import datetime
import shutil
from typing import Dict, List, Any

class APIDataManager:
    """Manage and organize MarketCheck API data efficiently."""
    
    def __init__(self, data_dir: str = "saved_api_data"):
        """
        Initialize API Data Manager.
        
        Args:
            data_dir (str): Directory to store organized API data
        """
        self.data_dir = data_dir
        self.create_data_structure()
    
    def create_data_structure(self):
        """Create organized directory structure for API data."""
        directories = [
            self.data_dir,
            f"{self.data_dir}/sales_statistics",
            f"{self.data_dir}/inventory_data", 
            f"{self.data_dir}/pricing_data",
            f"{self.data_dir}/dealer_data",
            f"{self.data_dir}/market_analysis",
            f"{self.data_dir}/daily_snapshots",
            f"{self.data_dir}/exports"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print(f"✅ Created organized data structure in {self.data_dir}/")
    
    def organize_existing_api_data(self):
        """Organize all existing API data files into proper structure."""
        
        print("\n📁 ORGANIZING EXISTING API DATA")
        print("=" * 50)
        
        # Map of current files to their organized locations
        file_mappings = {
            # Sales Statistics Files
            'toyota_sales_national.json': 'sales_statistics/toyota_national.json',
            'honda_accord_ny_sales.json': 'sales_statistics/honda_accord_ny.json', 
            'camry_2023_sales.json': 'sales_statistics/toyota_camry_2023_national.json',
            'multi_brand_sales_comparison.json': 'sales_statistics/multi_brand_national_comparison.json',
            'local_market_sales_20250620_161655.json': 'sales_statistics/ny_state_multi_brand.json',
            'sales_dashboard_data_20250620_161700.json': 'market_analysis/comprehensive_dashboard_data.json'
        }
        
        moved_files = []
        
        for current_file, new_location in file_mappings.items():
            if os.path.exists(current_file):
                destination = os.path.join(self.data_dir, new_location)
                shutil.copy2(current_file, destination)
                moved_files.append((current_file, new_location))
                print(f"📋 Copied: {current_file} → {new_location}")
        
        # Create master inventory file
        self.create_data_inventory()
        
        print(f"\n✅ Organized {len(moved_files)} API data files")
        return moved_files
    
    def create_data_inventory(self):
        """Create comprehensive inventory of all saved API data."""
        
        inventory = {
            'created_at': datetime.now().isoformat(),
            'total_api_calls_saved': 0,
            'data_sources': {
                'sales_statistics': {},
                'inventory_data': {},
                'pricing_data': {},
                'dealer_data': {},
                'market_analysis': {}
            },
            'geographic_coverage': [],
            'brands_analyzed': [],
            'models_analyzed': [],
            'time_periods': []
        }
        
        # Analyze sales statistics data
        sales_dir = f"{self.data_dir}/sales_statistics"
        if os.path.exists(sales_dir):
            for file in os.listdir(sales_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(sales_dir, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        inventory['data_sources']['sales_statistics'][file] = {
                            'file_size_kb': round(os.path.getsize(file_path) / 1024, 1),
                            'make': data.get('make', 'Unknown'),
                            'model': data.get('model', 'All Models'),
                            'year': data.get('year', 'All Years'),
                            'geography': data.get('state', data.get('geography', 'National')),
                            'sales_count': data.get('count', 0),
                            'api_calls_saved': 1
                        }
                        
                        inventory['total_api_calls_saved'] += 1
                        
                        # Add to coverage tracking
                        if data.get('make'):
                            inventory['brands_analyzed'].append(data['make'])
                        if data.get('model'):
                            inventory['models_analyzed'].append(f"{data.get('make', '')} {data['model']}")
                        
                    except Exception as e:
                        print(f"⚠️ Error reading {file}: {e}")
        
        # Remove duplicates
        inventory['brands_analyzed'] = list(set(inventory['brands_analyzed']))
        inventory['models_analyzed'] = list(set(inventory['models_analyzed']))
        
        # Save inventory
        inventory_file = f"{self.data_dir}/data_inventory.json"
        with open(inventory_file, 'w') as f:
            json.dump(inventory, f, indent=2)
        
        print(f"📊 Created data inventory: {inventory['total_api_calls_saved']} API calls saved")
        return inventory
    
    def create_sales_summary_report(self):
        """Create comprehensive summary report from saved sales data."""
        
        print("\n📈 CREATING SALES SUMMARY REPORT")
        print("=" * 50)
        
        summary_data = []
        sales_dir = f"{self.data_dir}/sales_statistics"
        
        if os.path.exists(sales_dir):
            for file in os.listdir(sales_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(sales_dir, file)
                    
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Extract key metrics
                        summary_row = {
                            'Data_Source': file.replace('.json', ''),
                            'Make': data.get('make', 'Unknown'),
                            'Model': data.get('model', 'All Models'),
                            'Year': data.get('year', 'All Years'),
                            'Geography': data.get('state', 'National'),
                            'Total_Sales': data.get('count', 0),
                            'CPO_Sales': data.get('cpo', 0),
                            'Non_CPO_Sales': data.get('non_cpo', 0),
                            'Avg_Price': data.get('price_stats', {}).get('mean', 0),
                            'Median_Price': data.get('price_stats', {}).get('median', 0),
                            'Avg_Days_On_Market': data.get('dom_stats', {}).get('mean', 0),
                            'Avg_Mileage': data.get('miles_stats', {}).get('mean', 0),
                            'CPO_Penetration_%': round((data.get('cpo', 0) / max(data.get('count', 1), 1)) * 100, 1)
                        }
                        
                        summary_data.append(summary_row)
                        
                    except Exception as e:
                        print(f"⚠️ Error processing {file}: {e}")
        
        # Create DataFrame and save
        if summary_data:
            df = pd.DataFrame(summary_data)
            
            # Sort by total sales
            df = df.sort_values('Total_Sales', ascending=False)
            
            # Save to CSV
            csv_file = f"{self.data_dir}/exports/sales_summary_report.csv"
            df.to_csv(csv_file, index=False)
            
            print(f"✅ Sales summary saved to: {csv_file}")
            print(f"📊 Analyzed {len(summary_data)} data sources")
            
            # Display top insights
            print("\n🏆 TOP SALES INSIGHTS:")
            print("-" * 30)
            for idx, row in df.head(5).iterrows():
                print(f"{idx+1}. {row['Make']} {row['Model']}: {row['Total_Sales']:,} sales")
            
            return df
        else:
            print("❌ No sales data found to summarize")
            return pd.DataFrame()
    
    def create_competitive_analysis_dataset(self):
        """Create a consolidated dataset for competitive analysis."""
        
        print("\n🎯 CREATING COMPETITIVE ANALYSIS DATASET")
        print("=" * 50)
        
        # Load multi-brand comparison data
        comparison_file = f"{self.data_dir}/sales_statistics/multi_brand_national_comparison.json"
        
        if os.path.exists(comparison_file):
            with open(comparison_file, 'r') as f:
                brand_data = json.load(f)
            
            competitive_metrics = []
            
            for brand, data in brand_data.items():
                if isinstance(data, dict) and 'count' in data:
                    metrics = {
                        'Brand': brand,
                        'Market_Share_Volume': data.get('count', 0),
                        'Avg_Selling_Price': data.get('price_stats', {}).get('mean', 0),
                        'Median_Price': data.get('price_stats', {}).get('median', 0),
                        'Price_Range_Low': data.get('price_stats', {}).get('min', 0),
                        'Price_Range_High': data.get('price_stats', {}).get('max', 0),
                        'Avg_Days_On_Market': data.get('dom_stats', {}).get('mean', 0),
                        'Inventory_Turnover_Rate': round(365 / max(data.get('dom_stats', {}).get('mean', 1), 1), 2),
                        'CPO_Penetration_%': round((data.get('cpo', 0) / max(data.get('count', 1), 1)) * 100, 1),
                        'Avg_Vehicle_Age_Miles': data.get('miles_stats', {}).get('mean', 0),
                        'Price_Volatility': data.get('price_stats', {}).get('standard_deviation', 0)
                    }
                    competitive_metrics.append(metrics)
            
            if competitive_metrics:
                df = pd.DataFrame(competitive_metrics)
                
                # Calculate market share percentages
                total_volume = df['Market_Share_Volume'].sum()
                df['Market_Share_%'] = round((df['Market_Share_Volume'] / total_volume) * 100, 1)
                
                # Rank brands
                df = df.sort_values('Market_Share_Volume', ascending=False)
                df['Market_Rank'] = range(1, len(df) + 1)
                
                # Save competitive analysis
                csv_file = f"{self.data_dir}/exports/competitive_analysis_dataset.csv"
                df.to_csv(csv_file, index=False)
                
                print(f"✅ Competitive analysis saved to: {csv_file}")
                print(f"📊 Analyzed {len(competitive_metrics)} competing brands")
                
                # Show competitive ranking
                print("\n🏆 BRAND COMPETITIVE RANKING:")
                print("-" * 40)
                for idx, row in df.iterrows():
                    print(f"{row['Market_Rank']}. {row['Brand']}: {row['Market_Share_%']}% market share")
                
                return df
        
        print("❌ No multi-brand comparison data found")
        return pd.DataFrame()
    
    def export_data_for_analysis(self):
        """Export all data in formats ready for analysis tools."""
        
        print("\n📤 EXPORTING DATA FOR ANALYSIS")
        print("=" * 50)
        
        exports = []
        
        # 1. Sales Summary Report
        sales_df = self.create_sales_summary_report()
        if not sales_df.empty:
            exports.append("Sales Summary Report")
        
        # 2. Competitive Analysis Dataset  
        comp_df = self.create_competitive_analysis_dataset()
        if not comp_df.empty:
            exports.append("Competitive Analysis Dataset")
        
        # 3. Create master data file
        master_data = {
            'export_timestamp': datetime.now().isoformat(),
            'data_sources_included': exports,
            'api_calls_preserved': self.count_saved_api_calls()
        }
        
        master_file = f"{self.data_dir}/exports/master_data_export.json"
        with open(master_file, 'w') as f:
            json.dump(master_data, f, indent=2)
        
        print(f"\n✅ Exported {len(exports)} analysis-ready datasets")
        print(f"💰 Preserved API calls: {master_data['api_calls_preserved']}")
        
        return exports
    
    def count_saved_api_calls(self):
        """Count how many API calls we've saved by organizing data."""
        
        count = 0
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith('.json') and 'inventory' not in file:
                    count += 1
        
        return count
    
    def show_data_summary(self):
        """Display comprehensive summary of saved data."""
        
        print("\n" + "="*60)
        print("📊 SAVED API DATA SUMMARY")
        print("="*60)
        
        inventory_file = f"{self.data_dir}/data_inventory.json"
        
        if os.path.exists(inventory_file):
            with open(inventory_file, 'r') as f:
                inventory = json.load(f)
            
            print(f"💰 API Calls Saved: {inventory['total_api_calls_saved']}")
            print(f"🏢 Brands Analyzed: {len(inventory['brands_analyzed'])}")
            print(f"🚗 Models Analyzed: {len(inventory['models_analyzed'])}")
            
            print(f"\n📋 Brands: {', '.join(inventory['brands_analyzed'])}")
            
            print(f"\n📁 Data Organization:")
            for category, files in inventory['data_sources'].items():
                if files:
                    print(f"  {category}: {len(files)} files")
        
        # Show export files
        exports_dir = f"{self.data_dir}/exports"
        if os.path.exists(exports_dir):
            export_files = [f for f in os.listdir(exports_dir) if f.endswith('.csv')]
            print(f"\n📤 Ready-to-Use Exports: {len(export_files)}")
            for file in export_files:
                print(f"  ✅ {file}")

def main():
    """Main function to organize and save API data."""
    
    print("🚀 MARKETCHECK API DATA MANAGEMENT SYSTEM")
    print("=" * 60)
    
    # Initialize data manager
    manager = APIDataManager()
    
    # Organize existing data
    moved_files = manager.organize_existing_api_data()
    
    # Create analysis exports
    exports = manager.export_data_for_analysis()
    
    # Show summary
    manager.show_data_summary()
    
    print("\n" + "="*60)
    print("🎉 API DATA SUCCESSFULLY ORGANIZED & SAVED!")
    print("="*60)
    
    print("\n🎯 NEXT STEPS:")
    print("1. Use saved_api_data/exports/ files for analysis")
    print("2. Work with organized data without making new API calls")
    print("3. Run competitive analysis on saved datasets")
    print("4. Preserve API quota for new data collection when needed")
    
    print(f"\n💡 TIP: You now have {manager.count_saved_api_calls()} API calls worth of data saved!")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3

import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime
import math

class SimpleCompetitorAnalyzer:
    def __init__(self):
        self.data = None
        self.target_location = None
        self.radius_miles = 15
        
    def load_data(self, file_path=None, data_type='used'):
        """Load vehicle data from CSV files"""
        if file_path is None:
            file_path = f'sample_data/mc_us_{data_type}_sample.csv'
        
        try:
            # Load data with low_memory=False to avoid mixed types warning
            self.data = pd.read_csv(file_path, low_memory=False)
            print(f"✅ Loaded {len(self.data)} records from {data_type} data")
            return True
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def set_target_location(self, latitude, longitude, dealership_name="Your Dealership"):
        """Set the target dealership location for comparison"""
        self.target_location = {
            'lat': latitude,
            'lon': longitude,
            'name': dealership_name
        }
        print(f"🎯 Target location set: {dealership_name} at ({latitude}, {longitude})")
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula"""
        try:
            # Convert to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            r = 3956  # Radius of Earth in miles
            
            return c * r
        except:
            return float('inf')
    
    def filter_by_radius(self, radius_miles=15):
        """Filter competitors within specified radius"""
        if self.target_location is None:
            print("❌ Target location not set. Use set_target_location() first.")
            return None
            
        self.radius_miles = radius_miles
        
        # Clean coordinate data
        df = self.data.copy()
        df = df.dropna(subset=['latitude', 'longitude'])
        
        # Calculate distances
        target_lat = self.target_location['lat']
        target_lon = self.target_location['lon']
        
        def calc_dist(row):
            return self.calculate_distance(target_lat, target_lon, row['latitude'], row['longitude'])
        
        df['distance_miles'] = df.apply(calc_dist, axis=1)
        
        # Filter by radius
        competitors = df[df['distance_miles'] <= radius_miles].copy()
        
        print(f"🔍 Found {len(competitors)} vehicles from competitors within {radius_miles} miles")
        return competitors
    
    def analyze_competitor_inventory(self, radius_miles=15):
        """Analyze competitor inventory within radius"""
        competitors = self.filter_by_radius(radius_miles)
        if competitors is None or len(competitors) == 0:
            return None, None
            
        analysis = {}
        
        # Dealer analysis
        dealer_summary = competitors.groupby('seller_name').agg({
            'id': 'count',
            'price': ['mean', 'median', 'min', 'max'],
            'miles': 'mean',
            'distance_miles': 'min',
            'neo_make': lambda x: x.value_counts().index[0] if len(x) > 0 else 'Unknown'
        }).round(2)
        
        dealer_summary.columns = ['inventory_count', 'avg_price', 'median_price', 
                                'min_price', 'max_price', 'avg_miles', 'distance', 'top_brand']
        
        analysis['dealers'] = dealer_summary.sort_values('inventory_count', ascending=False)
        
        # Brand analysis
        brand_analysis = competitors.groupby('neo_make').agg({
            'id': 'count',
            'price': 'mean',
            'miles': 'mean'
        }).round(2)
        brand_analysis.columns = ['count', 'avg_price', 'avg_miles']
        analysis['brands'] = brand_analysis.sort_values('count', ascending=False)
        
        # Price segments
        competitors['price_segment'] = pd.cut(competitors['price'], 
                                            bins=[0, 15000, 30000, 50000, 100000, float('inf')],
                                            labels=['Budget (<$15K)', 'Economy ($15K-$30K)', 
                                                  'Mid-range ($30K-$50K)', 'Premium ($50K-$100K)', 
                                                  'Luxury (>$100K)'])
        
        price_segment_analysis = competitors['price_segment'].value_counts()
        analysis['price_segments'] = price_segment_analysis
        
        # Model year analysis
        year_analysis = competitors.groupby('neo_year').agg({
            'id': 'count',
            'price': 'mean'
        }).round(2)
        year_analysis.columns = ['count', 'avg_price']
        analysis['model_years'] = year_analysis.sort_index(ascending=False)
        
        return analysis, competitors
    
    def analyze_pricing_strategy(self, make=None, model=None, year_range=None):
        """Analyze pricing strategies for specific vehicles"""
        competitors = self.filter_by_radius(self.radius_miles)
        if competitors is None:
            return None, None
            
        # Filter by criteria if provided
        if make:
            competitors = competitors[competitors['neo_make'].str.contains(make, case=False, na=False)]
        if model:
            competitors = competitors[competitors['neo_model'].str.contains(model, case=False, na=False)]
        if year_range:
            competitors = competitors[competitors['neo_year'].between(year_range[0], year_range[1])]
        
        if len(competitors) == 0:
            return None, None
            
        pricing_analysis = {}
        
        # Price vs MSRP analysis
        competitors['discount_amount'] = competitors['msrp'] - competitors['price']
        competitors['discount_percentage'] = (competitors['discount_amount'] / competitors['msrp'] * 100).round(2)
        
        pricing_analysis['price_stats'] = {
            'avg_price': competitors['price'].mean(),
            'median_price': competitors['price'].median(),
            'price_std': competitors['price'].std(),
            'avg_discount_pct': competitors['discount_percentage'].mean(),
            'vehicles_analyzed': len(competitors)
        }
        
        # Dealer pricing comparison
        dealer_pricing = competitors.groupby('seller_name').agg({
            'price': ['mean', 'count'],
            'discount_percentage': 'mean'
        }).round(2)
        
        dealer_pricing.columns = ['avg_price', 'vehicle_count', 'avg_discount_pct']
        pricing_analysis['dealer_comparison'] = dealer_pricing.sort_values('avg_price')
        
        return pricing_analysis, competitors
    
    def analyze_features_and_options(self):
        """Analyze popular features and options among competitors"""
        competitors = self.filter_by_radius(self.radius_miles)
        if competitors is None:
            return None
            
        feature_analysis = {}
        
        # Analyze high-value features
        if 'neo_high_value_features' in competitors.columns:
            features_data = competitors['neo_high_value_features'].dropna()
            if len(features_data) > 0:
                all_features = []
                for features_str in features_data:
                    try:
                        if isinstance(features_str, str) and features_str.strip():
                            features_obj = json.loads(features_str)
                            if 'STANDARD' in features_obj:
                                for feature in features_obj['STANDARD']:
                                    all_features.append(feature.get('description', ''))
                    except:
                        continue
                
                if all_features:
                    feature_counts = pd.Series(all_features).value_counts()
                    feature_analysis['popular_features'] = feature_counts.head(20)
        
        # Certification analysis
        if 'is_certified' in competitors.columns:
            cert_analysis = competitors['is_certified'].value_counts()
            feature_analysis['certification'] = cert_analysis
        
        # Body type analysis
        if 'neo_body_type' in competitors.columns:
            body_type_analysis = competitors['neo_body_type'].value_counts()
            feature_analysis['body_types'] = body_type_analysis
        
        # Fuel type analysis
        if 'neo_fuel_type' in competitors.columns:
            fuel_analysis = competitors['neo_fuel_type'].value_counts()
            feature_analysis['fuel_types'] = fuel_analysis
        
        return feature_analysis
    
    def generate_insights_report(self, analysis_data, competitors_data):
        """Generate textual insights from the analysis"""
        if analysis_data is None:
            return "No analysis data available."
            
        insights = []
        
        # Market overview
        total_competitors = len(analysis_data['dealers'])
        total_inventory = competitors_data['id'].count()
        avg_price = competitors_data['price'].mean()
        
        insights.append(f"📊 **Market Overview:**")
        insights.append(f"- Found {total_competitors} competing dealerships within {self.radius_miles} miles")
        insights.append(f"- Total competitive inventory: {total_inventory} vehicles")
        insights.append(f"- Average market price: ${avg_price:,.0f}")
        
        # Top competitors
        top_3_dealers = analysis_data['dealers'].head(3)
        insights.append(f"\n🏆 **Top Competitors by Inventory:**")
        for i, (dealer, data) in enumerate(top_3_dealers.iterrows(), 1):
            insights.append(f"{i}. {dealer} - {data['inventory_count']} vehicles, avg ${data['avg_price']:,.0f}")
        
        # Brand dominance
        top_brands = analysis_data['brands'].head(3)
        insights.append(f"\n🚗 **Most Popular Brands:**")
        for i, (brand, data) in enumerate(top_brands.iterrows(), 1):
            insights.append(f"{i}. {brand} - {data['count']} vehicles, avg ${data['avg_price']:,.0f}")
        
        # Price segments
        insights.append(f"\n💰 **Price Segment Distribution:**")
        for segment, count in analysis_data['price_segments'].items():
            percentage = (count / total_inventory) * 100
            insights.append(f"- {segment}: {count} vehicles ({percentage:.1f}%)")
        
        # Model year trends
        recent_years = analysis_data['model_years'].head(5)
        insights.append(f"\n📅 **Recent Model Years:**")
        for year, data in recent_years.iterrows():
            insights.append(f"- {year}: {data['count']} vehicles, avg ${data['avg_price']:,.0f}")
        
        return "\n".join(insights)

def main():
    """Main function for running the competitor analysis"""
    print("🚗 Simple Automotive Competitor Analysis System")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = SimpleCompetitorAnalyzer()
    
    # Try to load used car data first
    print("\n📂 Loading vehicle data...")
    if not analyzer.load_data(data_type='used'):
        print("❌ Failed to load used car data. Trying new car data...")
        if not analyzer.load_data(data_type='new'):
            print("❌ Failed to load data. Please check if sample data files exist.")
            return
    
    # Example locations for testing
    test_locations = [
        {"name": "Rochester, NY Dealer", "lat": 43.2158, "lon": -77.7492},
        {"name": "Manhattan, NY Dealer", "lat": 40.7831, "lon": -73.9712},
        {"name": "Buffalo, NY Dealer", "lat": 42.8864, "lon": -78.8784},
        {"name": "Syracuse, NY Dealer", "lat": 43.0481, "lon": -76.1474}
    ]
    
    print("\n🎯 Available test locations:")
    for i, loc in enumerate(test_locations, 1):
        print(f"{i}. {loc['name']}")
    
    try:
        choice = input("\nSelect a location (1-4) or press Enter for Rochester: ").strip()
        if choice == "":
            location = test_locations[0]
        else:
            location = test_locations[int(choice) - 1]
    except (ValueError, IndexError):
        location = test_locations[0]
    
    print(f"\n🎯 Using location: {location['name']}")
    
    # Set target location
    analyzer.set_target_location(location['lat'], location['lon'], location['name'])
    
    # Get radius
    try:
        radius = input("\nEnter analysis radius in miles (default 15): ").strip()
        radius = int(radius) if radius else 15
    except ValueError:
        radius = 15
    
    print(f"\n🔍 Analyzing competitors within {radius} miles...")
    
    # Run analysis
    analysis, competitors = analyzer.analyze_competitor_inventory(radius_miles=radius)
    
    if analysis is not None:
        print("\n" + "="*60)
        print("📊 COMPETITOR ANALYSIS RESULTS")
        print("="*60)
        
        # Generate and display insights
        insights = analyzer.generate_insights_report(analysis, competitors)
        print(insights)
        
        print("\n" + "="*60)
        print("📋 DETAILED COMPETITOR DATA")
        print("="*60)
        
        # Top 10 competitors by inventory
        print("\n🏆 TOP COMPETITORS BY INVENTORY:")
        print(analysis['dealers'].head(10).to_string())
        
        # Brand analysis
        print("\n\n🚗 BRAND ANALYSIS:")
        print(analysis['brands'].head(10).to_string())
        
        # Price segments
        print("\n\n💰 PRICE SEGMENT DISTRIBUTION:")
        for segment, count in analysis['price_segments'].items():
            total_inventory = competitors['id'].count()
            percentage = (count / total_inventory) * 100
            print(f"{segment}: {count} vehicles ({percentage:.1f}%)")
        
        # Feature analysis
        feature_analysis = analyzer.analyze_features_and_options()
        if feature_analysis and 'popular_features' in feature_analysis:
            print("\n\n🔧 MOST POPULAR FEATURES:")
            for i, (feature, count) in enumerate(feature_analysis['popular_features'].head(15).items(), 1):
                print(f"{i:2d}. {feature}: {count} vehicles")
        
        # Pricing analysis for specific makes
        print("\n" + "="*60)
        print("💰 PRICING ANALYSIS BY BRAND")
        print("="*60)
        
        top_brands = analysis['brands'].head(5).index.tolist()
        for brand in top_brands:
            pricing_analysis, brand_competitors = analyzer.analyze_pricing_strategy(make=brand)
            if pricing_analysis:
                stats = pricing_analysis['price_stats']
                print(f"\n{brand.upper()}:")
                print(f"  • Average Price: ${stats['avg_price']:,.0f}")
                print(f"  • Median Price: ${stats['median_price']:,.0f}")
                print(f"  • Average Discount: {stats['avg_discount_pct']:.1f}%")
                print(f"  • Vehicles Analyzed: {stats['vehicles_analyzed']}")
        
        # Save detailed results to CSV
        print(f"\n💾 Saving detailed results...")
        try:
            competitors.to_csv('competitor_analysis_results.csv', index=False)
            analysis['dealers'].to_csv('competitor_dealers_summary.csv')
            analysis['brands'].to_csv('competitor_brands_summary.csv')
            print("✅ Results saved to CSV files:")
            print("   - competitor_analysis_results.csv (full data)")
            print("   - competitor_dealers_summary.csv (dealer summary)")
            print("   - competitor_brands_summary.csv (brand summary)")
        except Exception as e:
            print(f"⚠️  Could not save CSV files: {e}")
        
    else:
        print(f"❌ No competitors found within {radius} miles of {location['name']}")
        print("Try increasing the radius or checking a different location.")
    
    print(f"\n🎉 Analysis complete!")

if __name__ == "__main__":
    main() 
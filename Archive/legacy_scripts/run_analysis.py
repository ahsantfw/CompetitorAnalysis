#!/usr/bin/env python3

import sys
import os
from competitor_analysis import CompetitorAnalyzer

def main():
    print("🚗 Automotive Competitor Analysis System")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = CompetitorAnalyzer()
    
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
        
        # Generate map
        print(f"\n🗺️  Generating competitor map...")
        try:
            competitor_map = analyzer.create_competitor_map()
            if competitor_map:
                competitor_map.save('competitor_map.html')
                print("✅ Interactive map saved as 'competitor_map.html'")
                print("   Open this file in your web browser to view the map.")
        except Exception as e:
            print(f"⚠️  Could not generate map: {e}")
        
    else:
        print(f"❌ No competitors found within {radius} miles of {location['name']}")
        print("Try increasing the radius or checking a different location.")
    
    print(f"\n🎉 Analysis complete!")

if __name__ == "__main__":
    main() 
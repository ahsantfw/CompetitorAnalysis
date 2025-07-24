import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from sklearn.cluster import KMeans
import json
import warnings
warnings.filterwarnings('ignore')
from geopy.distance import geodesic
from datetime import datetime, timedelta
import streamlit as st

class CompetitorAnalyzer:
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
        target_coords = (self.target_location['lat'], self.target_location['lon'])
        
        def calculate_distance(row):
            try:
                dealer_coords = (row['latitude'], row['longitude'])
                return geodesic(target_coords, dealer_coords).miles
            except:
                return float('inf')
        
        df['distance_miles'] = df.apply(calculate_distance, axis=1)
        
        # Filter by radius
        competitors = df[df['distance_miles'] <= radius_miles].copy()
        
        print(f"🔍 Found {len(competitors)} vehicles from competitors within {radius_miles} miles")
        return competitors
    
    def analyze_competitor_inventory(self, radius_miles=15):
        """Analyze competitor inventory within radius"""
        competitors = self.filter_by_radius(radius_miles)
        if competitors is None or len(competitors) == 0:
            return None
            
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
            return None
            
        # Filter by criteria if provided
        if make:
            competitors = competitors[competitors['neo_make'].str.contains(make, case=False, na=False)]
        if model:
            competitors = competitors[competitors['neo_model'].str.contains(model, case=False, na=False)]
        if year_range:
            competitors = competitors[competitors['neo_year'].between(year_range[0], year_range[1])]
        
        if len(competitors) == 0:
            return None
            
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
    
    def create_competitor_map(self):
        """Create an interactive map showing competitor locations"""
        competitors = self.filter_by_radius(self.radius_miles)
        if competitors is None:
            return None
            
        # Create base map centered on target location
        m = folium.Map(
            location=[self.target_location['lat'], self.target_location['lon']],
            zoom_start=10
        )
        
        # Add target dealership marker
        folium.Marker(
            [self.target_location['lat'], self.target_location['lon']],
            popup=f"🎯 {self.target_location['name']}",
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)
        
        # Add radius circle
        folium.Circle(
            location=[self.target_location['lat'], self.target_location['lon']],
            radius=self.radius_miles * 1609.34,  # Convert miles to meters
            popup=f'{self.radius_miles} mile radius',
            color='red',
            fillColor='red',
            fillOpacity=0.1
        ).add_to(m)
        
        # Add competitor markers
        dealer_locations = competitors.groupby(['seller_name', 'latitude', 'longitude']).agg({
            'id': 'count',
            'price': 'mean',
            'distance_miles': 'min'
        }).reset_index()
        
        for _, dealer in dealer_locations.iterrows():
            popup_text = f"""
            <b>{dealer['seller_name']}</b><br>
            Inventory: {dealer['id']} vehicles<br>
            Avg Price: ${dealer['price']:,.0f}<br>
            Distance: {dealer['distance_miles']:.1f} miles
            """
            
            folium.Marker(
                [dealer['latitude'], dealer['longitude']],
                popup=popup_text,
                icon=folium.Icon(color='blue', icon='car', prefix='fa')
            ).add_to(m)
        
        return m
    
    def create_pricing_charts(self, analysis_data, competitors_data):
        """Create pricing analysis charts"""
        if analysis_data is None or competitors_data is None:
            return None
            
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Price Distribution', 'Price by Dealer', 
                          'Price vs Miles', 'Discount Analysis'),
            specs=[[{"type": "histogram"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "box"}]]
        )
        
        # Price distribution
        fig.add_trace(
            go.Histogram(x=competitors_data['price'], name='Price Distribution'),
            row=1, col=1
        )
        
        # Price by dealer (top 10)
        top_dealers = competitors_data.groupby('seller_name')['price'].mean().sort_values(ascending=False).head(10)
        fig.add_trace(
            go.Bar(x=top_dealers.index, y=top_dealers.values, name='Avg Price by Dealer'),
            row=1, col=2
        )
        
        # Price vs Miles
        fig.add_trace(
            go.Scatter(x=competitors_data['miles'], y=competitors_data['price'], 
                      mode='markers', name='Price vs Miles'),
            row=2, col=1
        )
        
        # Discount analysis
        if 'discount_percentage' in competitors_data.columns:
            fig.add_trace(
                go.Box(y=competitors_data['discount_percentage'], name='Discount %'),
                row=2, col=2
            )
        
        fig.update_layout(height=800, showlegend=False, title_text="Competitor Pricing Analysis")
        return fig
    
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
    st.set_page_config(page_title="Automotive Competitor Analysis", layout="wide")
    
    st.title("🚗 Automotive Competitor Analysis Dashboard")
    st.markdown("Analyze your competition within a specified radius to understand market dynamics.")
    
    # Initialize analyzer
    analyzer = CompetitorAnalyzer()
    
    # Sidebar for inputs
    st.sidebar.header("Configuration")
    
    # Data source selection
    data_type = st.sidebar.selectbox("Select Data Source", 
                                   ["used", "new", "auction", "private_party"])
    
    # Location input
    st.sidebar.subheader("Target Dealership Location")
    dealer_name = st.sidebar.text_input("Dealership Name", "Your Dealership")
    lat = st.sidebar.number_input("Latitude", value=40.7128, format="%.4f")
    lon = st.sidebar.number_input("Longitude", value=-74.0060, format="%.4f")
    radius = st.sidebar.slider("Analysis Radius (miles)", 5, 50, 15)
    
    if st.sidebar.button("Load Data & Analyze"):
        with st.spinner("Loading and analyzing data..."):
            # Load data
            if analyzer.load_data(data_type=data_type):
                analyzer.set_target_location(lat, lon, dealer_name)
                
                # Run analysis
                analysis_data, competitors_data = analyzer.analyze_competitor_inventory(radius)
                
                if analysis_data is not None:
                    # Display insights
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("📈 Market Insights")
                        insights = analyzer.generate_insights_report(analysis_data, competitors_data)
                        st.markdown(insights)
                    
                    with col2:
                        st.subheader("🗺️ Competitor Map")
                        competitor_map = analyzer.create_competitor_map()
                        if competitor_map:
                            st.components.v1.html(competitor_map._repr_html_(), height=400)
                    
                    # Pricing analysis
                    st.subheader("💰 Pricing Analysis")
                    pricing_fig = analyzer.create_pricing_charts(analysis_data, competitors_data)
                    if pricing_fig:
                        st.plotly_chart(pricing_fig, use_container_width=True)
                    
                    # Feature analysis
                    st.subheader("🔧 Feature Analysis")
                    feature_analysis = analyzer.analyze_features_and_options()
                    if feature_analysis and 'popular_features' in feature_analysis:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Most Popular Features:**")
                            for feature, count in feature_analysis['popular_features'].head(10).items():
                                st.write(f"• {feature}: {count} vehicles")
                        
                        with col2:
                            if 'body_types' in feature_analysis:
                                st.write("**Body Type Distribution:**")
                                fig_body = px.pie(values=feature_analysis['body_types'].values,
                                               names=feature_analysis['body_types'].index,
                                               title="Body Types")
                                st.plotly_chart(fig_body, use_container_width=True)
                    
                    # Data tables
                    st.subheader("📊 Detailed Analysis")
                    
                    tab1, tab2, tab3 = st.tabs(["Dealer Comparison", "Brand Analysis", "Price Segments"])
                    
                    with tab1:
                        st.dataframe(analysis_data['dealers'])
                    
                    with tab2:
                        st.dataframe(analysis_data['brands'])
                    
                    with tab3:
                        st.bar_chart(analysis_data['price_segments'])
                
                else:
                    st.warning("No competitors found in the specified radius.")
            else:
                st.error("Failed to load data. Please check the data file.")

if __name__ == "__main__":
    # For standalone execution
    print("🚗 Automotive Competitor Analysis System")
    print("========================================")
    
    # Example usage
    analyzer = CompetitorAnalyzer()
    
    # Load used car data
    if analyzer.load_data(data_type='used'):
        # Set target location (example: Rochester, NY)
        analyzer.set_target_location(43.2158, -77.7492, "Rochester Area Dealer")
        
        # Analyze competitors
        analysis, competitors = analyzer.analyze_competitor_inventory(radius_miles=15)
        
        if analysis is not None:
            print("\n" + analyzer.generate_insights_report(analysis, competitors))
        else:
            print("No analysis data available.") 
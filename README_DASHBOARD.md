# 🚗 Dealer Competitive Analysis Dashboard

A world-class dashboard system for automotive dealer competitive analysis, built with **instant performance** and **comprehensive insights**.

## 🎯 **Features Overview**

### **📊 Dashboard Components**
- **🗺️ Interactive Dealer Map**: Click any dealer to see instant insights
- **📈 Sales Analytics**: Total, new, and used sales breakdowns
- **🎯 Competitive Analysis**: Market share and competitor insights
- **🚗 Model Performance**: Top models by make and sales volume
- **📅 Time-based Analysis**: Monthly trends and period comparisons

### **🔍 Advanced Filtering System**
- **Outside DMA**: Include/exclude dealers outside selected DMA
- **Year Filters**: Rolling 12, YTD, Calendar periods
- **Vehicle Types**: New, Used, or All vehicles
- **Sales Range**: Custom min/max sales filters
- **Dealer Selection**: Multi-select dealer filtering
- **Segments**: Sales volume segments (1-67, 68-134, etc.)
- **Makes & Models**: Brand and model-specific filtering
- **Zipcodes**: Geographic filtering by zip codes

## 🏗️ **Architecture**

### **Core Components**
```
features/
├── dashboard.py      # Main Streamlit dashboard
├── api.py           # FastAPI REST endpoints
└── etl.py           # Data processing pipeline

core/
├── loader.py        # High-performance data loading
├── sales.py         # Sales aggregation logic
├── db.py           # Database schema & connections
└── config.py       # Configuration management
```

### **Data Flow**
1. **ETL Pipeline**: CSV → Database → Pre-aggregated summaries
2. **Dashboard**: Instant queries from indexed database
3. **API**: REST endpoints for external integrations

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Set Up Environment**
Create `.env` file:
```env
SQL_SERVER=your_server
SQL_DATABASE=DealersInsights
SQL_USERNAME=your_username
SQL_PASSWORD=your_password
DATA_DIR=data
CHUNK_SIZE=100000
```

### **3. Run ETL Pipeline**
```bash
python features/etl.py data/inventory_2025_07.csv
```

### **4. Launch Dashboard**
```bash
streamlit run features/dashboard.py
```

### **5. Start API Server**
```bash
python features/api.py
```

## 📊 **Dashboard Features**

### **🗺️ Dealer Map Tab**
- **Interactive Map**: Click dealers for instant insights
- **Color-coded Markers**: Red (100+ sales), Orange (50+), Yellow (10+), Green (<10)
- **Dealer Selection**: Choose dealer for detailed analysis
- **Real-time Data**: Live from database

### **📊 Dealer Analysis Tab**
- **Dealer Information**: Name, address, contact details
- **Sales Metrics**: Total, new, used sales with percentages
- **Sales Trends**: Monthly charts with period breakdowns
- **Top Models**: Horizontal bar charts by make/model

### **🎯 Competitive Insights Tab**
- **Market Share Analysis**: Your share vs. competitors
- **Top Competitors**: Ranked by sales volume
- **Geographic Analysis**: Same city/state competitors
- **Performance Comparison**: Sales vs. market average

## 🔌 **API Endpoints**

### **Dealer Endpoints**
```bash
# Get all dealers
GET /dealers?limit=100&min_sales=10&state=NY

# Get specific dealer
GET /dealers/{dealer_id}

# Get dealer summary
GET /dealers/{dealer_id}/summary?period_start=2025-01-01

# Get dealer models
GET /dealers/{dealer_id}/models?limit=10

# Get competitors
GET /dealers/{dealer_id}/competitors?radius_miles=50
```

### **Market Endpoints**
```bash
# Market overview
GET /market/overview?state=NY&city=New%20York

# Top dealers
GET /market/top-dealers?limit=20&by_sales_type=total
```

## 🎨 **Dashboard Design**

### **Professional Styling**
- **Modern UI**: Clean, professional interface
- **Responsive Layout**: Works on all screen sizes
- **Color-coded Metrics**: Intuitive visual indicators
- **Interactive Charts**: Plotly-powered visualizations

### **User Experience**
- **Instant Loading**: Pre-aggregated data for sub-second response
- **Intuitive Navigation**: Tab-based organization
- **Comprehensive Filtering**: All filters from your requirements
- **Real-time Updates**: Live data from database

## 📈 **Performance Optimizations**

### **Database Indexes**
- `(dealer_id, period_start)` for summary queries
- `(dealer_id, period_start, make, model)` for model analysis
- `(mc_dealer_id, status_date)` for raw data queries

### **Caching Strategy**
- **Streamlit Caching**: `@st.cache_data` for data loading
- **Database Queries**: Optimized with proper indexing
- **Chart Rendering**: Efficient Plotly visualizations

### **Data Processing**
- **Chunked Loading**: Handles 15GB+ files efficiently
- **Pre-aggregation**: Heavy computation done during ETL
- **Selective Loading**: Only required columns loaded

## 🔧 **Configuration**

### **Environment Variables**
```env
# Database Configuration
SQL_SERVER=your_server_name
SQL_DATABASE=DealersInsights
SQL_USERNAME=your_username
SQL_PASSWORD=your_password

# Data Processing
DATA_DIR=data
CHUNK_SIZE=100000

# Optional: Direct database URL
SQLALCHEMY_DATABASE_URL=mssql+pyodbc://...
```

### **Dashboard Settings**
- **Chunk Size**: Adjust for memory optimization
- **Map Zoom**: Default zoom level for dealer map
- **Chart Limits**: Number of items in charts
- **API Limits**: Default pagination settings

## 📊 **Data Structure**

### **Sales Summary Table**
```sql
dealer_sales_summary:
- dealer_id (PK)
- period_start (date)
- period_end (date)
- total_sales (int)
- new_sales (int)
- used_sales (int)
- last_updated (timestamp)
```

### **Model Breakdown Table**
```sql
dealer_sales_by_model:
- dealer_id (PK)
- period_start (date)
- period_end (date)
- make (string)
- model (string)
- inventory_type (string)
- sales_count (int)
- last_updated (timestamp)
```

## 🎯 **Use Cases**

### **For Sales Managers**
- **Competitive Analysis**: See who's selling what in your area
- **Market Share**: Understand your position vs. competitors
- **Model Performance**: Identify top-performing vehicles
- **Trend Analysis**: Track sales over time

### **For Marketing Teams**
- **Target Identification**: Find high-performing competitors
- **Geographic Insights**: Understand market distribution
- **Model Trends**: See what's popular in your area
- **Seasonal Patterns**: Identify sales cycles

### **For Executives**
- **Market Overview**: High-level performance metrics
- **Dealer Performance**: Individual dealer insights
- **Strategic Planning**: Data-driven decision making
- **ROI Analysis**: Marketing effectiveness tracking

## 🔄 **Data Refresh**

### **Automated ETL**
```bash
# Daily refresh
python features/etl.py data/inventory_2025_07.csv

# Weekly aggregation
python features/etl.py --weekly data/inventory_2025_07.csv
```

### **Manual Updates**
- **New Data**: Drop new CSV files in `data/` directory
- **Database Refresh**: Run ETL pipeline
- **Dashboard Update**: Automatically picks up new data

## 🚀 **Deployment**

### **Local Development**
```bash
# Start all services
python features/etl.py
streamlit run features/dashboard.py
python features/api.py
```

### **Production Deployment**
```bash
# Using Docker
docker build -t dealer-dashboard .
docker run -p 8501:8501 dealer-dashboard

# Using systemd
sudo systemctl start dealer-dashboard
sudo systemctl enable dealer-dashboard
```

## 📞 **Support**

### **Troubleshooting**
- **Database Connection**: Check `.env` configuration
- **Data Loading**: Verify CSV file paths
- **Performance**: Monitor database indexes
- **Charts**: Ensure Plotly installation

### **Performance Monitoring**
- **Query Times**: Monitor database performance
- **Memory Usage**: Track data loading efficiency
- **User Experience**: Dashboard response times
- **API Usage**: Endpoint performance metrics

---

**🎉 Your world-class dealer competitive analysis dashboard is ready!**

The system provides instant insights, comprehensive filtering, and professional visualizations - exactly what you need for competitive analysis and strategic decision-making. 
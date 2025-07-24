# 🏁 Dealer DMA Competitor Sales Pipeline

## Objective
Build a high-performance, modular pipeline that, given a dealer (by name or id), returns the sales of all nearby dealers in their DMA (Designated Market Area) using MarketCheck data. This enables:
- **Competitive benchmarking**
- **Market share analysis**
- **Targeted marketing recommendations**

---

## 📦 Data Inputs
- **MarketCheck Inventory/Sales Data** (CSV, monthly, 15GB+)
- **Dealer Master List** (with name, id, location, DMA info)
- **DMA Mapping File** (dealer to DMA, or zip/city/state to DMA)

---

## 🔄 Pipeline Overview

1. **Dealer Lookup**
   - Input: Dealer name or id
   - Output: Dealer location (lat/lon, city, state, zip), DMA code
   - **Rationale:** Accurate dealer identification is critical for correct DMA assignment and competitor analysis.

2. **DMA Dealer Extraction**
   - Find all dealers in the same DMA (using mapping file or by geo lookup)
   - Output: List of competitor dealers (names, ids, locations)
   - **Rationale:** DMA is the industry standard for US automotive market analysis; ensures apples-to-apples comparison.

3. **Sales Data Aggregation**
   - Filter main data to the desired time window (e.g., last 3 months)
   - For each dealer in the DMA, count sales (using `status_date` as sale date)
   - Output: Table of dealer, sales count, and optionally by model/type
   - **Rationale:** Sales volume is the key metric for competitive benchmarking and market share.

4. **Competitor Ranking & Insights**
   - Rank dealers by sales volume in DMA
   - Highlight top competitors, market share, and trends
   - **Rationale:** Enables actionable insights and strategic recommendations for your boss/clients.

5. **Reporting & Visualization**
   - Output as table, Excel, or dashboard
   - (Optional) Visualize on map or as charts
   - **Rationale:** Clear, client-ready outputs drive business value and decision-making.

---

## 🛠️ Implementation Steps

### 1. **Data Loader Module**
- Chunked, memory-efficient loader for large CSVs
- Supports column selection and time filtering
- **Implementation Note:** Use pandas with `chunksize` and only load required columns for speed.

### 2. **Dealer & DMA Mapping Module**
- Lookup dealer by name/id
- Map dealer to DMA (via zip/city/state or external mapping)
- Extract all dealers in the same DMA
- **Implementation Note:** If DMA mapping file is missing, use city/state or zip as a proxy. For best results, obtain a DMA mapping file (can be sourced from Nielsen or other providers).

### 3. **Sales Aggregation Module**
- For each dealer in DMA, count unique sales (by `vin` or row) in time window
- Optionally segment by model, type, new/used
- **Implementation Note:** Use `status_date` as the sale date, as per your boss's guidance.

### 4. **Competitor Analysis Module**
- Rank dealers by sales
- Calculate market share, growth, and trends
- Identify top competitors and gaps
- **Implementation Note:** Output should be sorted by sales, and optionally include market share %.

### 5. **Reporting Module**
- Output as CSV, Excel, or dashboard
- (Optional) Generate visualizations (charts, maps)
- **Implementation Note:** Use pandas, ExcelWriter, or dashboard frameworks (e.g., Streamlit) for output.

---

## 🧩 Example Data Flow

1. **Input:** `dealer_id = 12345` (or `dealer_name = "ABC Motors"`)
2. **Lookup:** Find dealer's DMA (e.g., "New York DMA")
3. **Extract:** Get all dealers in "New York DMA"
4. **Aggregate:** Count sales for each dealer in last 3 months
5. **Output:**
   | Dealer Name      | Sales (Last 3 Months) |
   |------------------|----------------------|
   | ABC Motors       | 120                  |
   | XYZ Auto         | 98                   |
   | New York Toyota  | 87                   |

---

## 📚 Glossary: Key Columns from Data Dictionary
- `seller_name`: Dealer Name (the seller of the car)
- `dealer_id` or `mc_dealer_id`: Unique dealer identifier
- `status_date`: The last seen date for the listing (used as the sale date)
- `vin`: Unique vehicle identifier
- `model`, `make`, `trim`, `year`: Car details
- `city`, `state`, `zip`: Dealer location
- `latitude`, `longitude`: Dealer geolocation (if available)
- `dealer_type`: Franchise/independent
- `inventory_type`: New/used
- `price`, `msrp`: Pricing info
- `dma_code` or `dma_name`: Designated Market Area (if available)

---

## 🗺️ Handling DMA Mapping
- **With DMA Mapping File:** Use the mapping to assign each dealer to a DMA. This is the most accurate and industry-standard approach.
- **Without DMA Mapping File:**
  - Use `city`/`state` or `zip` as a proxy for DMA.
  - For more accuracy, use `latitude`/`longitude` and a public DMA boundary shapefile (can be sourced from US Census or Nielsen).
- **Radius-Based Analysis (Fallback):**
  - If DMA is missing, use geospatial queries to find all dealers within a given radius (e.g., 25 miles) of the target dealer.
  - Use the Haversine formula or geopy for fast distance calculations.

---

## 🚀 Future Extensions
- **Geographic Radius Option:** Use lat/lon for radius-based competitor search if DMA not available
- **Model/Type Segmentation:** Show sales by model, body type, or price segment
- **Market Share Trends:** Track changes over time
- **Alerting:** Notify when a competitor's sales spike
- **Integration:** API endpoints for real-time queries

---

## 📈 Success Metrics
- **Pipeline speed:** <10 seconds for DMA-level analysis
- **Accuracy:** 99.9% match to dealer sales
- **Scalability:** Handles 15GB+ monthly files
- **Extensibility:** Easy to add new data sources or analysis modules

---

## 📝 Example Usage

```python
from dma_pipeline import get_dma_competitor_sales

# Get sales for all competitors in a dealer's DMA
results = get_dma_competitor_sales(dealer_id="12345", months=3)
print(results)
```

---

## ❓ Troubleshooting & FAQ

**Q: What if my dealer is missing from the DMA mapping file?**
A: Use city/state or zip as a proxy, or fall back to radius-based analysis using lat/lon.

**Q: What if two dealers have similar names?**
A: Always use unique dealer IDs where possible. If not, match on name + city/state for disambiguation.

**Q: How do I handle very large files?**
A: Use chunked loading (pandas `chunksize`), filter columns and rows early, and aggregate in-memory only what you need.

**Q: What if DMA boundaries change?**
A: Update your DMA mapping file regularly from authoritative sources (Nielsen, US Census, etc.).

**Q: Can I add new data sources?**
A: Yes! The pipeline is modular—add new loaders or mapping modules as needed.

---

## 🏆 Why This Matters
- **Empowers your boss** to see exactly how each dealer stacks up against local competitors
- **Drives strategic decisions** on marketing, inventory, and pricing
- **Delivers client-ready insights** in seconds, even with massive data

---

*This pipeline is the foundation for world-class, data-driven automotive competitive intelligence.* 
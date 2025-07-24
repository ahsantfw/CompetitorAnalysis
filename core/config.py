# Central config for new pipeline

ESSENTIAL_COLUMNS = [
    'vin', 'mc_dealer_id', 'seller_name', 'neo_make', 'neo_model', 'neo_year',
    'inventory_type', 'status_date', 'price', 'msrp', 'city', 'state', 'zip',
    'mc_dealership_group_name', 'dealer_type', 'source',
    'latitude', 'longitude', 'seller_phone', 'seller_email',
    'car_seller_name', 'car_address', 'photo_links'
]

COLUMN_DTYPES = {
    'vin': str,
    'mc_dealer_id': int,
    'seller_name': str,
    'neo_make': str,
    'neo_model': str,
    'neo_year': int,
    'inventory_type': str,
    'status_date': str,  # parse as date later
    'price': float,
    'msrp': float,
    'city': str,
    'state': str,
    'zip': int,
    'mc_dealership_group_name': str,
    'dealer_type': str,
    'source': str,
    'latitude': float,
    'longitude': float,
    'seller_phone': str,
    'seller_email': str,
    'car_seller_name': str,
    'car_address': str,
    'photo_links': str
}

DATE_FORMAT = "%Y-%m-%d"
VIN_DISAPPEAR_DAYS = 5
RAW_DATA_PATH = "data/"
STATE_PATH = "state/vin_tracker.parquet"
DB_URL = "mssql+pyodbc://..." 
from get_data import MarketCheckAPI

api = MarketCheckAPI()

# Get live inventory around your dealership
inventory = api.get_all_inventory_in_radius(43.2158, -77.7492, 25)

# Find competitor dealerships
dealers = api.search_dealers_by_location(43.2158, -77.7492, 25)

# Integrate with your existing analysis
api.save_data_to_csv(inventory, "live_market_data.csv")

#!/usr/bin/env python3
"""
MarketCheck API Data Retrieval System
=====================================

This module provides methods to retrieve automotive data from MarketCheck API
for competitive analysis. It focuses on the most valuable endpoints for 
dealership competitive intelligence.

Key API Endpoints Implemented:
- Active Car Inventory Search
- Dealer Information & Search
- Private Party Listings
- Auction Listings
- Market Statistics
- Popular Cars Data
- Sales Statistics
- Price Predictions
- VIN History
- OEM Incentives

Author: Automotive Competitor Analysis System
Version: 1.0
"""

import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Union
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MarketCheckAPI:
    """
    MarketCheck API client for automotive data retrieval.
    
    This class provides methods to access various MarketCheck API endpoints
    for comprehensive competitive analysis.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize MarketCheck API client.
        
        Args:
            api_key (str): MarketCheck API key. If None, will try to load from environment.
        """
        self.api_key = api_key or os.getenv('MARKETCHECK_API_KEY')
        if not self.api_key:
            raise ValueError("API key is required. Set MARKETCHECK_API_KEY environment variable or pass api_key parameter.")
        
        self.base_url = "https://mc-api.marketcheck.com"
        self.headers = {
            'Host': 'mc-api.marketcheck.com',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint (str): API endpoint path
            params (dict): Query parameters
            
        Returns:
            dict: API response data
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                self.logger.warning("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(endpoint, params)
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request exception: {e}")
            return None
    
    # ============================================================================
    # CORE INVENTORY SEARCH METHODS (Most Important for Competitive Analysis)
    # ============================================================================
    
    def search_active_inventory(self, 
                               latitude: float = None,
                               longitude: float = None,
                               radius: int = 50,
                               make: str = None,
                               model: str = None,
                               year_min: int = None,
                               year_max: int = None,
                               price_min: int = None,
                               price_max: int = None,
                               mileage_max: int = None,
                               body_type: str = None,
                               fuel_type: str = None,
                               transmission: str = None,
                               drivetrain: str = None,
                               condition: str = None,
                               certified: bool = None,
                               dealer_type: str = None,
                               rows: int = 50,
                               start: int = 0) -> pd.DataFrame:
        """
        Search active car inventory - PRIMARY METHOD for competitive analysis.
        
        This is the most important method for getting current market inventory data.
        
        Args:
            latitude (float): Search center latitude
            longitude (float): Search center longitude  
            radius (int): Search radius in miles (default: 50)
            make (str): Vehicle make (e.g., 'Toyota', 'Honda')
            model (str): Vehicle model (e.g., 'Camry', 'Accord')
            year_min (int): Minimum model year
            year_max (int): Maximum model year
            price_min (int): Minimum price
            price_max (int): Maximum price
            mileage_max (int): Maximum mileage
            body_type (str): Body type ('SUV', 'Sedan', 'Truck', etc.)
            fuel_type (str): Fuel type ('Gasoline', 'Hybrid', 'Electric', etc.)
            transmission (str): Transmission type ('Automatic', 'Manual')
            drivetrain (str): Drivetrain ('FWD', 'AWD', 'RWD', '4WD')
            condition (str): Vehicle condition ('New', 'Used', 'Certified')
            certified (bool): Certified pre-owned only
            dealer_type (str): Dealer type filter
            rows (int): Number of results per page (max 50)
            start (int): Starting index for pagination
            
        Returns:
            pd.DataFrame: Vehicle inventory data
        """
        endpoint = "/v2/search/car/active"
        
        params = {
            'rows': rows,
            'start': start
        }
        
        # Geographic filters
        if latitude and longitude:
            params['latitude'] = latitude
            params['longitude'] = longitude
            params['radius'] = radius
        
        # Vehicle specification filters
        if make:
            params['make'] = make
        if model:
            params['model'] = model
        if year_min:
            params['year_min'] = year_min
        if year_max:
            params['year_max'] = year_max
        if price_min:
            params['price_min'] = price_min
        if price_max:
            params['price_max'] = price_max
        if mileage_max:
            params['miles_max'] = mileage_max
        if body_type:
            params['body_type'] = body_type
        if fuel_type:
            params['fuel_type'] = fuel_type
        if transmission:
            params['transmission'] = transmission
        if drivetrain:
            params['drivetrain'] = drivetrain
        if condition:
            params['inventory_type'] = condition
        if certified is not None:
            params['is_certified'] = certified
        if dealer_type:
            params['dealer_type'] = dealer_type
        
        self.logger.info(f"Searching active inventory with params: {params}")
        
        response = self._make_request(endpoint, params)
        
        if response and 'listings' in response:
            df = pd.DataFrame(response['listings'])
            self.logger.info(f"Retrieved {len(df)} vehicle listings")
            return df
        else:
            self.logger.warning("No inventory data retrieved")
            return pd.DataFrame()
    
    def get_all_inventory_in_radius(self,
                                   latitude: float,
                                   longitude: float,
                                   radius: int = 25,
                                   max_results: int = 1000) -> pd.DataFrame:
        """
        Get ALL available inventory within a radius (handles pagination).
        
        This method is essential for comprehensive competitive analysis.
        
        Args:
            latitude (float): Search center latitude
            longitude (float): Search center longitude
            radius (int): Search radius in miles
            max_results (int): Maximum number of results to retrieve
            
        Returns:
            pd.DataFrame: Complete inventory dataset
        """
        all_listings = []
        start = 0
        rows_per_request = 50
        
        self.logger.info(f"Retrieving all inventory within {radius} miles of ({latitude}, {longitude})")
        
        while len(all_listings) < max_results:
            batch = self.search_active_inventory(
                latitude=latitude,
                longitude=longitude,
                radius=radius,
                rows=rows_per_request,
                start=start
            )
            
            if batch.empty:
                break
                
            all_listings.append(batch)
            start += rows_per_request
            
            self.logger.info(f"Retrieved {len(batch)} listings (total: {len(all_listings) * rows_per_request})")
            
            # Break if we got fewer results than requested (end of data)
            if len(batch) < rows_per_request:
                break
        
        if all_listings:
            complete_df = pd.concat(all_listings, ignore_index=True)
            self.logger.info(f"Total inventory retrieved: {len(complete_df)} vehicles")
            return complete_df
        else:
            return pd.DataFrame()
    
    # ============================================================================
    # DEALER INFORMATION METHODS (Critical for Competitor Analysis)
    # ============================================================================
    
    def search_dealers_by_location(self,
                                  latitude: float,
                                  longitude: float,
                                  radius: int = 50,
                                  dealer_type: str = None,
                                  make: str = None) -> pd.DataFrame:
        """
        Search car dealers around a location - ESSENTIAL for competitor mapping.
        
        Args:
            latitude (float): Search center latitude
            longitude (float): Search center longitude
            radius (int): Search radius in miles
            dealer_type (str): Type of dealer
            make (str): Specific make/brand
            
        Returns:
            pd.DataFrame: Dealer information
        """
        endpoint = "/v2/dealers/car"
        
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'radius': radius
        }
        
        if dealer_type:
            params['dealer_type'] = dealer_type
        if make:
            params['make'] = make
        
        self.logger.info(f"Searching dealers within {radius} miles of ({latitude}, {longitude})")
        
        response = self._make_request(endpoint, params)
        
        if response and 'dealers' in response:
            df = pd.DataFrame(response['dealers'])
            self.logger.info(f"Found {len(df)} dealers")
            return df
        else:
            return pd.DataFrame()
    
    def get_dealer_details(self, dealer_id: str) -> Dict:
        """
        Get detailed information about a specific dealer.
        
        Args:
            dealer_id (str): Dealer ID
            
        Returns:
            dict: Detailed dealer information
        """
        endpoint = f"/v2/dealer/car/{dealer_id}"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Retrieved details for dealer {dealer_id}")
            return response
        else:
            return {}
    
    def get_dealer_active_inventory(self,
                                   dealer_id: str = None,
                                   dealer_name: str = None,
                                   latitude: float = None,
                                   longitude: float = None,
                                   radius: int = 10) -> pd.DataFrame:
        """
        Get active inventory for specific dealers.
        
        Args:
            dealer_id (str): Specific dealer ID
            dealer_name (str): Dealer name to search for
            latitude (float): Search center latitude
            longitude (float): Search center longitude
            radius (int): Search radius in miles
            
        Returns:
            pd.DataFrame: Dealer's active inventory
        """
        endpoint = "/v2/search/car/dealer/inventory/active"
        
        params = {}
        
        if dealer_id:
            params['dealer_id'] = dealer_id
        if dealer_name:
            params['dealer_name'] = dealer_name
        if latitude and longitude:
            params['latitude'] = latitude
            params['longitude'] = longitude
            params['radius'] = radius
        
        response = self._make_request(endpoint, params)
        
        if response and 'listings' in response:
            df = pd.DataFrame(response['listings'])
            self.logger.info(f"Retrieved {len(df)} vehicles from dealer inventory")
            return df
        else:
            return pd.DataFrame()
    
    # ============================================================================
    # ALTERNATIVE INVENTORY SOURCES (Private Party & Auction)
    # ============================================================================
    
    def search_private_party_listings(self,
                                     latitude: float = None,
                                     longitude: float = None,
                                     radius: int = 50,
                                     make: str = None,
                                     model: str = None,
                                     year_min: int = None,
                                     year_max: int = None,
                                     price_min: int = None,
                                     price_max: int = None,
                                     rows: int = 50) -> pd.DataFrame:
        """
        Search private party (FSBO - For Sale By Owner) listings.
        
        Important for understanding total market competition including private sellers.
        
        Args:
            latitude (float): Search center latitude
            longitude (float): Search center longitude
            radius (int): Search radius in miles
            make (str): Vehicle make
            model (str): Vehicle model
            year_min (int): Minimum model year
            year_max (int): Maximum model year
            price_min (int): Minimum price
            price_max (int): Maximum price
            rows (int): Number of results
            
        Returns:
            pd.DataFrame: Private party listings
        """
        endpoint = "/v2/search/car/fsbo/active"
        
        params = {'rows': rows}
        
        if latitude and longitude:
            params['latitude'] = latitude
            params['longitude'] = longitude
            params['radius'] = radius
        if make:
            params['make'] = make
        if model:
            params['model'] = model
        if year_min:
            params['year_min'] = year_min
        if year_max:
            params['year_max'] = year_max
        if price_min:
            params['price_min'] = price_min
        if price_max:
            params['price_max'] = price_max
        
        response = self._make_request(endpoint, params)
        
        if response and 'listings' in response:
            df = pd.DataFrame(response['listings'])
            self.logger.info(f"Retrieved {len(df)} private party listings")
            return df
        else:
            return pd.DataFrame()
    
    def search_auction_listings(self,
                               make: str = None,
                               model: str = None,
                               year_min: int = None,
                               year_max: int = None,
                               rows: int = 50) -> pd.DataFrame:
        """
        Search auction listings.
        
        Useful for understanding wholesale market pricing and trends.
        
        Args:
            make (str): Vehicle make
            model (str): Vehicle model
            year_min (int): Minimum model year
            year_max (int): Maximum model year
            rows (int): Number of results
            
        Returns:
            pd.DataFrame: Auction listings
        """
        endpoint = "/v2/search/car/auction/active"
        
        params = {'rows': rows}
        
        if make:
            params['make'] = make
        if model:
            params['model'] = model
        if year_min:
            params['year_min'] = year_min
        if year_max:
            params['year_max'] = year_max
        
        response = self._make_request(endpoint, params)
        
        if response and 'listings' in response:
            df = pd.DataFrame(response['listings'])
            self.logger.info(f"Retrieved {len(df)} auction listings")
            return df
        else:
            return pd.DataFrame()
    
    # ============================================================================
    # MARKET INTELLIGENCE METHODS (Strategic Analysis)
    # ============================================================================
    
    def get_popular_cars(self,
                        geography: str = 'national',
                        state: str = None,
                        city: str = None,
                        period: str = 'last_30_days') -> Dict:
        """
        Get most popular cars data - VALUABLE for market trend analysis.
        
        Args:
            geography (str): 'national', 'state', or 'city'
            state (str): State code (if geography is 'state' or 'city')
            city (str): City name (if geography is 'city')
            period (str): Time period for popularity analysis
            
        Returns:
            dict: Popular cars data
        """
        endpoint = "/v2/popular/cars"
        
        params = {
            'geography': geography,
            'period': period
        }
        
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        
        response = self._make_request(endpoint, params)
        
        if response:
            self.logger.info(f"Retrieved popular cars data for {geography}")
            return response
        else:
            return {}
    
    def get_sales_statistics(self,
                           make: str = None,
                           model: str = None,
                           year: int = None,
                           trim: str = None,
                           geography: str = 'national',
                           state: str = None,
                           city: str = None) -> Dict:
        """
        Get sales statistics for last 90 days - CRITICAL for market analysis.
        
        Args:
            make (str): Vehicle make
            model (str): Vehicle model
            year (int): Model year
            trim (str): Trim level
            geography (str): 'national', 'state', or 'city'
            state (str): State code
            city (str): City name
            
        Returns:
            dict: Sales statistics
        """
        endpoint = "/v2/sales/car"
        
        params = {
            'geography': geography
        }
        
        if make:
            params['make'] = make
        if model:
            params['model'] = model
        if year:
            params['year'] = year
        if trim:
            params['trim'] = trim
        if state:
            params['state'] = state
        if city:
            params['city'] = city
        
        response = self._make_request(endpoint, params)
        
        if response:
            self.logger.info(f"Retrieved sales statistics for {make} {model}")
            return response
        else:
            return {}
    
    def get_market_days_supply(self,
                              make: str,
                              model: str,
                              year: int,
                              trim: str = None,
                              zip_code: str = None) -> Dict:
        """
        Get Market Days Supply (MDS) value - IMPORTANT for inventory planning.
        
        Args:
            make (str): Vehicle make
            model (str): Vehicle model
            year (int): Model year
            trim (str): Trim level
            zip_code (str): ZIP code for local market analysis
            
        Returns:
            dict: Market Days Supply data
        """
        endpoint = "/v2/mds"
        
        params = {
            'make': make,
            'model': model,
            'year': year
        }
        
        if trim:
            params['trim'] = trim
        if zip_code:
            params['zip'] = zip_code
        
        response = self._make_request(endpoint, params)
        
        if response:
            self.logger.info(f"Retrieved MDS for {year} {make} {model}")
            return response
        else:
            return {}
    
    # ============================================================================
    # PRICING & VALUATION METHODS (Competitive Pricing)
    # ============================================================================
    
    def predict_car_price(self,
                         vin: str = None,
                         make: str = None,
                         model: str = None,
                         year: int = None,
                         mileage: int = None,
                         zip_code: str = None) -> Dict:
        """
        Predict fair retail price - ESSENTIAL for competitive pricing strategy.
        
        Args:
            vin (str): Vehicle VIN (preferred method)
            make (str): Vehicle make (if no VIN)
            model (str): Vehicle model (if no VIN)
            year (int): Model year (if no VIN)
            mileage (int): Vehicle mileage
            zip_code (str): ZIP code for local market pricing
            
        Returns:
            dict: Price prediction data
        """
        endpoint = "/v2/predict/car/price"
        
        params = {}
        
        if vin:
            params['vin'] = vin
        else:
            if make:
                params['make'] = make
            if model:
                params['model'] = model
            if year:
                params['year'] = year
        
        if mileage:
            params['mileage'] = mileage
        if zip_code:
            params['zip'] = zip_code
        
        response = self._make_request(endpoint, params)
        
        if response:
            self.logger.info(f"Retrieved price prediction for {vin or f'{year} {make} {model}'}")
            return response
        else:
            return {}
    
    def get_marketcheck_price_base(self,
                                  vin: str,
                                  mileage: int,
                                  zip_code: str) -> Dict:
        """
        Get MarketCheck base price analysis.
        
        Args:
            vin (str): Vehicle VIN
            mileage (int): Vehicle mileage
            zip_code (str): ZIP code
            
        Returns:
            dict: Base price analysis
        """
        endpoint = "/v2/predict/car/us/marketcheck_price"
        
        params = {
            'vin': vin,
            'mileage': mileage,
            'zip': zip_code
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            self.logger.info(f"Retrieved MarketCheck base price for VIN {vin}")
            return response
        else:
            return {}
    
    def get_marketcheck_price_comparables(self,
                                        vin: str,
                                        mileage: int,
                                        zip_code: str) -> Dict:
        """
        Get MarketCheck price with comparable vehicles (Premium API).
        
        Args:
            vin (str): Vehicle VIN
            mileage (int): Vehicle mileage
            zip_code (str): ZIP code
            
        Returns:
            dict: Price analysis with comparables
        """
        endpoint = "/v2/predict/car/us/marketcheck_price/comparables"
        
        params = {
            'vin': vin,
            'mileage': mileage,
            'zip': zip_code
        }
        
        response = self._make_request(endpoint, params)
        
        if response:
            self.logger.info(f"Retrieved MarketCheck price with comparables for VIN {vin}")
            return response
        else:
            return {}
    
    # ============================================================================
    # INCENTIVES & PROMOTIONS (Market Intelligence)
    # ============================================================================
    
    def get_oem_incentives(self,
                          oem: str,
                          zip_code: str) -> Dict:
        """
        Get OEM incentive programs - VALUABLE for competitive pricing analysis.
        
        Args:
            oem (str): OEM/Manufacturer name (e.g., 'toyota', 'honda')
            zip_code (str): ZIP code for local incentives
            
        Returns:
            dict: OEM incentive data
        """
        endpoint = f"/v2/search/car/incentive/{oem}/{zip_code}"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Retrieved OEM incentives for {oem} in {zip_code}")
            return response
        else:
            return {}
    
    def search_all_oem_incentives(self) -> Dict:
        """
        Search all available OEM incentive programs.
        
        Returns:
            dict: All OEM incentive programs
        """
        endpoint = "/v2/search/car/incentive/oem"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info("Retrieved all OEM incentive programs")
            return response
        else:
            return {}
    
    # ============================================================================
    # VIN & VEHICLE HISTORY (Due Diligence)
    # ============================================================================
    
    def get_vin_history(self, vin: str) -> Dict:
        """
        Get online listing history for a VIN - USEFUL for market analysis.
        
        Args:
            vin (str): Vehicle VIN
            
        Returns:
            dict: VIN listing history
        """
        endpoint = f"/v2/history/car/{vin}"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Retrieved history for VIN {vin}")
            return response
        else:
            return {}
    
    def decode_vin_basic(self, vin: str) -> Dict:
        """
        Basic VIN decode to specifications.
        
        Args:
            vin (str): Vehicle VIN
            
        Returns:
            dict: VIN decode specifications
        """
        endpoint = f"/v2/decode/car/{vin}/specs"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Decoded VIN {vin}")
            return response
        else:
            return {}
    
    def decode_vin_enhanced(self, vin: str) -> Dict:
        """
        Enhanced VIN decode with more detailed specifications.
        
        Args:
            vin (str): Vehicle VIN
            
        Returns:
            dict: Enhanced VIN decode data
        """
        endpoint = f"/v2/decode/car/epi/{vin}/specs"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Enhanced decode for VIN {vin}")
            return response
        else:
            return {}
    
    def decode_vin_neovin(self, vin: str) -> Dict:
        """
        NeoVIN enhanced decode - most comprehensive VIN decode.
        
        Args:
            vin (str): Vehicle VIN
            
        Returns:
            dict: NeoVIN decode data
        """
        endpoint = f"/v2/decode/car/neovin/{vin}/specs"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"NeoVIN decode for VIN {vin}")
            return response
        else:
            return {}
    
    # ============================================================================
    # LISTING DETAILS (Deep Dive Analysis)
    # ============================================================================
    
    def get_listing_details(self, listing_id: str) -> Dict:
        """
        Get complete listing details.
        
        Args:
            listing_id (str): Listing ID
            
        Returns:
            dict: Complete listing data
        """
        endpoint = f"/v2/listing/car/{listing_id}"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Retrieved details for listing {listing_id}")
            return response
        else:
            return {}
    
    def get_listing_media(self, listing_id: str) -> Dict:
        """
        Get photos and videos for a listing.
        
        Args:
            listing_id (str): Listing ID
            
        Returns:
            dict: Media data (photos, videos)
        """
        endpoint = f"/v2/listing/car/{listing_id}/media"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Retrieved media for listing {listing_id}")
            return response
        else:
            return {}
    
    def get_listing_extras(self, listing_id: str) -> Dict:
        """
        Get options, features, and seller comments for a listing.
        
        Args:
            listing_id (str): Listing ID
            
        Returns:
            dict: Options, features, and comments
        """
        endpoint = f"/v2/listing/car/{listing_id}/extra"
        
        response = self._make_request(endpoint)
        
        if response:
            self.logger.info(f"Retrieved extras for listing {listing_id}")
            return response
        else:
            return {}
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def save_data_to_csv(self, data: pd.DataFrame, filename: str, directory: str = "api_data"):
        """
        Save retrieved data to CSV file.
        
        Args:
            data (pd.DataFrame): Data to save
            filename (str): Output filename
            directory (str): Output directory
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        filepath = os.path.join(directory, filename)
        data.to_csv(filepath, index=False)
        self.logger.info(f"Saved {len(data)} records to {filepath}")
    
    def get_comprehensive_market_data(self,
                                    latitude: float,
                                    longitude: float,
                                    radius: int = 25,
                                    max_results: int = 1000) -> Dict[str, pd.DataFrame]:
        """
        Get comprehensive market data for competitive analysis.
        
        This method combines multiple API calls to provide a complete market picture.
        
        Args:
            latitude (float): Search center latitude
            longitude (float): Search center longitude
            radius (int): Search radius in miles
            max_results (int): Maximum results per data type
            
        Returns:
            dict: Dictionary containing all market data types
        """
        market_data = {}
        
        self.logger.info(f"Starting comprehensive market data collection for ({latitude}, {longitude})")
        
        # 1. Active dealer inventory
        self.logger.info("Collecting active dealer inventory...")
        market_data['dealer_inventory'] = self.get_all_inventory_in_radius(
            latitude, longitude, radius, max_results
        )
        
        # 2. Dealer information
        self.logger.info("Collecting dealer information...")
        market_data['dealers'] = self.search_dealers_by_location(
            latitude, longitude, radius
        )
        
        # 3. Private party listings
        self.logger.info("Collecting private party listings...")
        market_data['private_party'] = self.search_private_party_listings(
            latitude, longitude, radius, rows=min(max_results, 200)
        )
        
        # 4. Popular cars data (national and state level)
        self.logger.info("Collecting popular cars data...")
        try:
            market_data['popular_cars_national'] = self.get_popular_cars('national')
            # You can add state-specific data if you have state info
        except Exception as e:
            self.logger.warning(f"Could not retrieve popular cars data: {e}")
            market_data['popular_cars_national'] = {}
        
        # Save all data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for data_type, data in market_data.items():
            if isinstance(data, pd.DataFrame) and not data.empty:
                filename = f"{data_type}_{timestamp}.csv"
                self.save_data_to_csv(data, filename)
        
        self.logger.info("Comprehensive market data collection complete")
        return market_data

# ============================================================================
# USAGE EXAMPLES AND TESTING
# ============================================================================

def main():
    """
    Example usage of MarketCheck API client.
    """
    # Initialize API client
    try:
        api = MarketCheckAPI()
        print("✅ MarketCheck API client initialized successfully")
    except ValueError as e:
        print(f"❌ Error initializing API client: {e}")
        print("Please set your MARKETCHECK_API_KEY in the .env file")
        return
    
    # Example: Search for inventory around a location
    print("\n🔍 Example: Searching for inventory in Rochester, NY area...")
    
    # Rochester, NY coordinates
    latitude = 43.2158
    longitude = -77.7492
    radius = 25
    
    try:
        # Get active inventory
        inventory = api.search_active_inventory(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            rows=10  # Limit for testing
        )
        
        if not inventory.empty:
            print(f"✅ Found {len(inventory)} vehicles")
            print("\nSample data:")
            print(inventory[['make', 'model', 'year', 'price', 'miles']].head())
        else:
            print("❌ No inventory found")
        
        # Get dealers in the area
        print(f"\n🏢 Searching for dealers within {radius} miles...")
        dealers = api.search_dealers_by_location(
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        
        if not dealers.empty:
            print(f"✅ Found {len(dealers)} dealers")
            if 'name' in dealers.columns:
                print("Dealers found:")
                for dealer in dealers['name'].head():
                    print(f"  - {dealer}")
        else:
            print("❌ No dealers found")
        
        # Get popular cars data
        print(f"\n📊 Getting popular cars data...")
        popular = api.get_popular_cars()
        
        if popular:
            print("✅ Retrieved popular cars data")
            if 'popular_cars' in popular:
                print("Top popular cars:")
                for i, car in enumerate(popular['popular_cars'][:5], 1):
                    print(f"  {i}. {car.get('make', 'Unknown')} {car.get('model', 'Unknown')}")
        else:
            print("❌ No popular cars data available")
            
    except Exception as e:
        print(f"❌ Error during API testing: {e}")

if __name__ == "__main__":
    main() 
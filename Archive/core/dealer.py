import pandas as pd

def get_dealer_info(dealer_id, dealer_df):
    row = dealer_df[dealer_df['dealer_id'] == dealer_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()

def get_dealers_by_zip(zip_code, dealer_df):
    return dealer_df[dealer_df['zip'] == zip_code] 
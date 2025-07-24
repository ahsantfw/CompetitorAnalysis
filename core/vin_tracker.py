import pandas as pd
import os
import sys, os
print(sys.path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import STATE_PATH, VIN_DISAPPEAR_DAYS, DATE_FORMAT

def load_state():
    if os.path.exists(STATE_PATH):
        return pd.read_parquet(STATE_PATH)
    else:
        return pd.DataFrame(columns=['vin', 'last_seen', 'disappear_count', 'dealer_id', 'make', 'model', 'year'])

def save_state(state_df):
    state_df.to_parquet(STATE_PATH, index=False)

def update_state(today_df, today_date, prev_state):
    today_vins = set(today_df['vin'])
    today_date_str = pd.to_datetime(today_date).strftime(DATE_FORMAT)
    # Mark all VINs seen today
    seen_today = prev_state['vin'].isin(today_vins)
    prev_state.loc[seen_today, 'last_seen'] = today_date_str
    prev_state.loc[seen_today, 'disappear_count'] = 0
    # For VINs not seen today, increment disappear_count
    not_seen_today = ~prev_state['vin'].isin(today_vins)
    prev_state.loc[not_seen_today, 'disappear_count'] += 1
    # Add new VINs
    new_vins = today_vins - set(prev_state['vin'])
    if new_vins:
        new_rows = today_df[today_df['vin'].isin(new_vins)].copy()
        new_rows['last_seen'] = today_date_str
        new_rows['disappear_count'] = 0
        prev_state = pd.concat([prev_state, new_rows[['vin', 'last_seen', 'disappear_count', 'mc_dealer_id', 'make', 'model', 'year']].rename(columns={'mc_dealer_id':'dealer_id'})], ignore_index=True)
    # Mark as sold if disappear_count >= threshold
    sold_mask = prev_state['disappear_count'] >= VIN_DISAPPEAR_DAYS
    sold_vins = prev_state[sold_mask].copy()
    # Remove sold VINs from state
    state_df = prev_state[~sold_mask].reset_index(drop=True)
    return state_df, sold_vins

def get_sold_vins(today_df, today_date, prev_state):
    state_df, sold_vins = update_state(today_df, today_date, prev_state)
    save_state(state_df)
    return sold_vins 
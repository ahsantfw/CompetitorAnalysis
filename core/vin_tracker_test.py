import pandas as pd
import numpy as np
import time
from core.vin_tracker import load_state, save_state, update_state
from core.config import VIN_DISAPPEAR_DAYS

# Simulate 1 million VINs for day 0
N = 1_000_000
np.random.seed(42)
base_vins = [f'VIN{str(i).zfill(8)}' for i in range(N)]

# Simulate dealer, make, model, year
dealers = np.random.randint(1000000, 1001000, N)
makes = np.random.choice(['ford', 'chevy', 'honda', 'toyota'], N)
models = np.random.choice(['focus', 'civic', 'camry', 'malibu'], N)
years = np.random.randint(2018, 2024, N)

# Create initial DataFrame
def make_df(vins):
    idx = [int(v[3:]) for v in vins]
    return pd.DataFrame({
        'vin': vins,
        'mc_dealer_id': dealers[idx],
        'make': makes[idx],
        'model': models[idx],
        'year': years[idx]
    })

# Simulate 6 days, each day randomly remove 1% of VINs (simulate sales)
vin_sets = [set(base_vins)]
for day in range(1, 6+1):
    prev = vin_sets[-1]
    remove_n = int(0.01 * len(prev))
    remove_vins = set(np.random.choice(list(prev), remove_n, replace=False))
    vin_sets.append(prev - remove_vins)

# Run the tracker
state = None
sold_total = pd.DataFrame()
start = time.time()
for i, vins in enumerate(vin_sets):
    today = make_df(list(vins))
    date = f"2025-07-{i+1:02d}"
    if state is None:
        state = pd.DataFrame(columns=['vin', 'last_seen', 'disappear_count', 'dealer_id', 'make', 'model', 'year'])
    state, sold = update_state(today, date, state)
    print(f"Day {i+1}: {len(today)} active, {len(sold)} sold")
    if not sold.empty:
        sold_total = pd.concat([sold_total, sold], ignore_index=True)
end = time.time()
print(f"\nTotal sold after {len(vin_sets)} days: {len(sold_total)}")
print(f"Elapsed time: {end-start:.2f} seconds") 
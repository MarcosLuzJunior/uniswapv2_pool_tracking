import os
import pandas as pd
import ast
from dataclasses import dataclass, asdict
import time
import json
import unittest
import test_pool_tracking
import requests

def get_binance_price(symbol="ETHUSDT"): #No WETH/USDT pair, Binance uses native ETH, uni uses WETH for ECR20 purposes so pretend for this demo 1 WETH ~ 1 ETH
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url)
    return float(response.json()["price"])

def detect_mispricing(reserve0, reserve1, external_price):
    # Need to check the contract, but say we normalise it with the following assumptions:
    weth_n= int(reserve0) / 1e18
    usdt_n = int(reserve1) / 1e6
    uniswap_price = usdt_n / weth_n if weth_n > 0 else 0
    delta = abs(uniswap_price - external_price)
    mispriced = delta > 0.01 * external_price  # e.g., >1% difference as example here, not taking into account gas fees etc
    return mispriced, uniswap_price

@dataclass
class UniswapV2State:
    reserve0: int = 0
    reserve1: int = 0


    # Initialise the states to 0, 0.
    def update(self, reserve0: int, reserve1: int):
        self.reserve0 = reserve0
        self.reserve1 = reserve1

    # Think of outage, serialise the last state so it can be picked up from that.
    # Could append it to keep history but it's slower than override and files grows in size
    # Thinking of podcast videos where team commented about system outages etc
    def serialise_to_json(self, file_path):
        try:
            with open(file_path, "w") as f:
                json.dump(asdict(self), f)
            print(f"State serialized to {file_path}")
        except Exception as e:
            print(f"Serialization error: {e}")

    # Check if there's a serialised json with the latest state and set the initial reserves to that
    def load_from_json(self, file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                self.reserve0 = data.get("reserve0", 0) #Get values from key, if not present set it to zero
                self.reserve1 = data.get("reserve1", 0)
            print(f"State loaded from {file_path}")
        except FileNotFoundError:
            print(f"No state file found at {file_path}. Starting with default state.")
        except Exception as e:
            print(f"Error loading state: {e}")

def load_file():
    #Find downloaded file in download folder and read to df, wrap in try-except
    try:
        username = os.getlogin()
        downloads_path = os.path.join("C:/Users", username, "Downloads", "uniswap_v2.csv")

        if os.path.exists(downloads_path):
            df = pd.read_csv(downloads_path)
            print("File loaded successfully:")
            # print(df.head())
            return df
        else:
            raise FileNotFoundError(f"File not found at: {downloads_path}")
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def filter_sync_events(df):

    #filter only for those syc type events in column event_signature, create new columns to save the two int value of the currency-token pair
    try:
        sync_events = df[df["event_signature"] == "Sync(uint112,uint112)"].copy() #Sync event checking because it seems where the liquidy pool updates perhaps the authorative state? to check with Matt
        sync_events["args"] = sync_events["args"].apply(ast.literal_eval)
        sync_events["reserve0"] = sync_events["args"].apply(lambda x: int(x[0]))
        sync_events["reserve1"] = sync_events["args"].apply(lambda x: int(x[1]))

        # Check if there are any negative values, and log/print them. Shoulf log them in prod
        invalid_rows = sync_events[(sync_events["reserve0"] < 0) | (sync_events["reserve1"] < 0)]
        if not invalid_rows.empty:
            print("Warning: Negative reserve values detected and removed:")
            print(invalid_rows[["block_number", "reserve0", "reserve1"]])

        # Drop the negative instances, to discuss with Matt (is it malformed, part of the test etc) Keep only valid rows
        sync_events = sync_events[(sync_events["reserve0"] >= 0) & (sync_events["reserve1"] >= 0)]

        return sync_events # Return only instances non-nagative of type sync
    except Exception as e:
        print(f"Error processing sync events: {e}")
        return pd.DataFrame()  # Return empty dataframe on failure

def sync_metrics_tracking(sync_events, state):

    #using the state method, loop through the filtered df and gather metrics updating the state arguments each time and appending to a list to track it
    history = []
    try:
        for _, row in sync_events.iterrows(): # For index (ignore), row -> iterate through rows
            state.update(row["reserve0"], row["reserve1"]) # update the state of each variable with the new values from columns reservce0 and reserve1

            eth_external_price = get_binance_price()  # Using the free API no need for key I think 1500 requests per minute
            mispriced, uni_price = detect_mispricing(state.reserve0, state.reserve1, eth_external_price)

            if mispriced:
                direction = "buy" if uni_price < eth_external_price else "sell"
                print(f"Mispricing detected: Uniswap={uni_price}, External={eth_external_price}, Action={direction}")

            history.append({
                "timestamp": row["block_timestamp"],
                "block_number": row["block_number"],
                "reserve0": state.reserve0,
                "reserve1": state.reserve1
            })
        return pd.DataFrame(history)
    except Exception as e:
        print(f"Error tracking metrics: {e}")
        return pd.DataFrame()

# Run the tests in test_pool_tracking.py
def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_pool_tracking)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print("Some tests failed.")
    else:
        print("All tests passed successfully.")

# Main runner, run the functions and use negative checking to ensure file has been loaded, processing functions have been run,
if __name__ == "__main__":

    start_time = time.time()
    run_tests()
    state = UniswapV2State()
    STATE_FILE = "latest_state.json"
    state.load_from_json(STATE_FILE)  # Load state from file if it exists. Perhaps code stopped or outage etc

    df = load_file()
    if df is not None:
        try:
            sync_events = filter_sync_events(df) # Load the events of type Sync non-negative
            if not sync_events.empty:
                state_history_df = sync_metrics_tracking(sync_events, state) # Save each state to a list (history) + block number + timestamp
                # state_history_df.to_csv("state_history.csv", index=False) #Save history to CSV
                print("\nState History Sample:")
                print(state_history_df.head())

                # # Serialise current state
                state.serialise_to_json(STATE_FILE)

            else:
                print("No Sync events to process.")
        except Exception as e:
            print(f"Unexpected error during processing: {e}")

    print(f"\nDone in {time.time() - start_time:.2f} seconds.")
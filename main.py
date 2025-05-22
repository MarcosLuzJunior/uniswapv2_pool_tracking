import os
import pandas as pd
import ast
from dataclasses import dataclass, asdict
import time
import json
import unittest
import test_pool_tracking


@dataclass
class UniswapV2State:
    reserve0: int = 0
    reserve1: int = 0

    def update(self, reserve0: int, reserve1: int):
        self.reserve0 = reserve0
        self.reserve1 = reserve1

    # def serialize_to_json(self, file_path="latest_state.json"):
    #     try:
    #         with open(file_path, "w") as f:
    #             json.dump(asdict(self), f)
    #         print(f"State serialized to {file_path}")
    #     except Exception as e:
    #         print(f"Serialization error: {e}")

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
        sync_events = df[df["event_signature"] == "Sync(uint112,uint112)"].copy()
        sync_events["args"] = sync_events["args"].apply(ast.literal_eval)
        sync_events["reserve0"] = sync_events["args"].apply(lambda x: int(x[0]))
        sync_events["reserve1"] = sync_events["args"].apply(lambda x: int(x[1]))

        # Check if there are any negative values, and log/print them
        invalid_rows = sync_events[(sync_events["reserve0"] < 0) | (sync_events["reserve1"] < 0)]
        if not invalid_rows.empty:
            print("Warning: Negative reserve values detected and removed:")
            print(invalid_rows[["block_number", "reserve0", "reserve1"]])

        # Drop the negative instances, to discuss with Matt (is it malformed, part of the test etc) Keep only valid rows
        sync_events = sync_events[(sync_events["reserve0"] >= 0) & (sync_events["reserve1"] >= 0)]

        return sync_events
    except Exception as e:
        print(f"Error processing sync events: {e}")
        return pd.DataFrame()  # Return empty dataframe on failure

def sync_metrics_tracking(sync_events, state):
    #using the state class, loop through the filtered df and gather metrics updating the state arguments each time and appending to a list
    history = []
    try:
        for _, row in sync_events.iterrows():
            state.update(row["reserve0"], row["reserve1"])
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

    df = load_file()
    if df is not None:
        try:
            state = UniswapV2State()
            sync_events = filter_sync_events(df)
            if not sync_events.empty:
                state_history_df = sync_metrics_tracking(sync_events, state)
                # state_history_df.to_csv("state_history.csv", index=False) #Save history to CSV
                print("\nState History Sample:")
                print(state_history_df.head())

                # # Serialise current state
                # state.serialize_to_json()

            else:
                print("No Sync events to process.")
        except Exception as e:
            print(f"Unexpected error during processing: {e}")

    print(f"\nDone in {time.time() - start_time:.2f} seconds.")
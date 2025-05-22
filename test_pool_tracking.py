import unittest
import pandas as pd
from main import UniswapV2State, load_file, filter_sync_events, sync_metrics_tracking


class TestPoolTracking(unittest.TestCase):

    def test_uniswap_state_update(self):
        #Test if the method is working the class to update the variables
        state = UniswapV2State()
        state.update(1234, 5678)
        self.assertEqual(state.reserve0, 1234)
        self.assertEqual(state.reserve1, 5678)

    def test_filter_sync_events_valid(self):
        # Create a dummy DataFrame with a valid Sync event
        df = pd.DataFrame({
            "event_signature": ["Sync(uint112,uint112)"],
            "args": ["['1000', '2000']"],
            "block_timestamp": ["2020-05-19 01:07:09 UTC"],
            "block_number": [10093341]
        })

        filtered = filter_sync_events(df)
        self.assertEqual(filtered.iloc[0]['reserve0'], 1000)
        self.assertEqual(filtered.iloc[0]['reserve1'], 2000)

    # def test_filter_sync_events_invalid_args(self):
    #     # Invalid 'args' should fail gracefully, so need to check
    #     df = pd.DataFrame({
    #         "event_signature": ["Sync(uint112,uint112)"],
    #         "args": ["not a list"]
    #     })
    #     filtered = filter_sync_events(df)
    #     self.assertTrue(filtered.empty)

    def test_sync_metrics_tracking(self):
        #Check if the metrics we're supposed to track are being picked up ok
        df = pd.DataFrame({
            "block_timestamp": ["2020-05-19 01:07:09 UTC", "2020-05-19 01:08:09 UTC"],
            "block_number": [10093341, 10093342],
            "reserve0": [5000, 6000],
            "reserve1": [1000, 1500]
        })
        state = UniswapV2State()
        history = sync_metrics_tracking(df, state)
        self.assertEqual(len(history), 2)
        self.assertEqual(history.iloc[1]['reserve0'], 6000)
        self.assertEqual(history.iloc[1]['reserve1'], 1500)

    def test_load_file_returns_none(self):
        # Should return None or handle file-not-, because no file passed
        df = load_file()
        self.assertTrue(df is None or isinstance(df, pd.DataFrame))

if __name__ == '__main__':
    unittest.main()
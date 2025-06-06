# uniswapv2_pool_tracking
A Python script to process and track Uniswap V2 Sync(uint112,uint112) events and updates token reserves over timefrom CSV logs. Includes state management, data cleaning, historical reserve tracking, and automated testing.

It:
- Loads event data from a CSV file (expected in your Downloads folder)
- Filters for Sync events
- Tracks reserve0 and reserve1 using a state class
- Prints a history of reserve changes
- Runs basic tests on the functions

To run it:
1. Make sure you have Python 3.8+ and `pandas` installed (`pip install pandas`)
2. Place `uniswap_v2.csv` in your Downloads folder
3. Run the script with:

Observation V2 vs V3:
As a trader, V3 gives you better prices in active ranges, but you might hit a liquidity wall outside ranges (i.e. spread increases "dries")
As an LP, V3 lets you earn more with less capital if you manage your ranges well.

```bash
python main.py


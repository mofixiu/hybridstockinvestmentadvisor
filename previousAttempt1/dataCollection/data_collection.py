import yfinance as yf
import pandas as pd

def get_stock_data(symbol):
    print(f"Fetching full history for {symbol} using yfinance...")
    
    # 1. Download data (max history)
    # The ".LAGOS" suffix is often used for Nigerian stocks on Yahoo, 
    # but sometimes they are listed just by ticker. 
    # For US stocks, just use the symbol (e.g., 'AAPL', 'GOOG').
    # For Nigerian stocks, try 'GTCO.LG' or check Yahoo Finance website for the exact ticker.
    
    try:
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(period="max")
        
        # 2. Check if data is empty
        if data.empty:
            print(f"Error: No data found for {symbol}. Check the ticker symbol.")
            return

        # 3. Clean up (Yahoo gives extra columns we don't need)
        # We only keep: Open, High, Low, Close, Volume
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Rename columns to lowercase to match your other scripts
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        
        # 4. Save to CSV
        filename = f"{symbol}_market_data.csv"
        data.to_csv(filename)
        
        print(f"Success! Saved {len(data)} rows to {filename}")
        print(data.head())

    except Exception as e:
        print(f"An error occurred: {e}")

# --- TEST IT ---
# Try a US stock first to confirm it works
get_stock_data("MTNN.LG") 

# Try a Nigerian stock (Check Yahoo Finance for exact ticker)
# GTBank is usually 'GTCO.LG' on Yahoo
# get_stock_data("GTCO.LG")
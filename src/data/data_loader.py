import pandas as pd
import os

def load_and_clean_data(ticker):
    """
    Reads a raw CSV from Investing.com, cleans it, and saves it to 'processed'.
    """
    # 1. Construct File Paths
    # We assume you saved them in 'data/raw/'
    raw_path = f"data/raw/marketData/{ticker}.csv"
    processed_path = f"data/processed/{ticker}_clean.csv"
    
    # 2. Check if file exists
    if not os.path.exists(raw_path):
        print(f"❌ Error: {raw_path} not found. Did you download it?")
        return None
    
    print(f"🧹 Cleaning {ticker}...")
    
    # 3. Read CSV
    df = pd.read_csv(raw_path)
    
    # 4. Rename Columns to Standard Format (lowercase)
    # Investing.com usually gives: "Date", "Price", "Open", "High", "Low", "Vol.", "Change %"
    # We rename them to match what your model expects
    df.rename(columns={
        "Date": "date",
        "Price": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Vol.": "volume"
    }, inplace=True)
    
    # 5. Fix Data Types (The hard part)
    # Dates might be "Dec 12, 2024" -> convert to actual Python Date
    df['date'] = pd.to_datetime(df['date'])
    
    # Numbers might have commas "1,200.00" -> remove comma
    cols_to_fix = ['close', 'open', 'high', 'low']
    for col in cols_to_fix:
        if df[col].dtype == object: # if it looks like text
            df[col] = df[col].str.replace(',', '').astype(float)
            
    # Volume might have "M" or "K" (e.g., "1.5M")
    def clean_vol(x):
        if isinstance(x, str):
            x = x.replace(',', '')
            if 'K' in x: return float(x.replace('K', '')) * 1000
            if 'M' in x: return float(x.replace('M', '')) * 1000000
            if 'B' in x: return float(x.replace('B', '')) * 1000000000
        return float(x)
    
    if df['volume'].dtype == object:
        df['volume'] = df['volume'].apply(clean_vol)
    
    # DROP the "Change %" column (We don't need it for interpolation)
    if 'Change %' in df.columns:
        df = df.drop(columns=['Change %'])
    
    # --- NEW: INTERPOLATION LOGIC ---
    # 1. Set Date as Index
    df.set_index('date', inplace=True)
    
    # 2. Resample to Daily frequency ('D') to reveal missing days (weekends)
    df = df.resample('D').mean()
    
    # 3. Interpolate (Linear Fill)
    # This draws a straight line between Friday's price and Monday's price
    df.interpolate(method='linear', inplace=True)
    
    # 4. Reset Index to make 'date' a column again
    df.reset_index(inplace=True)
        
    # 6. Sort Oldest to Newest (Investing.com gives newest first)
    df = df.sort_values('date', ascending=True).reset_index(drop=True)
    
    # 7. Save to Processed Folder
    os.makedirs("data/processed", exist_ok=True) # Create folder if missing
    df.to_csv(processed_path, index=False)
    
    print(f"✅ Success! Data interpolated and saved to {processed_path}")
    print(df.head())
    return df

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # List the tickers you downloaded
    tickers = ["GTCO", "ZENITH", "DANGCEM", "MTNN","WAPCO"]
    
    for t in tickers:
        load_and_clean_data(t)
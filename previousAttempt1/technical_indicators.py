import pandas as pd
import pandas_ta as ta

def add_technical_indicators(csv_file):
    # 1. Load your saved data
    print(f"Loading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # 2. Clean up: Ensure we have the right columns
    # pandas_ta needs 'close' column to calculate indicators
    
    # 3. Calculate RSI (Relative Strength Index)
    # Strategy: RSI < 30 is "Oversold" (Cheap), RSI > 70 is "Overbought" (Expensive)
    df['RSI'] = df.ta.rsi(length=14)
    
    # 4. Calculate EMA (Exponential Moving Average)
    # Strategy: If Price > EMA, it's an Uptrend.
    df['EMA_50'] = df.ta.ema(length=50)
    
    # 5. Calculate MACD (Momentum)
    # Strategy: Measures the speed of price movement
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)
    
    # 6. Drop the "NaN" rows 
    # (The first 50 days won't have an EMA_50 because they need 50 days of history)
    df = df.dropna()
    
    # 7. Save the "Smart" Data
    output_file = "AAPL_engineered_data.csv"
    df.to_csv(output_file, index=False)
    
    print(f"Success! Added indicators. Saved to {output_file}")
    print(df[['close', 'RSI', 'EMA_50']].tail()) # Show the last 5 rows

# Run it on your downloaded Apple data
add_technical_indicators('AAPL_market_data.csv')
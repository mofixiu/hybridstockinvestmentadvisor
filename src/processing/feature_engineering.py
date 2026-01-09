import pandas as pd
import pandas_ta as ta
import os

def add_technical_indicators(ticker="GTCO"):
    print(f"🛠️ Engineering Features for {ticker}...")
    
    # 1. Load the Fused Data
    input_path = "data/processed/FINAL_TRAINING_DATA.csv"
    output_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    
    if not os.path.exists(input_path):
        print(f"❌ Error: {input_path} not found. Run src/data_fusion.py first.")
        return

    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True) # Index by date for calculations
    
    # 2. Calculate Indicators (The Magic)
    
    # RSI (Relative Strength Index) - Momentum
    # Signal: >70 is Overbought (Sell), <30 is Oversold (Buy)
    df['RSI'] = df.ta.rsi(length=14)
    
    # EMA (Exponential Moving Average) - Trend
    # EMA 50 is the "Medium Term" trend
    df['EMA_50'] = df.ta.ema(length=50)
    # EMA 200 is the "Long Term" trend (Golden Cross/Death Cross)
    df['EMA_200'] = df.ta.ema(length=200)
    
    # MACD (Moving Average Convergence Divergence) - Trend Reversal
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    # pandas_ta returns 3 columns, we join them back
    df = df.join(macd)
    
    # Bollinger Bands - Volatility
    bbands = df.ta.bbands(length=20, std=2)
    df = df.join(bbands)
    
    # 3. Clean NaN Values
    # The first 200 days will have NaN because EMA_200 needs 200 days of history.
    # We must drop them, or the AI will crash.
    print(f"   - Original Row Count: {len(df)}")
    df.dropna(inplace=True)
    print(f"   - New Row Count (after dropping warm-up days): {len(df)}")
    
    # 4. Target Creation (What are we predicting?)
    # Let's define: 1 (Buy) if price goes UP tomorrow, 0 (Sell/Hold) if price goes DOWN
    # We shift the 'close' price backwards by 1 day to compare
    df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # 5. Save
    df.reset_index(inplace=True)
    df.to_csv(output_path, index=False)
    
    print(f"✅ Success! Features added. Saved to {output_path}")
    print(df[['date', 'close', 'RSI', 'EMA_50', 'Target']].tail())

if __name__ == "__main__":
    add_technical_indicators("GTCO")
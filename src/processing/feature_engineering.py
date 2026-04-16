# import pandas as pd
# import pandas_ta as ta
# import os

# def add_technical_indicators(ticker="GTCO"):
#     print(f"🛠️ Engineering Features for {ticker}...")
    
#     # 1. Load the Fused Data
#     input_path = "data/processed/FINAL_TRAINING_DATA.csv"
#     output_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    
#     if not os.path.exists(input_path):
#         print(f"❌ Error: {input_path} not found. Run src/data_fusion.py first.")
#         return

#     df = pd.read_csv(input_path)
#     df['date'] = pd.to_datetime(df['date'])
#     df.set_index('date', inplace=True) # Index by date for calculations
    
#     # 2. Calculate Indicators (The Magic)
    
#     # RSI (Relative Strength Index) - Momentum
#     # Signal: >70 is Overbought (Sell), <30 is Oversold (Buy)
#     df['RSI'] = df.ta.rsi(length=14)
    
#     # EMA (Exponential Moving Average) - Trend
#     # EMA 50 is the "Medium Term" trend
#     df['EMA_50'] = df.ta.ema(length=50)
#     # EMA 200 is the "Long Term" trend (Golden Cross/Death Cross)
#     df['EMA_200'] = df.ta.ema(length=200)
    
#     # MACD (Moving Average Convergence Divergence) - Trend Reversal
#     macd = df.ta.macd(fast=12, slow=26, signal=9)
#     # pandas_ta returns 3 columns, we join them back
#     df = df.join(macd)
    
#     # Bollinger Bands - Volatility
#     bbands = df.ta.bbands(length=20, std=2)
#     df = df.join(bbands)
    
#     # 3. Clean NaN Values
#     # The first 200 days will have NaN because EMA_200 needs 200 days of history.
#     # We must drop them, or the AI will crash.
#     print(f"   - Original Row Count: {len(df)}")
#     df.dropna(inplace=True)
#     print(f"   - New Row Count (after dropping warm-up days): {len(df)}")
    
#     # 4. Target Creation (What are we predicting?)
#     # Let's define: 1 (Buy) if price goes UP tomorrow, 0 (Sell/Hold) if price goes DOWN
#     # We shift the 'close' price backwards by 1 day to compare
#     df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
#     # 5. Save
#     df.reset_index(inplace=True)
#     df.to_csv(output_path, index=False)
    
#     print(f"✅ Success! Features added. Saved to {output_path}")
#     print(df[['date', 'close', 'RSI', 'EMA_50', 'Target']].tail())

# if __name__ == "__main__":
#     add_technical_indicators("GTCO")
import pandas as pd
import pandas_ta as ta
import os

def add_technical_indicators():
    print("🛠️ Engineering Features for GLOBAL Dataset (Preventing Data Bleed)...")
    
    input_path = "data/processed/FINAL_TRAINING_DATA.csv"
    output_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    
    if not os.path.exists(input_path):
        print(f"❌ Error: {input_path} not found. Run src/processing/data_fusion.py first.")
        return

    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    safe_dfs = []
    
    # 🚨 THE FIX: Group by ticker and do the math in absolute isolation
    for ticker, group_df in df.groupby('ticker'):
        print(f"   - Crunching technicals for {ticker}...")
        group_df = group_df.sort_index() # Ensure dates are strictly oldest to newest
        
        # Calculate Indicators safely
        group_df['RSI'] = group_df.ta.rsi(length=14)
        group_df['EMA_50'] = group_df.ta.ema(length=50)
        group_df['EMA_200'] = group_df.ta.ema(length=200)
        
        macd = group_df.ta.macd(fast=12, slow=26, signal=9)
        group_df = group_df.join(macd)
        
        bbands = group_df.ta.bbands(length=20, std=2)
        group_df = group_df.join(bbands)
        
        # Safely create Target: Did THIS specific stock go up tomorrow?
        group_df['Target'] = (group_df['close'].shift(-1) > group_df['close']).astype(int)
        
        # Drop the NaN warm-up days for this specific stock
        group_df.dropna(inplace=True)
        safe_dfs.append(group_df)
        
    # Stitch the safe datasets back together into one master CSV
    final_df = pd.concat(safe_dfs)
    final_df.reset_index(inplace=True)
    
    final_df.to_csv(output_path, index=False)
    print(f"\n✅ Success! Multi-Stock Features added safely. Saved to {output_path}")

if __name__ == "__main__":
    add_technical_indicators()
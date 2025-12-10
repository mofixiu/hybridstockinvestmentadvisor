import pandas as pd
import numpy as np

def fuse_data():
    # 1. Load the Engineered Market Data
    market_df = pd.read_csv("AAPL_engineered_data.csv")
    
    # 2. Simulate Sentiment Data (Since we don't have 10 years of tweets yet)
    # In real life, this would come from your FinBERT script.
    print("Generating mock sentiment scores for fusion...")
    
    # Generate random sentiment between 0 (Negative) and 1 (Positive)
    # We create as many rows as the market data
    market_df['sentiment_score'] = np.random.uniform(0, 1, len(market_df))
    
    # 3. Create the "Target" (What we want to predict)
    # If tomorrow's price is higher than today's, Target = 1 (Buy), else 0 (Sell)
    # We shift the 'close' column up by -1 to compare today vs tomorrow
    market_df['tomorrow_close'] = market_df['close'].shift(-1)
    market_df['target'] = (market_df['tomorrow_close'] > market_df['close']).astype(int)
    
    # Drop the last row (since it has no 'tomorrow' to compare to)
    market_df = market_df.dropna()
    
    # 4. Save the Final Training Set
    market_df.to_csv("FINAL_TRAINING_DATA.csv", index=False)
    print("Fusion Complete! Created 'FINAL_TRAINING_DATA.csv'.")
    print(market_df[['Date', 'RSI', 'sentiment_score', 'target']].tail())

fuse_data()
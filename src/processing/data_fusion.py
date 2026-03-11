# import pandas as pd
# import os

# def fuse_datasets(ticker="GTCO"):
#     print(f"🔗 Fusing data for {ticker}...")
    
#     # 1. Load Files
#     price_path = f"data/processed/{ticker}_clean.csv"
#     sent_path = "data/processed/sentiment_daily_scored.csv"
    
#     if not os.path.exists(price_path):
#         print(f"❌ Error: {price_path} not found. Run data_loader.py first.")
#         return
#     if not os.path.exists(sent_path):
#         print(f"❌ Error: {sent_path} not found. Run sentiment_scoring.py first.")
#         return

#     df_price = pd.read_csv(price_path)
#     df_sent = pd.read_csv(sent_path)
    
#     # 2. Standardize Dates (Crucial for merging)
#     # Ensure both are just "YYYY-MM-DD" with no time info
#     df_price['date'] = pd.to_datetime(df_price['date']).dt.date
#     df_sent['date'] = pd.to_datetime(df_sent['date']).dt.date
    
#     # 3. Merge (Left Join)
#     # We take the Price Data (Main) and attach Sentiment Data where dates match
#     fused_df = pd.merge(df_price, df_sent, on='date', how='left')
    
#     # 4. Fill Missing Sentiment
#     # For days with no tweets (e.g., 2019 or weekends), we assume Neutral (0.0)
#     fused_df['avg_sentiment'] = fused_df['avg_sentiment'].fillna(0.0)
    
#     # 5. Save Final Training Data
#     output_path = "data/processed/FINAL_TRAINING_DATA.csv"
#     fused_df.to_csv(output_path, index=False)
    
#     print(f"✅ Success! Fused data saved to {output_path}")
#     print(f"   - Total Rows: {len(fused_df)}")
#     print(f"   - Sample with Sentiment:\n{fused_df[fused_df['avg_sentiment'] != 0].head()}")

# if __name__ == "__main__":
#     fuse_datasets("GTCO")
import pandas as pd
import os

def fuse_global_dataset():
    print("🔗 Fusing GLOBAL data (Multi-Stock Training Set)...")
    
    # Use 5 diverse stocks to teach the AI different price scales
    training_tickers = ["GTCO", "ZENITH", "DANGCEM", "MTNN", "WAPCO"]
    all_fused_data = []
    
    # The sentiment file is the same for all (it's market-wide sentiment for now)
    sent_path = "data/processed/sentiment_daily_scored.csv"
    if not os.path.exists(sent_path):
        print(f"❌ Error: {sent_path} not found. Run sentiment_scoring.py first.")
        return

    df_sent = pd.read_csv(sent_path)
    df_sent['date'] = pd.to_datetime(df_sent['date']).dt.date
    
    for ticker in training_tickers:
        price_path = f"data/processed/{ticker}_clean.csv"
        
        if not os.path.exists(price_path):
            print(f"⚠️ Warning: {price_path} not found. Skipping {ticker} for training.")
            continue
            
        df_price = pd.read_csv(price_path)
        df_price['date'] = pd.to_datetime(df_price['date']).dt.date
        
        # Merge Price and Sentiment
        fused_df = pd.merge(df_price, df_sent, on='date', how='left')
        fused_df['avg_sentiment'] = fused_df['avg_sentiment'].fillna(0.0)
        
        all_fused_data.append(fused_df)
        print(f"   ✅ Added {ticker} to Global Training Set.")

    # Combine all 5 stocks into one massive dataset
    if all_fused_data:
        global_training_df = pd.concat(all_fused_data, ignore_index=True)
        
        output_path = "data/processed/FINAL_TRAINING_DATA.csv"
        global_training_df.to_csv(output_path, index=False)
        
        print(f"\n🎉 Success! Global training data saved to {output_path}")
        print(f"   - Total Training Rows: {len(global_training_df)}")
    else:
        print("❌ Failed to create global dataset.")

if __name__ == "__main__":
    fuse_global_dataset()
import pandas as pd
import re
import os

# Define keywords that suggest a post is actually about Finance/Nigeria
# If a Reddit post doesn't have at least ONE of these, we throw it away.
SLANG_MAP = {
    "hodl": "hold",
    "fomo": "fear of missing out",
    "ath": "all time high",
    "btd": "buy the dip",
    "stonks": "stocks",
    "bullish": "positive",
    "bearish": "negative",
    "bagholder": "investor losing money",
    "moving": "the stock is rising",
    "To the Moon": "the stock is rising",
}
RELEVANCE_KEYWORDS = [
    # General Finance
    "stock", "market", "price", "invest", "naira", "bank", "dividend", "profit", 
    "loss", "shares", "plc", "economy", "inflation", "bearish", "bullish", "dip", 
    "pump", "crypto", "up", "trend", "down",
    
    # Nigerian Banks & Financial Institutions
    "gtco", "zenith", "uba", "access", "fcmb", "fidelity", "stanbic", "sterling",
    "unity", "wema", "polaris", "ecobank", "firstbank", "guaranty trust",
    
    # Major Nigerian Companies
    "dangote", "mtnn", "nestle", "flour mills", "seplat", "oando", "total",
    "mobil", "guinness", "nigerian breweries", "nbplc", "unilever", "cadbury",
    "presco", "honeywell", "transcorp", "lafarge", "buacement",
    
    # Nigerian Market Terms
    "ngx", "nse", "nigerian stock exchange", "all share index", "asi", "cbn",
    "central bank", "sec nigeria", "nasd", "otc", "fmdq", "quoted", "delisted",
    
    # Trading & Investment Terms
    "portfolio", "equity", "bond", "treasury", "mutual fund", "asset management",
    "hedge", "long", "short", "buy", "sell", "hold", "rally", "crash", "correction",
    "resistance", "support", "breakout", "volume", "liquidity", "volatility",
    
    # Economic Indicators
    "gdp", "interest rate", "monetary policy", "fiscal", "budget", "debt",
    "crude oil", "forex", "exchange rate", "dollar", "euro", "pounds",
    "unemployment", "consumer price index", "cpi", "manufacturing",
    
    # Market Sentiment
    "bull run", "bear market", "all time high", "ath", "buy the dip", "btd",
    "hodl", "moon", "rocket", "gains", "returns", "roi", "yield", "earnings",
    "quarterly results", "financial statement", "earnings per share", "eps",
    "price to earnings", "pe ratio", "book value",
    
    # Nigerian Context
    "lagos", "abuja", "nigeria", "african", "west africa", "subsaharan",
    "emerging market", "frontier market", "naira devaluation", "petrol",
    "fuel subsidy", "power sector", "telco", "telecommunications"
]

def clean_text(text):
    """
    Standard text cleaning: lowercase, remove URLs, remove junk.
    """
    if not isinstance(text, str):
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove URLs (http://...)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # 3. Remove User Handles (@username) - Common in tweets
    text = re.sub(r'\@\w+', '', text)
    
    # 4. Handle Slang (NEW)
    for slang, real_meaning in SLANG_MAP.items():
        text = re.sub(r'\b' + slang + r'\b', real_meaning, text)
    
    # 5. Remove Emojis (NEW - Basic ASCII filter)
    # This removes anything that isn't a standard letter, number, or punctuation
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    
    # 6. Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def is_relevant(text):
    """
    Returns True if the text contains at least one financial keyword.
    """
    # Simple keyword matching
    for word in RELEVANCE_KEYWORDS:
        if word in text:
            return True
    return False

def preprocess_file(file_path, ticker_name="GTCO"):
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return None
    
    print(f"🧹 Processing {file_path}...")
    df = pd.read_csv(file_path)
    
    # 1. Standardize Column Names
    # Reddit has 'title', Twitter has 'text'. Let's make them all 'text'.
    if 'title' in df.columns:
        df.rename(columns={'title': 'text'}, inplace=True)
    
    # Ensure 'text' column exists
    if 'text' not in df.columns:
        print(f"❌ Error: No 'text' or 'title' column found in {file_path}")
        return None

    # 2. Apply Cleaning
    df['clean_text'] = df['text'].apply(clean_text)
    
    # 3. Apply Filtering (The "My Little Pony" Remover)
    # We only keep rows where 'is_relevant' is True
    initial_count = len(df)
    df = df[df['clean_text'].apply(is_relevant)]
    final_count = len(df)
    
    removed = initial_count - final_count
    print(f"   - Removed {removed} irrelevant posts. Kept {final_count}.")
    
    # 4. Add Ticker Column (So we know which stock this belongs to)
    df['ticker'] = ticker_name
    
    return df

def run_pipeline():
    # List of your raw files
    files_to_process = [
        ("data/raw/sentimentData/GTCO_tweets.csv", "GTCO"),
        ("data/raw/sentimentData/GTCO_reddit.csv", "GTCO"),
        ("data/raw/sentimentData/Nigeria Economy_reddit.csv", "Economy")
    ]
    
    all_data = []
    
    for file_path, ticker in files_to_process:
        processed_df = preprocess_file(file_path, ticker)
        if processed_df is not None:
            all_data.append(processed_df)
    
    # Combine everything into one big "Master Sentiment Dataset"
    if all_data:
        master_df = pd.concat(all_data, ignore_index=True)
        
        # Save to processed folder
        os.makedirs("data/processed", exist_ok=True)
        output_path = "data/processed/sentiment_master_clean.csv"
        master_df.to_csv(output_path, index=False)
        print(f"\n✅ SUCCESS! Master dataset saved to {output_path}")
        print(master_df[['date', 'source', 'clean_text']].head())
    else:
        print("❌ No data processed.")

if __name__ == "__main__":
    run_pipeline()
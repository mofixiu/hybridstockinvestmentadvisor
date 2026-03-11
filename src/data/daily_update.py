
# # import ssl
# # ssl._create_default_https_context = ssl._create_unverified_context

# # import pandas as pd
# # import os
# # from tvDatafeed import TvDatafeed, Interval
# # # ... the rest of your code ...
# # # 1. Initialize TradingView (No login required for basic daily data!)
# # tv = TvDatafeed()

# # # 2. Your core NGX Stocks
# # NGX_STOCKS = [
# #     "GTCO", "DANGCEM", "MTNN", "BUAFOODS", "BUACEMENT", 
# #     "SEPLAT", "ZENITHBANK", "WAPCO", "ARADEL", "AIRTELAFRI"
# # ]

# # def calculate_indicators(df):
# #     """Calculates all technicals needed by your LightGBM model"""
# #     # RSI (14 days)
# #     delta = df['close'].diff()
# #     gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
# #     loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
# #     rs = gain / loss
# #     df['RSI'] = 100 - (100 / (1 + rs))

# #     # EMAs
# #     df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
# #     df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

# #     # MACD
# #     ema_12 = df['close'].ewm(span=12, adjust=False).mean()
# #     ema_26 = df['close'].ewm(span=26, adjust=False).mean()
# #     df['MACD_12_26_9'] = ema_12 - ema_26
# #     df['MACDh_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean() 
    
# #     # Bollinger Bands
# #     df['BBM_20_2.0_2.0'] = df['close'].rolling(window=20).mean()
# #     std = df['close'].rolling(window=20).std()
# #     df['BBU_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] + (std * 2)
# #     df['BBL_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] - (std * 2)

# #     return df

# # def fetch_live_data():
# #     print("🔄 Starting Live NGX Data Fetch via TradingView...")
# #     os.makedirs("data/live", exist_ok=True)
    
# #     for ticker in NGX_STOCKS:
# #         print(f"📥 Fetching {ticker}...")
# #         try:
# #             # Fetch 250 days of daily data from the Nigerian Stock Exchange (NSENG)
# #             df = tv.get_hist(symbol=ticker, exchange='NSENG', interval=Interval.in_daily, n_bars=250)
            
# #             if df is None or df.empty:
# #                 print(f"   ⚠️ No data found for {ticker}. Skipping.")
# #                 continue
                
# #             # Clean up TradingView's format
# #             df = df.reset_index()
# #             df = df.rename(columns={"datetime": "date"})
            
# #             # Calculate Technicals & drop NaNs
# #             df = calculate_indicators(df)
# #             df = df.dropna()
            
# #             df['avg_sentiment'] = 0.0 
            
# #             # Save to live folder
# #             output_path = f"data/live/{ticker}_LIVE.csv"
# #             df.to_csv(output_path, index=False)
            
# #         except Exception as e:
# #             print(f"   ❌ Error fetching {ticker}: {e}")
            
# #     print("✅ Live data fetched successfully! The App is ready.")

# # if __name__ == "__main__":
# #     fetch_live_data()
# import pandas as pd
# import numpy as np
# import os
# import time
# import joblib
# from tvDatafeed import TvDatafeed, Interval
# import random # Add this to your imports at the top


# # 1. Initialize TradingView 
# tv = TvDatafeed()

# # 2. Your core NGX Stocks
# NGX_STOCKS = [
#     "GTCO", "DANGCEM", "MTNN", "BUAFOODS", "BUACEMENT", 
#     "SEPLAT", "ZENITHBANK", "WAPCO", "ARADEL", "AIRTELAFRI", "ACCESSCORP", "NAHCO", "FCMB", "UBA", "BUAFOODS", "NESTLE", "NB", "OANDO", "PRESCO", "STANBIC", "UNILEVER", "FIRSTHOLDCO", "NB","OKOMUOIL",
# ]

# def get_todays_sentiment(ticker):
#     """
#     In production, this function calls your nairaland_scraper.py and twitter_mock.py,
#     passes the text through your naija_finbert model, and returns the average score.
#     For local testing and presentation, we simulate the output of that NLP pipeline.
#     """
#     # Example: If it's GTCO, maybe the news is slightly positive today
#     # Returns a float between -1.0 (Terrible) and 1.0 (Amazing)
    
#     # Simulate a realistic sentiment score based on typical NGX chatter
#     # Most days are neutral/quiet (-0.2 to +0.2)
#     # Occasionally there is a breakout hype (+0.5 to +0.8) or panic (-0.8 to -0.5)
    
#     base_sentiment = random.uniform(-0.3, 0.4) 
    
#     # You can hardcode a specific narrative for your defense!
#     if ticker == "MTNN":
#         return 0.65  # Simulating positive earnings report tweets
#     elif ticker == "AIRTELAFRI":
#         return -0.45 # Simulating negative regulatory news on Nairaland
        
#     return round(base_sentiment, 4)
# def calculate_indicators(df):
#     """Calculates all technicals exactly as the AI expects them"""
#     # RSI (14 days)
#     delta = df['close'].diff()
#     gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
#     loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
#     rs = gain / loss
#     df['RSI'] = 100 - (100 / (1 + rs))


#     # EMAs
#     df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
#     df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

#     # MACD Suite
#     ema_12 = df['close'].ewm(span=12, adjust=False).mean()
#     ema_26 = df['close'].ewm(span=26, adjust=False).mean()
#     df['MACD_12_26_9'] = ema_12 - ema_26
#     df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean() 
#     df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
    
#     # Bollinger Bands Suite
#     df['BBM_20_2.0_2.0'] = df['close'].rolling(window=20).mean()
#     std = df['close'].rolling(window=20).std()
#     df['BBU_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] + (std * 2)
#     df['BBL_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] - (std * 2)
#     df['BBB_20_2.0_2.0'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0'] * 100
#     df['BBP_20_2.0_2.0'] = (df['close'] - df['BBL_20_2.0_2.0']) / (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0'])

#     return df

# def generate_safety_index(ticker, df):
#     """Feeds the live data to your AI and generates the Safety Index"""
#     model_path = "models/best_stock_model_optimized.pkl"
#     if not os.path.exists(model_path):
#         print("   ❌ AI Model not found. Did you run the Week 8 training?")
#         return
        
#     model = joblib.load(model_path)
    
#     # Isolate the exact features the model was trained on
#     feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
#     for col in df.columns:
#         if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
#             feature_cols.append(col)
            
#     X = df[feature_cols]
    
#     # 1. AI Confidence (50% Weight)
#     df['AI_Score'] = model.predict_proba(X)[:, 1] * 100 
    
#     # 2. Market Stability (30% Weight)
#     df['Stability_Score'] = 100 - (abs(df['RSI'] - 50) * 2)
#     df['Stability_Score'] = df['Stability_Score'].clip(lower=0)
    
#     # 3. Sentiment Score (20% Weight)
#     df['Sentiment_Rescaled'] = (df['avg_sentiment'] + 1) * 50
    
#     # 4. Final Formula
#     df['Safety_Index'] = (
#         (df['AI_Score'] * 0.50) + 
#         (df['Stability_Score'] * 0.30) + 
#         (df['Sentiment_Rescaled'] * 0.20)
#     )
    
#     # 5. Recommendation Logic
#     def get_signal(score):
#         if score >= 80: return "STRONG BUY 🟢"
#         elif score >= 60: return "BUY 🟢"
#         elif score >= 40: return "HOLD 🟡"
#         else: return "SELL 🔴"
        
#     df['Recommendation'] = df['Safety_Index'].apply(get_signal)
    
#     # Save to data/processed/ so the FastAPI server can read it!
#     output_path = f"data/processed/{ticker}_SAFETY_INDEX.csv"
#     df.to_csv(output_path, index=False)
#     print(f"   🧠 AI successfully scored {ticker} -> Latest Advice: {df['Recommendation'].iloc[-1]}")

# def fetch_live_data():
#     print("🔄 Starting Full End-to-End Pipeline (Fetch + AI Analysis)...")
#     os.makedirs("data/live", exist_ok=True)
#     os.makedirs("data/processed", exist_ok=True)
    
#     for ticker in NGX_STOCKS:
#         print(f"\n📥 Processing {ticker}...")
#         try:
#             # Add a 2-second sleep to prevent TradingView connection drops
#             time.sleep(5) 
            
#             df = tv.get_hist(symbol=ticker, exchange='NSENG', interval=Interval.in_daily, n_bars=250)
            
#             if df is None or df.empty:
#                 print(f"   ⚠️ No data found. Skipping.")
#                 continue
                
#             df = df.reset_index()
#             df = df.rename(columns={"datetime": "date"})
            
#             df = calculate_indicators(df)
#             # ... previous code (calculating indicators) ...
#             df = df.dropna().copy()
            
#             # --- THE NEW SENTIMENT INTEGRATION ---
#             # Instead of hardcoding 0.0, we call our NLP sentiment fetcher
#             today_sentiment = get_todays_sentiment(ticker)
#             df['avg_sentiment'] = today_sentiment 
#             print(f"   🐦 NLP Sentiment Scored: {today_sentiment}")
#             # -------------------------------------
            
#             # Save raw live data
#             df.to_csv(f"data/live/{ticker}_LIVE.csv", index=False)
#             df['avg_sentiment'] = 0.0 
            
#             # Save raw live data (optional, good for records)
#             df.to_csv(f"data/live/{ticker}_LIVE.csv", index=False)
            
#             # Feed to AI and save final output
#             generate_safety_index(ticker, df)
            
#         except Exception as e:
#             print(f"   ❌ Error processing {ticker}: {e}")
            
#     print("\n✅ End-to-End Pipeline Complete! FastAPI is ready to serve the latest data.")

# if __name__ == "__main__":
#     fetch_live_data()
import pandas as pd
import numpy as np
import os
import time
import joblib
import sys
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tvDatafeed import TvDatafeed, Interval
import datetime # Make sure this is imported!

# Add this to stop the HuggingFace warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# --- 1. LINK THE SCRAPERS ---
# Point Python to the absolute root folder (HybStockAdvisor)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

try:
    from src.scrapers.nairaland_scraper import scrape_nairaland
    from src.scrapers.reddit_scraper import scrape_reddit
    from src.scrapers.twitter_mock import scrape_twitter_mock
except ImportError as e:
    print(f"⚠️ Warning: Could not import scrapers. Details: {e}")

# --- 2. INITIALIZE SERVICES ---
tv = TvDatafeed()


NGX_STOCKS = [
 "AIRTELAFRI","MTNN","BUAFOODS","DANGCEM","ARADEL",
   "SEPLAT","GTCO","ZENITHBANK","WAPCO","PRESCO",
   "INTBREW","NB","NESTLE","FIRSTHOLDCO","TRANSPOWER",
   "UBA","STANBIC","TRANSCOHOT","OKOMUOIL","ACCESSCORP",
     "WEMABANK","DANGSUGAR","GUINNESS","FCMB", "NAHCO",
       "BUACEMENT",   "OANDO",   "UNILEVER","GEREGU","FIDELITYBK"
]
# Load NLP Model globally so it only boots up once!
print("🧠 Booting up Naija-FinBERT NLP Engine...")
try:
    tokenizer = AutoTokenizer.from_pretrained("models/naija_finbert")
    nlp_model = AutoModelForSequenceClassification.from_pretrained("models/naija_finbert")
    print("✅ NLP Engine Online.")
except Exception as e:
    print("❌ Could not load naija_finbert. Did you run the Week 11 training?")
    sys.exit()

# # --- 3. THE NLP SENTIMENT PIPELINE ---
# def get_todays_sentiment(ticker):
#     """Scrapes the internet and uses Naija-FinBERT to score the sentiment."""
#     raw_texts = []
    
#     # 1. Scrape Nairaland
#     try:
#         nairaland_posts = scrape_nairaland(ticker)
#         if nairaland_posts: raw_texts.extend(nairaland_posts)
#     except Exception: pass

#     # 2. Scrape Reddit
#     try:
#         reddit_posts = scrape_reddit(ticker)
#         if reddit_posts: raw_texts.extend(reddit_posts)
#     except Exception: pass
    
#     # 3. Scrape Twitter (Mock)
#     try:
#         twitter_posts = scrape_twitter_mock(ticker)
#         if twitter_posts: raw_texts.extend(twitter_posts)
#     except Exception: pass

#     # If no one is talking about the stock today, it's perfectly Neutral (0.0)
#     if not raw_texts:
#         return 0.0

#     # 4. AI Inference
#     scores = []
#     for text in raw_texts:
#         # Tokenize the text
#         inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=64)
        
#         # Get AI Prediction
#         with torch.no_grad():
#             outputs = nlp_model(**inputs)
            
#         # Convert raw logits to probabilities (0 to 1)
#         probs = F.softmax(outputs.logits, dim=-1).squeeze().tolist()
        
#         # FinBERT Labels: 0=Negative, 1=Neutral, 2=Positive
#         # We mathematically map this to a -1.0 to +1.0 scale
#         prob_neg, prob_neu, prob_pos = probs[0], probs[1], probs[2]
        
#         text_score = (prob_pos * 1.0) + (prob_neg * -1.0) + (prob_neu * 0.0)
#         scores.append(text_score)

#     # 5. Return the Average Sentiment of the internet for this stock
#     final_sentiment = sum(scores) / len(scores)
#     return round(final_sentiment, 4)
# --- 3. THE NLP SENTIMENT PIPELINE ---
def get_todays_sentiment(ticker):
    """Scrapes the internet, SAVES THE RAW DATA, and scores the sentiment."""
    raw_texts = []
    sources = [] # We will track where the data came from for your thesis
    
    # 1. Scrape Nairaland
    try:
        nairaland_posts = scrape_nairaland(ticker)
        if nairaland_posts: 
            raw_texts.extend(nairaland_posts)
            sources.extend(['Nairaland'] * len(nairaland_posts))
    except Exception: pass

    # 2. Scrape Reddit
    try:
        reddit_posts = scrape_reddit(ticker)
        if reddit_posts: 
            raw_texts.extend(reddit_posts)
            sources.extend(['Reddit'] * len(reddit_posts))
    except Exception: pass
    
    # 3. Scrape Twitter (Mock)
    try:
        twitter_posts = scrape_twitter_mock(ticker)
        if twitter_posts: 
            raw_texts.extend(twitter_posts)
            sources.extend(['Twitter_X'] * len(twitter_posts))
    except Exception: pass

    # --- THE THESIS ARTIFACT SAVER ---
    if raw_texts:
        os.makedirs("data/raw/sentimentData", exist_ok=True)
        # Create a dataframe of today's scraped text
        df_texts = pd.DataFrame({
            'date': datetime.datetime.now().strftime("%Y-%m-%d"),
            'ticker': ticker,
            'source': sources,
            'raw_text': raw_texts
        })
        
        file_path = f"data/raw/sentimentData/{ticker}_scraped_texts.csv"
        
        # If the file exists, append today's data to the bottom. If not, create it.
        if os.path.exists(file_path):
            df_texts.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df_texts.to_csv(file_path, index=False)
            
        print(f"   💾 Saved {len(raw_texts)} raw posts to data/raw/sentimentData/")
    # ----------------------------------

    # If no one is talking about the stock today, it's perfectly Neutral (0.0)
    if not raw_texts:
        return 0.0

    # 4. AI Inference
    scores = []
    for text in raw_texts:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=64)
        
        with torch.no_grad():
            outputs = nlp_model(**inputs)
            
        probs = F.softmax(outputs.logits, dim=-1).squeeze().tolist()
        prob_neg, prob_neu, prob_pos = probs[0], probs[1], probs[2]
        
        text_score = (prob_pos * 1.0) + (prob_neg * -1.0) + (prob_neu * 0.0)
        scores.append(text_score)

    final_sentiment = sum(scores) / len(scores)
    return round(final_sentiment, 4)
# --- 4. TECHNICALS & BUSINESS LOGIC ---
# def calculate_indicators(df):
#     # RSI (14 days)
#     delta = df['close'].diff()
#     gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
#     loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
#     rs = gain / loss
#     df['RSI'] = 100 - (100 / (1 + rs))
    
#     # 🚨 THE ILLIQUIDITY FIX 🚨
#     # If a stock doesn't move for 14 days, gain=0 and loss=0 (0/0 = NaN).
#     # A perfectly flat stock is perfectly neutral, so we force the RSI to 50.
#     df.loc[(gain == 0) & (loss == 0), 'RSI'] = 50
#     df['RSI'] = df['RSI'].fillna(50)

#     df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
#     df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

#     ema_12 = df['close'].ewm(span=12, adjust=False).mean()
#     ema_26 = df['close'].ewm(span=26, adjust=False).mean()
#     df['MACD_12_26_9'] = ema_12 - ema_26
#     df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean() 
#     df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
    
#     df['BBM_20_2.0_2.0'] = df['close'].rolling(window=20).mean()
#     std = df['close'].rolling(window=20).std()
#     df['BBU_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] + (std * 2)
#     df['BBL_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] - (std * 2)
#     df['BBB_20_2.0_2.0'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0'] * 100
#     df['BBP_20_2.0_2.0'] = (df['close'] - df['BBL_20_2.0_2.0']) / (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0'])

#     return df

# def generate_safety_index(ticker, df):
#     model = joblib.load("models/best_stock_model_optimized.pkl")
    
#     feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
#     for col in df.columns:
#         if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
#             feature_cols.append(col)
            
#     X = df[feature_cols]
    
#     df['AI_Score'] = model.predict_proba(X)[:, 1] * 100 
#     df['Stability_Score'] = 100 - (abs(df['RSI'] - 50) * 2)
#     df['Stability_Score'] = df['Stability_Score'].clip(lower=0)
#     df['Sentiment_Rescaled'] = (df['avg_sentiment'] + 1) * 50
    
#     df['Safety_Index'] = (
#         (df['AI_Score'] * 0.50) + 
#         (df['Stability_Score'] * 0.30) + 
#         (df['Sentiment_Rescaled'] * 0.20)
#     )
    
#     def get_signal(score):
#         if score >= 80: return "STRONG BUY 🟢"
#         elif score >= 60: return "BUY 🟢"
#         elif score >= 40: return "HOLD 🟡"
#         else: return "SELL 🔴"
        
#     df['Recommendation'] = df['Safety_Index'].apply(get_signal)
    
#     df.to_csv(f"data/processed/{ticker}_SAFETY_INDEX.csv", index=False)
#     print(f"   📊 Final Advice: {df['Recommendation'].iloc[-1]}")
def calculate_indicators(df):
    # RSI (14 days)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 🚨 THE ILLIQUIDITY FIX 🚨
    # If a stock doesn't move for 14 days, gain=0 and loss=0 (0/0 = NaN).
    # A perfectly flat stock is perfectly neutral, so we force the RSI to 50.
    df.loc[(gain == 0) & (loss == 0), 'RSI'] = 50
    df['RSI'] = df['RSI'].fillna(50)

    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_12_26_9'] = ema_12 - ema_26
    df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean() 
    df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
    
    df['BBM_20_2.0_2.0'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['BBU_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] + (std * 2)
    df['BBL_20_2.0_2.0'] = df['BBM_20_2.0_2.0'] - (std * 2)
    df['BBB_20_2.0_2.0'] = (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0']) / df['BBM_20_2.0_2.0'] * 100
    df['BBP_20_2.0_2.0'] = (df['close'] - df['BBL_20_2.0_2.0']) / (df['BBU_20_2.0_2.0'] - df['BBL_20_2.0_2.0'])

    return df

def generate_safety_index(ticker, df):
    model = joblib.load("models/best_stock_model_optimized.pkl")
    
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    for col in df.columns:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    X = df[feature_cols]
    
    # Base Component Scores
    df['AI_Score'] = model.predict_proba(X)[:, 1] * 100 
    df['Stability_Score'] = 100 - (abs(df['RSI'] - 50) * 2)
    df['Stability_Score'] = df['Stability_Score'].clip(lower=0)
    df['Sentiment_Rescaled'] = (df['avg_sentiment'] + 1) * 50
    
    # 1. The Raw Formula
    df['Safety_Index'] = (
        (df['AI_Score'] * 0.50) + 
        (df['Stability_Score'] * 0.30) + 
        (df['Sentiment_Rescaled'] * 0.20)
    )
    
    # 🚨 2. NEW: FINANCIAL GUARDRAILS (Overrides the AI if technicals look bad) 🚨
    
    # RSI Guardrails
    # If RSI > 70 (Overbought - people are buying too much, a crash is likely), penalize the score by 15 points
    df.loc[df['RSI'] > 70, 'Safety_Index'] -= 15
    # If RSI < 30 (Oversold - people panicked, it's cheap), boost the score by 10 points
    df.loc[df['RSI'] < 30, 'Safety_Index'] += 10
    
    # Moving Average Guardrails (Golden Cross vs Death Cross)
    # If 50-day is below 200-day (Bearish/Death Cross territory), penalize by 10 points
    df.loc[df['EMA_50'] < df['EMA_200'], 'Safety_Index'] -= 10
    # If 50-day is above 200-day (Bullish/Golden Cross territory), boost by 5 points
    df.loc[df['EMA_50'] > df['EMA_200'], 'Safety_Index'] += 5
    
    # Force the final score to stay neatly between 0 and 100
    df['Safety_Index'] = df['Safety_Index'].clip(0, 100)
    
    # 3. Stricter Thresholds for the UI (Makes "Buys" harder to get)
    def get_signal(score):
        if score >= 80: return "STRONG BUY 🟢"
        elif score >= 65: return "BUY 🟢"    # Raised boundary from 60 to 65
        elif score >= 45: return "HOLD 🟡"   # Raised boundary from 40 to 45
        else: return "SELL 🔴"
        
    df['Recommendation'] = df['Safety_Index'].apply(get_signal)
    
    df.to_csv(f"data/processed/{ticker}_SAFETY_INDEX.csv", index=False)
    
    # Updated print statement to show you exactly what score it landed on
    print(f"   📊 Final Advice: {df['Recommendation'].iloc[-1]} (Score: {df['Safety_Index'].iloc[-1]:.1f})")
    
# def fetch_live_data():
#     print("🔄 Starting Full Multi-Modal Pipeline (Prices + AI + NLP)...")
#     os.makedirs("data/live", exist_ok=True)
#     os.makedirs("data/processed", exist_ok=True)
    
#     for ticker in NGX_STOCKS:
#         print(f"\n📥 Processing {ticker}...")
#         try:
#             time.sleep(5) # Prevent TradingView block
            
#             df = tv.get_hist(symbol=ticker, exchange='NSENG', interval=Interval.in_daily, n_bars=250)
            
#             if df is None or df.empty:
#                 print(f"   ⚠️ No data found. Skipping.")
#                 continue
                
#             df = df.reset_index().rename(columns={"datetime": "date"})
#             df = calculate_indicators(df).dropna().copy()
            
#             # THE REAL NLP PIPELINE FIRES HERE
#             today_sentiment = get_todays_sentiment(ticker)
#             df['avg_sentiment'] = today_sentiment 
#             print(f"   🐦 Live NLP Sentiment: {today_sentiment}")
            
#             df.to_csv(f"data/live/{ticker}_LIVE.csv", index=False)
#             generate_safety_index(ticker, df)
            
#         except Exception as e:
#             print(f"   ❌ Error processing {ticker}: {e}")
            
#     print("\n✅ End-to-End Pipeline Complete! System is fully synced.")
def fetch_live_data():
    print("🔄 Starting Full Multi-Modal Pipeline (Prices + AI + NLP)...")
    os.makedirs("data/live", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    for ticker in NGX_STOCKS:
        print(f"\n📥 Processing {ticker}...")
        
        # --- THE NEW RETRY LOGIC ---
        max_retries = 3
        df = None
        
        for attempt in range(max_retries):
            try:
                # Wait longer on each retry to let TradingView's server cool down
                sleep_time = 5 + (attempt * 3) 
                time.sleep(sleep_time) 
                
                df = tv.get_hist(symbol=ticker, exchange='NSENG', interval=Interval.in_daily, n_bars=250)
                
                # If we got data, break out of the retry loop!
                if df is not None and not df.empty:
                    break 
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Network hiccup. Retrying {ticker} (Attempt {attempt+2}/{max_retries})...")
                else:
                    print(f"   ❌ Failed after 3 attempts: {e}")
        # ---------------------------

        if df is None or df.empty:
            print(f"   ⏭️ Skipping {ticker} - Could not establish connection.")
            continue
            
        try:
            # Data Formatting
            df = df.reset_index().rename(columns={"datetime": "date"})
            df = calculate_indicators(df).dropna().copy()
            
            # THE REAL NLP PIPELINE FIRES HERE
            today_sentiment = get_todays_sentiment(ticker)
            df['avg_sentiment'] = today_sentiment 
            print(f"   🐦 Live NLP Sentiment: {today_sentiment}")
            
            # Save and Score
            df.to_csv(f"data/live/{ticker}_LIVE.csv", index=False)
            generate_safety_index(ticker, df)
            
        except Exception as e:
            print(f"   ❌ Error processing {ticker} data: {e}")
            
    print("\n✅ End-to-End Pipeline Complete! System is fully synced.")
if __name__ == "__main__":
    fetch_live_data()
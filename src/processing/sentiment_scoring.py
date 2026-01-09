import pandas as pd
from transformers import pipeline
from tqdm import tqdm 
import torch

def score_sentiment():
    print("🧠 Loading FinBERT model...")
    # Smart device detection for Mac (MPS) vs Windows/Linux (CUDA) vs CPU
    if torch.backends.mps.is_available():
        device = "mps"
        print("   - Using Mac GPU (Metal Performance Shaders) 🚀")
    elif torch.cuda.is_available():
        device = 0
        print("   - Using NVIDIA GPU 🚀")
    else:
        device = -1
        print("   - Using CPU (Slower but reliable)")
    
    finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert", device=device)
    
    input_path = "data/processed/sentiment_master_clean.csv"
    output_path = "data/processed/sentiment_daily_scored.csv"
    
    print(f"📖 Reading {input_path}...")
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print("❌ Error: Run src/preprocessing.py first!")
        return

    # 1. Run FinBERT on every row
    print("Calculating sentiment scores (this might take a moment)...")
    results = []
    
    for text in tqdm(df['clean_text']):
        try:
            # FinBERT returns [{'label': 'positive', 'score': 0.95}]
            # Truncate to 512 characters to prevent errors with long text
            res = finbert(str(text)[:512])[0] 
            
            score = res['score']
            if res['label'] == 'negative':
                score = -score # Make negative sentiment a negative number
            elif res['label'] == 'neutral':
                score = 0 # Neutral is zero
            
            results.append(score)
        except Exception as e:
            # If text is empty or errors out, assume Neutral
            results.append(0)

    df['sentiment_score'] = results

    # 2. Fix Dates (THE FIX)
    print("📅 Standardizing dates...")
    
    # Use 'mixed' format to handle Reddit (ISO) vs Twitter (Standard)
    # Use 'coerce' to turn text like "Today" into NaT (Not a Time) instead of crashing
    df['date'] = pd.to_datetime(df['date'], format='mixed', utc=True, errors='coerce')
    
    # Fill any failed dates (like "Today" from Nairaland) with the current date
    df['date'] = df['date'].fillna(pd.Timestamp.now(tz='UTC'))
    
    # Convert to standard Date only (YYYY-MM-DD), removing Timezone info
    df['date'] = df['date'].dt.tz_convert(None).dt.date
    
    # 3. Aggregate by Day
    # If we have 50 tweets in one day, we take the AVERAGE score
    daily_sentiment = df.groupby('date')['sentiment_score'].mean().reset_index()
    daily_sentiment.columns = ['date', 'avg_sentiment']
    
    # Save
    daily_sentiment.to_csv(output_path, index=False)
    print(f"✅ Success! Daily scores saved to {output_path}")
    print(daily_sentiment.head())

if __name__ == "__main__":
    score_sentiment()
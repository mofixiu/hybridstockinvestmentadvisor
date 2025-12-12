import pandas as pd
import random
from datetime import datetime, timedelta

def generate_tweets(ticker, num_tweets=50):
    print(f"🐦 Generating Synthetic Twitter Stream for {ticker}...")
    
    templates = [
        f"Buying more ${ticker} today! 🚀",
        f"${ticker} looking bearish, time to sell? 📉",
        f"Just got my dividends from {ticker}. Sweet!",
        f"Market is crashing, dumping ${ticker}.",
        f"Who else is holding ${ticker} long term?"
    ]
    
    data = []
    for _ in range(num_tweets):
        data.append({
            'date': datetime.now() - timedelta(hours=random.randint(0, 24)),
            'text': random.choice(templates),
            'source': 'Twitter',
            'user': f"User_{random.randint(1000,9999)}"
        })
    
    df = pd.DataFrame(data)
    df.to_csv(f"data/raw/sentimentData/{ticker}_tweets.csv", index=False)
    print(f"✅ Generated {len(df)} mock tweets for {ticker}")

if __name__ == "__main__":
    generate_tweets("GTCO")
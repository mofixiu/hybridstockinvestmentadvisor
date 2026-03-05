# import pandas as pd
# import random
# from datetime import datetime, timedelta

# def generate_tweets(ticker, num_tweets=50):
#     print(f"🐦 Generating Synthetic Twitter Stream for {ticker}...")
    
#     templates = [
#         f"Buying more ${ticker} today! 🚀",
#         f"${ticker} looking bearish, time to sell? 📉",
#         f"Just got my dividends from {ticker}. Sweet!",
#         f"Market is crashing, dumping ${ticker}.",
#         f"Who else is holding ${ticker} long term?"
#     ]
    
#     data = []
#     for _ in range(num_tweets):
#         data.append({
#             'date': datetime.now() - timedelta(hours=random.randint(0, 24)),
#             'text': random.choice(templates),
#             'source': 'Twitter',
#             'user': f"User_{random.randint(1000,9999)}"
#         })
    
#     df = pd.DataFrame(data)
#     df.to_csv(f"data/raw/sentimentData/{ticker}_tweets.csv", index=False)
#     print(f"✅ Generated {len(df)} mock tweets for {ticker}")

# if __name__ == "__main__":
#     generate_tweets("GTCO")
import random

def scrape_twitter_mock(query):
    print(f"   🐦 Simulating X (Twitter) feed for: {query}...")
    
    # Simulating Nigerian retail investor slang
    positive = [
        f"{query} is mooning today! 🚀🚀", 
        f"Clear road! The earnings report for {query} is massive.",
        f"Buying more units of {query}, the dividends are mad."
    ]
    negative = [
        f"Omo, {query} has cast. My portfolio is bleeding.", 
        f"Whales are dumping {query}, run for your life!",
        f"Sapa everywhere, no movement on {query}."
    ]
    neutral = [
        f"Zenith and {query} are just consolidating, nothing much.", 
        f"Just watching the market for now, {query} has no clear signal.",
        f"Hold your shares, {query} will soon bounce back."
    ]
    
    # Randomly select a narrative for the day
    narrative = random.choice([positive, negative, neutral])
    
    # Return 2 random tweets from the chosen narrative
    return random.sample(narrative, 2)
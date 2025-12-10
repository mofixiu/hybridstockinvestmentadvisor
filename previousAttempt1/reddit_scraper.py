import praw
import pandas as pd
from datetime import datetime

# REPLACE WITH YOUR REDDIT KEYS
reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="StockSentimentApp/1.0"
)

def get_reddit_posts(query, limit=100):
    print(f"Scraping Reddit for: {query}...")
    subreddit = reddit.subreddit("all")
    
    posts = []
    # Search for the stock ticker or company name
    for post in subreddit.search(query, sort='new', limit=limit):
        posts.append({
            'date': datetime.fromtimestamp(post.created_utc),
            'title': post.title,
            'body': post.selftext[:500],  # First 500 chars
            'score': post.score,
            'source': 'Reddit'
        })
    
    df = pd.DataFrame(posts)
    df.to_csv(f"{query}_reddit_data.csv", index=False)
    print(f"Saved {len(df)} Reddit posts!")
    return df

# Test for a Nigerian context
get_reddit_posts("Guaranty Trust Bank")
get_reddit_posts("Dangote Cement")
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

def scrape_reddit_rss(query):
    print(f"🤖 Scraping Reddit (RSS) for: {query}...")
    
    # Reddit Search RSS URL (No API Key needed)
    # We search globally for the ticker
    url = f"https://www.reddit.com/search.rss?q={query}&sort=new"
    
    # CRITICAL: Reddit blocks default python requests. We must pretend to be a browser.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error: Reddit returned status code {response.status_code}")
            return None
            
        # Parse XML
        soup = BeautifulSoup(response.content, features="xml")
        entries = soup.find_all('entry')
        
        posts = []
        if len(entries) == 0:
            print(f"⚠️ No recent posts found for {query}.")
        
        for entry in entries:
            posts.append({
                'date': entry.updated.text if entry.updated else str(datetime.now()),
                'title': entry.title.text,
                'link': entry.link['href'],
                'source': 'Reddit'
            })
            # Print preview
            print(f"- {entry.title.text[:50]}...")
            
        # Save
        if posts:
            df = pd.DataFrame(posts)
            filename = f"data/raw/sentimentData/{query}_reddit.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Success! Saved {len(df)} posts to {filename}")
            return df
            
    except Exception as e:
        print(f"❌ Scraping Error: {e}")
        return None

if __name__ == "__main__":
    # Test with generic terms first to prove it works
    scrape_reddit_rss("Nigeria Economy") 
    scrape_reddit_rss("GTCO")
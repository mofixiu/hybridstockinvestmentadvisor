from ntscraper import Nitter
import pandas as pd
import time
import random

def get_tweets(query, limit=100):
    print(f"Scraping Twitter for: {query}...")
    scraper = Nitter()
    
    # List of known Nitter instances to try
    # You can find more at: https://github.com/zedeus/nitter/wiki/Instances
    instances = [
        'https://nitter.poast.org',
        'https://nitter.lucabased.xyz',
        'https://nitter.privacydev.net',
        'https://nitter.net',
        'https://nitter.cz',
        'https://nitter.perennialte.ch',
    ]
    
    tweets_data = []
    success = False
    
    # Try instances one by one until success
    for instance in instances:
        try:
            print(f"Trying instance: {instance}...")
            tweets = scraper.get_tweets(query, mode='term', number=limit, instance=instance)
            
            # Check if we actually got tweets back
            if tweets and 'tweets' in tweets and len(tweets['tweets']) > 0:
                print(f"Success on {instance}! Found {len(tweets['tweets'])} tweets.")
                
                for tweet in tweets['tweets']:
                    tweets_data.append({
                        'date': tweet['date'],
                        'text': tweet['text'],
                        'user': tweet['user']['username'],
                        'likes': tweet['stats']['likes'],
                        'source': 'Twitter'
                    })
                success = True
                break # Stop trying other instances if this one worked
            else:
                print(f"Instance {instance} returned no tweets. Trying next...")
                
        except Exception as e:
            print(f"Error on {instance}: {e}")
            continue # Try next instance
            
    if not success:
        print("Failed to scrape tweets from all instances. Twitter/Nitter might be blocking requests.")
        return None

    # Save Data
    df = pd.DataFrame(tweets_data)
    filename = f"{query}_tweets.csv"
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} Tweets to {filename}!")
    return df

# Test with a popular ticker first
if __name__ == "__main__":
    get_tweets("AAPL")
import requests
from bs4 import BeautifulSoup

def get_live_news(query):
    print(f"Scraping news for: {query}...")
    
    # We use Google News RSS feed (Easiest way to scrape without getting blocked)
    url = f"https://news.google.com/rss/search?q={query}+stock+nigeria+when:7d"
    
    try:
        response = requests.get(url)
        # Use 'xml' parser because RSS is XML format
        soup = BeautifulSoup(response.content, features="xml")
        
        items = soup.findAll('item')
        headlines = []
        
        print(f"Found {len(items)} articles.")
        
        for item in items:
            # Clean the headline (remove the source name at the end)
            title = item.title.text
            date = item.pubDate.text
            headlines.append({'date': date, 'headline': title})
            
            # Print preview
            print(f"- {title}")
            
        return headlines

    except Exception as e:
        print(f"Error scraping news: {e}")
        return []

# Test it for AAPL
news = get_live_news("AAPL")
# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# import time
# import random

# def scrape_nairaland(query):
#     print(f"🇳🇬 Scraping Nairaland for: {query}...")
    
#     # We use Google to search Nairaland because Nairaland's internal search is tricky to scrape
#     # "site:nairaland.com {query}"
#     search_url = f"https://www.google.com/search?q=site:nairaland.com+{query}&tbm=nws" # tbm=nws looks at news/recent
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#     }
    
#     try:
#         response = requests.get(search_url, headers=headers)
#         soup = BeautifulSoup(response.content, 'html.parser')
        
#         # Google stores results in different tags depending on the page structure
#         # Often div class="BNeawe vvjwJb AP7Wnd" contains the title in simple HTML mode
#         # or simple <h3> tags
        
#         results = []
#         # Look for headlines
#         links = soup.find_all('div', role='heading') 
        
#         if not links:
#             # Fallback for different google page structure
#             links = soup.find_all('h3')

#         for link in links:
#             title = link.text
#             if title:
#                 results.append({
#                     'date': 'Recent', # Google doesn't always give easy date in html
#                     'text': title,
#                     'source': 'Nairaland'
#                 })
#                 print(f"- {title[:50]}...")

#         if results:
#             df = pd.DataFrame(results)
#             filename = f"data/raw/sentimentData/{query}_nairaland.csv"
#             df.to_csv(filename, index=False)
#             print(f"✅ Success! Saved {len(df)} Nairaland discussions.")
#         else:
#             print("⚠️ No results found via Google-Nairaland search.")

#     except Exception as e:
#         print(f"❌ Error: {e}")

# if __name__ == "__main__":
#     scrape_nairaland("GTCO")
#     scrape_nairaland("Zenith Bank")
import requests
from bs4 import BeautifulSoup

def scrape_nairaland(query):
    print(f"   🇳🇬 Scraping Nairaland for: {query}...")
    # Standard search is less likely to be blocked than News search
    search_url = f"https://www.google.com/search?q=site:nairaland.com+{query}" 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Google uses h3 for search result titles
        links = soup.find_all('h3')
        
        texts = [link.text for link in links if link.text]
        return texts
    except Exception as e:
        return []
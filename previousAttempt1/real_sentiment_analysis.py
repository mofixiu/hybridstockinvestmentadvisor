from transformers import pipeline
from news_scraper import get_live_news # Import the tool you just built

# 1. Load FinBERT
print("Loading FinBERT...")
finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")

# 2. Get Real News
stock_name = "AAPL"
articles = get_live_news(stock_name)

if len(articles) > 0:
    # 3. Analyze Sentiment for each headline
    print(f"\nAnalyzing Sentiment for {stock_name}...")
    
    total_score = 0
    count = 0
    
    for article in articles:
        text = article['headline']
        # FinBERT prediction
        result = finbert(text)[0]
        label = result['label']
        score = result['score']
        
        # Convert label to a number for averaging
        # Positive = 1, Neutral = 0, Negative = -1
        numeric_val = 0
        if label == 'positive': numeric_val = 1
        elif label == 'negative': numeric_val = -1
        
        total_score += numeric_val
        print(f"Headline: {text[:50]}... -> {label} ({numeric_val})")
        count += 1
        
    # 4. Calculate Final "Market Sentiment" Score
    final_sentiment = total_score / count
    print(f"\n--- FINAL REPORT ---")
    print(f"Average Sentiment Score: {final_sentiment:.2f}")
    
    if final_sentiment > 0.2:
        print("Recommendation: BULLISH (Positive News)")
    elif final_sentiment < -0.2:
        print("Recommendation: BEARISH (Negative News)")
    else:
        print("Recommendation: NEUTRAL (Mixed News)")

else:
    print("No news found to analyze.")
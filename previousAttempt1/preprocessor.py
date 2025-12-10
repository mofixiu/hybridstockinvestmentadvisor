import pandas as pd
import re

def clean_text(text):
    # 1. Lowercase
    text = str(text).lower()
    # 2. Remove URLs (http...)
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    # 3. Remove User @ references and '#' from hashtags
    text = re.sub(r'\@\w+|\#', '', text)
    # 4. Remove extra spaces
    text = text.strip()
    return text

def preprocess_files(file_list):
    all_data = []
    for file in file_list:
        try:
            df = pd.read_csv(file)
            # Standardize column names (News has 'headline', Reddit 'title', Twitter 'text')
            if 'headline' in df.columns: df.rename(columns={'headline': 'text'}, inplace=True)
            if 'title' in df.columns: df.rename(columns={'title': 'text'}, inplace=True)
            
            # Apply cleaning
            df['clean_text'] = df['text'].apply(clean_text)
            all_data.append(df)
        except Exception as e:
            print(f"Skipping {file}: {e}")
            
    if not all_data: return None
    
    # Combine everything
    master_df = pd.concat(all_data, ignore_index=True)
    master_df.to_csv("CLEANED_SENTIMENT_DATA.csv", index=False)
    print("Preprocessing Complete! Saved 'CLEANED_SENTIMENT_DATA.csv'")
    return master_df

# Example usage
# preprocess_files(['AAPL_reddit_data.csv', 'AAPL_tweets.csv'])``
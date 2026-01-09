import pandas as pd
import numpy as np
import joblib
import os

def calculate_safety_score(ticker="GTCO"):
    print(f"🛡️ Calculating Investment Safety Index for {ticker}...")
    
    # 1. Load Data & Model
    data_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    model_path = "models/best_stock_model_optimized.pkl"
    
    if not os.path.exists(data_path) or not os.path.exists(model_path):
        print("❌ Missing files. Please check data and models folders.")
        return

    df = pd.read_csv(data_path)
    model = joblib.load(model_path)
    
    # 2. Prepare Features for the Model
    # We need to make sure we use the EXACT same columns the model was trained on
    # (Checking the model's feature names if possible, otherwise using our standard list)
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    # Add dynamic columns
    for col in df.columns:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    X = df[feature_cols]
    
    # 3. COMPONENT A: AI Confidence (50% Weight)
    # model.predict_proba gives [[prob_sell, prob_buy]]
    # We take the second value (Index 1) which is "Probability of Buy"
    ai_probs = model.predict_proba(X)[:, 1] 
    df['AI_Score'] = ai_probs * 100 # Convert 0.75 -> 75.0
    
    # 4. COMPONENT B: Market Stability (30% Weight)
    # Logic: RSI 50 is perfect stability. RSI 0 or 100 is extreme risk.
    # Formula: 100 - Distance from 50.
    # If RSI is 50, score is 100. If RSI is 90, distance is 40, score is 100 - (40*2) = 20.
    df['Stability_Score'] = 100 - (abs(df['RSI'] - 50) * 2)
    # Clip it so it doesn't go below 0
    df['Stability_Score'] = df['Stability_Score'].clip(lower=0)
    
    # 5. COMPONENT C: Sentiment Score (20% Weight)
    # Sentiment is usually -1 to 1. We map it to 0 to 100.
    # -1 (Bad) -> 0
    # 0 (Neutral) -> 50
    # +1 (Good) -> 100
    df['Sentiment_Rescaled'] = (df['avg_sentiment'] + 1) * 50
    
    # 6. THE FINAL FORMULA
    df['Safety_Index'] = (
        (df['AI_Score'] * 0.50) + 
        (df['Stability_Score'] * 0.30) + 
        (df['Sentiment_Rescaled'] * 0.20)
    )
    
    # 7. Generate Action Signal
    def get_signal(score):
        if score >= 80: return "STRONG BUY 🟢"
        elif score >= 60: return "BUY 🟢"
        elif score >= 40: return "HOLD 🟡"
        else: return "SELL 🔴"
        
    df['Recommendation'] = df['Safety_Index'].apply(get_signal)
    
    # 8. Save and Show
    output_path = f"data/processed/{ticker}_SAFETY_INDEX.csv"
    df.to_csv(output_path, index=False)
    
    print(f"✅ Success! Safety Index generated in {output_path}")
    
    # Show the most recent days
    print("\n📅 LATEST 5 DAYS FORECAST:")
    print(df[['date', 'close', 'AI_Score', 'Safety_Index', 'Recommendation']].tail())

if __name__ == "__main__":
    calculate_safety_score("GTCO")
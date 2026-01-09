import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib # To save the model
import os

def train_models(ticker="GTCO"):
    print(f"🧠 Training Baseline Models for {ticker}...")
    
    # 1. Load Data
    input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    if not os.path.exists(input_path):
        print("❌ Data not found. Finish Week 5 first.")
        return

    df = pd.read_csv(input_path)
    
    # 2. Prepare X (Features) and y (Target)
    # We drop columns that are not features (like Date, Close price, Target itself)
    # The AI only sees: RSI, EMA, MACD, Sentiment
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment'] 
    # Note: You can add MACD columns if they exist in your CSV, check column names!
    # Let's inspect columns first to be safe
    available_cols = df.columns.tolist()
    final_features = [c for c in feature_cols if c in available_cols]
    
    # Add MACD/Bollinger columns dynamically if they exist
    for col in available_cols:
        if "MACD" in col or "BBL" in col or "BBM" in col or "BBU" in col:
            final_features.append(col)
            
    print(f"   - Training on features: {final_features}")
    
    X = df[final_features]
    y = df['Target']
    
    # 3. Split Data (Time-Based Split)
    # shuffle=False is CRITICAL for financial data. 
    # We train on the first 80% of history, test on the recent 20%.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    print(f"   - Training Set: {len(X_train)} rows")
    print(f"   - Testing Set: {len(X_test)} rows")
    
    # --- MODEL 1: Logistic Regression (The Baseline) ---
    print("\n🔹 Training Logistic Regression...")
    lr_model = LogisticRegression()
    lr_model.fit(X_train, y_train)
    lr_preds = lr_model.predict(X_test)
    
    print("   - Logistic Regression Accuracy:", accuracy_score(y_test, lr_preds))
    print(classification_report(y_test, lr_preds))
    
    # --- MODEL 2: Random Forest (The Real Deal) ---
    print("\n🌲 Training Random Forest...")
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    
    rf_acc = accuracy_score(y_test, rf_preds)
    print(f"   - Random Forest Accuracy: {rf_acc:.4f}")
    print(classification_report(y_test, rf_preds))
    
    # 4. Save the Best Model
    # We save the Random Forest as our "v1" model
    os.makedirs("models", exist_ok=True)
    joblib.dump(rf_model, f"models/{ticker}_random_forest.pkl")
    print(f"\n✅ Model saved to models/{ticker}_random_forest.pkl")

if __name__ == "__main__":
    train_models("GTCO")
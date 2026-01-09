import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import joblib
import os

def train_advanced_models(ticker="GTCO"):
    print(f"🚀 Training Advanced Models for {ticker}...")
    
    # 1. Load Data
    input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    if not os.path.exists(input_path):
        print("❌ Data not found. Run Week 5 script first.")
        return

    df = pd.read_csv(input_path)
    
    # 2. Setup Features
    # We dynamically select all the good columns we built
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    all_cols = df.columns.tolist()
    # Add MACD and Bollinger Bands if they exist
    for col in all_cols:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    print(f"   - Features Used: {feature_cols}")
    
    X = df[feature_cols]
    y = df['Target']
    
    # 3. Time-Series Split (Train on Past, Test on Future)
    # We use the last 20% for testing
    split_point = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
    y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]
    
    print(f"   - Train Size: {len(X_train)} | Test Size: {len(X_test)}")
    
    # --- CRITICAL: CALCULATE CLASS WEIGHT ---
    # Because 'Buy' signals are rare, we calculate how much to boost them.
    # ratio = Number of Negatives / Number of Positives
    ratio = float(np.sum(y_train == 0)) / np.sum(y_train == 1)
    print(f"   - Class Imbalance Ratio: {ratio:.2f} (We will boost 'Buy' signals by this amount)")

    # 4. Define Models
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=200, 
            max_depth=10, 
            class_weight="balanced", # Fixes the lazy buy
            random_state=42
        ),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=200, 
            learning_rate=0.05, 
            max_depth=5, 
            scale_pos_weight=ratio, # Fixes the lazy buy
            eval_metric='logloss',
            random_state=42
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=200, 
            learning_rate=0.05, 
            num_leaves=31, 
            scale_pos_weight=ratio, # Fixes the lazy buy
            verbosity=-1,
            random_state=42
        )
    }
    
    # 5. Train & Compare
    results = []
    best_f1 = 0
    best_model_name = ""
    best_model_obj = None
    
    print("\n📊 COMPARATIVE RESULTS:")
    print(f"{'Model':<15} | {'Accuracy':<10} | {'Precision':<10} | {'Recall (Buy)':<12} | {'F1-Score':<10}")
    print("-" * 70)
    
    for name, model in models.items():
        # Train
        model.fit(X_train, y_train)
        
        # Predict
        preds = model.predict(X_test)
        
        # Metrics
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds)
        rec = recall_score(y_test, preds)
        f1 = f1_score(y_test, preds)
        
        print(f"{name:<15} | {acc:.4f}     | {prec:.4f}     | {rec:.4f}       | {f1:.4f}")
        
        results.append({'Model': name, 'F1': f1})
        
        # Save Champion
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            best_model_obj = model

    # 6. Save the Champion
    print("-" * 70)
    print(f"🏆 CHAMPION MODEL: {best_model_name} (F1: {best_f1:.4f})")
    
    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model_obj, "models/best_stock_model.pkl")
    print(f"✅ Saved champion to models/best_stock_model.pkl")

if __name__ == "__main__":
    train_advanced_models("GTCO")
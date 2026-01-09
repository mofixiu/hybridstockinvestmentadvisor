import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import classification_report, f1_score
import joblib
import os

def tune_lightgbm(ticker="GTCO"):
    print(f"🔧 Starting Hyperparameter Tuning for {ticker} (LightGBM)...")
    
    # 1. Load Data
    input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    if not os.path.exists(input_path):
        print("❌ Data not found.")
        return

    df = pd.read_csv(input_path)
    
    # 2. Setup Features (Same as before)
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    for col in df.columns:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    X = df[feature_cols]
    y = df['Target']
    
    # 3. Time-Series Split
    # We use the first 80% for "Train + Validation" and keep last 20% for "Final Test"
    split_point = int(len(df) * 0.8)
    X_train_full, X_test = X.iloc[:split_point], X.iloc[split_point:]
    y_train_full, y_test = y.iloc[:split_point], y.iloc[split_point:]
    
    # Calculate Class Weight
    ratio = float(np.sum(y_train_full == 0)) / np.sum(y_train_full == 1)
    print(f"   - Class Imbalance Ratio: {ratio:.2f}")

    # 4. Define the Parameter Grid
    # These are the "Knobs" we will turn. 
    # The grid will try every combination (3 x 3 x 2 x 2 = 36 combinations)
    param_grid = {
        'learning_rate': [0.01, 0.05, 0.1],      # How fast it learns
        'n_estimators': [100, 200, 300],         # Number of trees
        'num_leaves': [20, 31, 50],              # Complexity of trees
        'max_depth': [-1, 10],                   # Limit depth to prevent overfitting
        'scale_pos_weight': [ratio, ratio * 1.2] # Try standard ratio and boosted ratio
    }
    
    # 5. Setup Grid Search with Time-Series Cross Validation
    # cv=3 means it will test each combo on 3 different time periods in the past
    tscv = TimeSeriesSplit(n_splits=3)
    
    lgbm = lgb.LGBMClassifier(random_state=42, verbose=-1)
    
    print("\n⏳ Running Grid Search (This may take a minute)...")
    grid_search = GridSearchCV(
        estimator=lgbm,
        param_grid=param_grid,
        scoring='f1', # We want to maximize F1 Score (Finding Buys accurately)
        cv=tscv,
        n_jobs=-1,    # Use all CPU cores
        verbose=1
    )
    
    grid_search.fit(X_train_full, y_train_full)
    
    # 6. Evaluate the Best Model
    best_model = grid_search.best_estimator_
    print(f"\n🏆 BEST PARAMS: {grid_search.best_params_}")
    
    print("\n🧪 Testing Best Model on Unseen Future Data:")
    preds = best_model.predict(X_test)
    
    print(classification_report(y_test, preds))
    print(f"Final F1 Score: {f1_score(y_test, preds):.4f}")
    
    # 7. Save the Optimized Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/best_stock_model_optimized.pkl")
    print("✅ Optimized model saved to models/best_stock_model_optimized.pkl")

if __name__ == "__main__":
    tune_lightgbm("GTCO")
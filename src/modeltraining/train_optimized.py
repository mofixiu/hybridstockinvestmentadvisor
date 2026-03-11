# import pandas as pd
# import numpy as np
# import lightgbm as lgb
# from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
# from sklearn.metrics import classification_report, f1_score
# import joblib
# import os

# def tune_lightgbm(ticker="GTCO"):
#     print(f"🔧 Starting Hyperparameter Tuning for {ticker} (LightGBM)...")
    
#     # 1. Load Data
#     input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
#     if not os.path.exists(input_path):
#         print("❌ Data not found.")
#         return

#     df = pd.read_csv(input_path)
    
#     # 2. Setup Features (Same as before)
#     feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
#     for col in df.columns:
#         if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
#             feature_cols.append(col)
            
#     X = df[feature_cols]
#     y = df['Target']
    
#     # 3. Time-Series Split
#     # We use the first 80% for "Train + Validation" and keep last 20% for "Final Test"
#     split_point = int(len(df) * 0.8)
#     X_train_full, X_test = X.iloc[:split_point], X.iloc[split_point:]
#     y_train_full, y_test = y.iloc[:split_point], y.iloc[split_point:]
    
#     # Calculate Class Weight
#     ratio = float(np.sum(y_train_full == 0)) / np.sum(y_train_full == 1)
#     print(f"   - Class Imbalance Ratio: {ratio:.2f}")

#     # 4. Define the Parameter Grid
#     # These are the "Knobs" we will turn. 
#     # The grid will try every combination (3 x 3 x 2 x 2 = 36 combinations)
#     param_grid = {
#         'learning_rate': [0.01, 0.05, 0.1],      # How fast it learns
#         'n_estimators': [100, 200, 300],         # Number of trees
#         'num_leaves': [20, 31, 50],              # Complexity of trees
#         'max_depth': [-1, 10],                   # Limit depth to prevent overfitting
#         'scale_pos_weight': [ratio, ratio * 1.2] # Try standard ratio and boosted ratio
#     }
    
#     # 5. Setup Grid Search with Time-Series Cross Validation
#     # cv=3 means it will test each combo on 3 different time periods in the past
#     tscv = TimeSeriesSplit(n_splits=3)
    
#     lgbm = lgb.LGBMClassifier(random_state=42, verbose=-1)
    
#     print("\n⏳ Running Grid Search (This may take a minute)...")
#     grid_search = GridSearchCV(
#         estimator=lgbm,
#         param_grid=param_grid,
#         scoring='f1', # We want to maximize F1 Score (Finding Buys accurately)
#         cv=tscv,
#         n_jobs=-1,    # Use all CPU cores
#         verbose=1
#     )
    
#     grid_search.fit(X_train_full, y_train_full)
    
#     # 6. Evaluate the Best Model
#     best_model = grid_search.best_estimator_
#     print(f"\n🏆 BEST PARAMS: {grid_search.best_params_}")
    
#     print("\n🧪 Testing Best Model on Unseen Future Data:")
#     preds = best_model.predict(X_test)
    
#     print(classification_report(y_test, preds))
#     print(f"Final F1 Score: {f1_score(y_test, preds):.4f}")
    
#     # 7. Save the Optimized Model
#     os.makedirs("models", exist_ok=True)
#     joblib.dump(best_model, "models/best_stock_model_optimized.pkl")
#     print("✅ Optimized model saved to models/best_stock_model_optimized.pkl")

# if __name__ == "__main__":
#     tune_lightgbm("GTCO")
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.metrics import classification_report, f1_score
import joblib
import os

def tune_lightgbm(ticker="GTCO"):
    print(f"🚀 Starting DEEP Hyperparameter Tuning for {ticker} (LightGBM)...")
    
    # 1. Load Data
    input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    if not os.path.exists(input_path):
        print("❌ Data not found.")
        return

    df = pd.read_csv(input_path)
    
    # 2. Setup Features
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    for col in df.columns:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    X = df[feature_cols]
    y = df['Target']
    
    # 3. Time-Series Split
    split_point = int(len(df) * 0.8)
    X_train_full, X_test = X.iloc[:split_point], X.iloc[split_point:]
    y_train_full, y_test = y.iloc[:split_point], y.iloc[split_point:]
    
    # Calculate Class Weight
    ratio = float(np.sum(y_train_full == 0)) / np.sum(y_train_full == 1)
    print(f"   - Class Imbalance Ratio: {ratio:.2f}")
#if you want a lower f1 score but more conservative buy signals and AI uncomment below
    # # 4. Define the EXPANDED Parameter Universe
    # # We are vastly increasing the complexity and protection against overfitting
    # param_dist = {
    #     'learning_rate': [0.005, 0.01, 0.05, 0.1],     # Added ultra-fine 0.005
    #     'n_estimators': [200, 400, 600, 800],          # Increased "epochs" up to 800
    #     'num_leaves': [20, 31, 50, 70, 100],           # Deeper mathematical trees
    #     'max_depth': [-1, 5, 10, 15],                  # Structural limits
    #     'min_child_samples': [10, 20, 30],             # Overfitting protection
    #     'subsample': [0.7, 0.8, 0.9, 1.0],             # Row bagging (randomly drops data to learn harder)
    #     'colsample_bytree': [0.7, 0.8, 0.9, 1.0],      # Feature bagging (randomly drops indicators)
    #     'scale_pos_weight': [ratio, ratio * 1.2, ratio * 1.5] # Aggressive buy-signal boosting
    # }
    
# 4. Define the AGGRESSIVE Parameter Universe
    # We lowered the strictness and forced higher scale_pos_weight to boost Recall
    param_dist = {
        'learning_rate': [0.05, 0.1, 0.15],            
        'n_estimators': [100, 200, 300, 400],          
        'num_leaves': [31, 50, 70],           
        'max_depth': [5, 10, -1],                  
        'min_child_samples': [5, 10, 15],              # Lowered so it learns smaller patterns
        'subsample': [0.8, 0.9, 1.0],                  
        'colsample_bytree': [0.8, 0.9, 1.0],      
        'scale_pos_weight': [ratio * 1.5, ratio * 2.0, ratio * 2.5] # 🚨 Forces the AI to predict 'Buy' more often
    } 
    # 5. Setup Randomized Search with Time-Series Cross Validation
    tscv = TimeSeriesSplit(n_splits=3)
    
    lgbm = lgb.LGBMClassifier(random_state=42, verbosity=-1)
    
    print("\n⏳ Running Randomized Search (Testing 50 deep variations)...")
    
    # RandomizedSearchCV tests 50 random combinations from the massive grid above
    random_search = RandomizedSearchCV(
        estimator=lgbm,
        param_distributions=param_dist,
        n_iter=50,       # The number of models it will build and test
        scoring='f1',    # Maximize F1 Score
        cv=tscv,
        n_jobs=-1,       # Use all CPU cores on your Mac
        verbose=1,
        random_state=42
    )
    
    random_search.fit(X_train_full, y_train_full)
    
    # 6. Evaluate the Best Model
    best_model = random_search.best_estimator_
    print(f"\n🏆 BEST PARAMS FOUND: {random_search.best_params_}")
    
    print("\n🧪 Testing Best Model on Unseen Future Data:")
    preds = best_model.predict(X_test)
    
    print(classification_report(y_test, preds))
    print(f"Final F1 Score: {f1_score(y_test, preds):.4f}")
    
    # 7. Save the Optimized Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/best_stock_model_optimized.pkl")
    print("\n✅ New Ultra-Optimized model saved to models/best_stock_model_optimized.pkl")

if __name__ == "__main__":
    tune_lightgbm("GTCO")
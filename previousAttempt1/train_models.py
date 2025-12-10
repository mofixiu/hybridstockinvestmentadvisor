# import pandas as pd
# from sklearn.model_selection import train_test_split
# from sklearn.ensemble import RandomForestClassifier
# from xgboost import XGBClassifier
# from lightgbm import LGBMClassifier
# from sklearn.metrics import accuracy_score, f1_score, classification_report
# import joblib  # To save the best model

# # 1. Load Your Fused Data (From the previous "Data Fusion" step)
# # This assumes you have columns: 'RSI', 'EMA', 'Sentiment', 'Target'
# print("Loading Training Data...")
# df = pd.read_csv("FINAL_TRAINING_DATA.csv") 

# features = ['RSI', 'EMA_50', 'MACD_12_26_9', 'sentiment_score']
# X = df[features]
# y = df['target']

# # 2. Split Data (Time-Series Split is better, but simple split for now)
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# # --- MODEL 1: Random Forest ---
# print("\n1. Training Random Forest...")
# rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
# rf.fit(X_train, y_train)
# rf_pred = rf.predict(X_test)
# rf_f1 = f1_score(y_test, rf_pred)
# print(f"Random Forest F1-Score: {rf_f1:.4f}")

# # --- MODEL 2: XGBoost ---
# print("\n2. Training XGBoost...")
# xgb = XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42)
# xgb.fit(X_train, y_train)
# xgb_pred = xgb.predict(X_test)
# xgb_f1 = f1_score(y_test, xgb_pred)
# print(f"XGBoost F1-Score: {xgb_f1:.4f}")

# # --- MODEL 3: LightGBM ---
# print("\n3. Training LightGBM...")
# lgb = LGBMClassifier(n_estimators=100, learning_rate=0.05, random_state=42)
# lgb.fit(X_train, y_train)
# lgb_pred = lgb.predict(X_test)
# lgb_f1 = f1_score(y_test, lgb_pred)
# print(f"LightGBM F1-Score: {lgb_f1:.4f}")

# # --- COMPARE & SAVE ---
# print("\n--- COMPARATIVE RESULTS ---")
# scores = {'RandomForest': rf_f1, 'XGBoost': xgb_f1, 'LightGBM': lgb_f1}
# best_model_name = max(scores, key=scores.get)
# print(f"The Champion Model is: {best_model_name} (F1: {scores[best_model_name]:.4f})")

# # Save the winner to use in your app later
# if best_model_name == 'RandomForest':
#     joblib.dump(rf, 'best_stock_model.pkl')
# elif best_model_name == 'XGBoost':
#     joblib.dump(xgb, 'best_stock_model.pkl')
# else:
#     joblib.dump(lgb, 'best_stock_model.pkl')

# print(f"Saved {best_model_name} to 'best_stock_model.pkl'")
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import f1_score, make_scorer

# 1. Load Data
print("Loading Training Data...")
df = pd.read_csv("FINAL_TRAINING_DATA.csv") 
features = ['RSI', 'EMA_50', 'MACD_12_26_9', 'sentiment_score']
X = df[features]
y = df['target']

# 2. Setup "Time Series" Validation (Standard for Finance)
# We don't shuffle stock data. We train on Jan-Mar to predict April.
tscv = TimeSeriesSplit(n_splits=5)

# 3. Define the "Search Space" (The Hard Work)
# We tell the computer to try ALL these combinations.
rf_params = {
    'n_estimators': [50, 100, 200],
    'max_depth': [None, 10, 20],
    'min_samples_split': [2, 5]
}

xgb_params = {
    'n_estimators': [50, 100, 200],
    'learning_rate': [0.01, 0.1, 0.2],
    'max_depth': [3, 5, 7]
}

lgb_params = {
    'n_estimators': [50, 100, 200],
    'learning_rate': [0.01, 0.1, 0.2],
    'num_leaves': [20, 31, 50]
}

# 4. Run the "Grid Search" (This will take time!)
print("\n--- STARTING HYPERPARAMETER TUNING ---")
print("This simulates training hundreds of models to find the best one...")

# Random Forest Tuning
print("\nTuning Random Forest...")
rf_search = GridSearchCV(RandomForestClassifier(random_state=42), rf_params, cv=tscv, scoring='f1', n_jobs=-1)
rf_search.fit(X, y)
print(f"Best RF Params: {rf_search.best_params_}")
print(f"Best RF F1-Score: {rf_search.best_score_:.4f}")

# XGBoost Tuning
print("\nTuning XGBoost...")
xgb_search = GridSearchCV(XGBClassifier(random_state=42), xgb_params, cv=tscv, scoring='f1', n_jobs=-1)
xgb_search.fit(X, y)
print(f"Best XGB Params: {xgb_search.best_params_}")
print(f"Best XGB F1-Score: {xgb_search.best_score_:.4f}")

# LightGBM Tuning
print("\nTuning LightGBM...")
lgb_search = GridSearchCV(LGBMClassifier(random_state=42, verbose=-1), lgb_params, cv=tscv, scoring='f1', n_jobs=-1)
lgb_search.fit(X, y)
print(f"Best LGB Params: {lgb_search.best_params_}")
print(f"Best LGB F1-Score: {lgb_search.best_score_:.4f}")

# 5. Save the Winner
best_scores = {
    'RandomForest': rf_search.best_score_,
    'XGBoost': xgb_search.best_score_,
    'LightGBM': lgb_search.best_score_
}
winner = max(best_scores, key=best_scores.get)
print(f"\n\n🏆 CHAMPION MODEL: {winner} with F1-Score: {best_scores[winner]:.4f}")

if winner == 'RandomForest': joblib.dump(rf_search.best_estimator_, 'best_stock_model.pkl')
elif winner == 'XGBoost': joblib.dump(xgb_search.best_estimator_, 'best_stock_model.pkl')
else: joblib.dump(lgb_search.best_estimator_, 'best_stock_model.pkl')

print("Saved champion model to 'best_stock_model.pkl'")
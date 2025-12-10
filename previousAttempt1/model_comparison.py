# import numpy as np
# import pandas as pd
# from sklearn.ensemble import RandomForestClassifier
# from xgboost import XGBClassifier
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import accuracy_score

# print("Generating fake stock data for testing...")

# # 1. Create Fake Data (Just to test the models)
# # Imagine: [RSI, Sentiment, EMA]
# X = np.random.rand(1000, 3) 
# # Target: 0 = Sell, 1 = Buy
# y = np.random.randint(0, 2, 1000)

# # 2. Split Data
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# # 3. Train Random Forest
# print("\nTraining Random Forest...")
# rf = RandomForestClassifier()
# rf.fit(X_train, y_train)
# rf_acc = accuracy_score(y_test, rf.predict(X_test))
# print(f"Random Forest Accuracy: {rf_acc:.2f}")

# # 4. Train XGBoost
# print("\nTraining XGBoost...")
# xgb = XGBClassifier()
# xgb.fit(X_train, y_train)
# xgb_acc = accuracy_score(y_test, xgb.predict(X_test))
# print(f"XGBoost Accuracy: {xgb_acc:.2f}")

# # 5. Compare
# if xgb_acc > rf_acc:
#     print("\nWinner: XGBoost is better for this data.")
# else:
#     print("\nWinner: Random Forest is better for this data.")
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 1. Load the REAL Data
df = pd.read_csv("FINAL_TRAINING_DATA.csv")

# 2. Define Features (X) and Target (y)
# We use RSI, EMA, MACD, and Sentiment as inputs
features = ['RSI', 'EMA_50', 'MACD_12_26_9', 'sentiment_score']
X = df[features]
y = df['target']

# 3. Split Data (Shuffle=False because it's time-series data!)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# 4. Train Random Forest
print("Training Random Forest...")
rf = RandomForestClassifier()
rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)
print(f"Random Forest Accuracy: {accuracy_score(y_test, rf_pred):.4f}")

# 5. Train XGBoost
print("Training XGBoost...")
xgb = XGBClassifier()
xgb.fit(X_train, y_train)
xgb_pred = xgb.predict(X_test)
print(f"XGBoost Accuracy: {accuracy_score(y_test, xgb_pred):.4f}")
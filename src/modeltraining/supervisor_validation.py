import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import seaborn as sns
import os
import joblib

def run_supervisor_validation():
    print("🎓 Starting Supervisor Validation Protocol (Multi-Stock Generalization)...")
    
    # 1. Load the Generalized Data
    input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # 2. Setup Features
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    for col in df.columns:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    print(f"   - Features Used: {feature_cols}")
    
    # 3. Safe Time-Series Split (80/20 Per Stock)
    train_dfs, test_dfs = [], []
    for ticker, group in df.groupby('ticker'):
        group = group.sort_values('date') # Sort oldest to newest
        split_idx = int(len(group) * 0.8)
        train_dfs.append(group.iloc[:split_idx])
        test_dfs.append(group.iloc[split_idx:])
        
    train_df = pd.concat(train_dfs)
    test_df = pd.concat(test_dfs)
    
    X_train = train_df[feature_cols]
    y_train = train_df['Target']
    
    # Calculate Global Class Imbalance
    ratio = float(np.sum(y_train == 0)) / np.sum(y_train == 1)
    aggressive_weight = ratio * 2.5 
    print(f"   - Global Training Rows: {len(X_train)}")

    # 4. Define Generalized Models
    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=10, 
            class_weight={0: 1, 1: aggressive_weight}, min_samples_leaf=15, random_state=42
        ),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=10, 
            subsample=0.8, colsample_bytree=1.0, scale_pos_weight=aggressive_weight, random_state=42
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.05, num_leaves=70, 
            min_child_samples=15, subsample=0.8, colsample_bytree=1.0, 
            scale_pos_weight=aggressive_weight, verbosity=-1, random_state=42
        )
    }
    
    # 5. Train All Models on the Global Dataset
    print("\n🧠 Training models on generalized multi-stock data...")
    for name, model in models.items():
        model.fit(X_train, y_train)
        
    # =========================================================
    # PART A: Detailed Comparative Analysis on Main Stock (GTCO)
    # =========================================================
    print("\n📊 PART A: Comparative Analysis on Main Stock (GTCO)")
    print("-" * 75)
    print(f"{'Model':<15} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 75)
    
    gtco_test = test_df[test_df['ticker'] == 'GTCO']
    X_gtco, y_gtco = gtco_test[feature_cols], gtco_test['Target']
    
    metrics_list = []
    
    for name, model in models.items():
        preds = model.predict(X_gtco)
        acc = accuracy_score(y_gtco, preds)
        prec = precision_score(y_gtco, preds, zero_division=0)
        rec = recall_score(y_gtco, preds, zero_division=0)
        f1 = f1_score(y_gtco, preds, zero_division=0)
        
        print(f"{name:<15} | {acc:.4f}     | {prec:.4f}     | {rec:.4f}     | {f1:.4f}")
        metrics_list.append({"Model": name, "Metric": "F1-Score", "Score": f1})
        
    # Generate Chart for Chapter 4
    metrics_df = pd.DataFrame(metrics_list)
    plt.figure(figsize=(8, 5))
    sns.barplot(x="Model", y="Score", data=metrics_df, palette="viridis")
    plt.title("Model Generalization Test: F1-Scores on GTCO", fontweight='bold')
    plt.ylim(0, 1.0)
    plt.ylabel("F1-Score")
    
    os.makedirs("src/analysis", exist_ok=True)
    plt.savefig("src/analysis/supervisor_comparison_chart.png", dpi=300)
    
    # =========================================================
    # PART B: Validation on Additional Stocks (ZENITH & MTNN)
    # =========================================================
    print("\n✅ PART B: Validating LightGBM on Additional Stocks")
    print("-" * 55)
    print(f"{'Ticker':<15} | {'LightGBM F1-Score':<20}")
    print("-" * 55)
    
    lgbm_model = models["LightGBM"]
    validation_tickers = ['ZENITH', 'MTNN']
    
    for val_ticker in validation_tickers:
        val_test = test_df[test_df['ticker'] == val_ticker]
        if not val_test.empty:
            X_val, y_val = val_test[feature_cols], val_test['Target']
            val_preds = lgbm_model.predict(X_val)
            val_f1 = f1_score(y_val, val_preds, zero_division=0)
            print(f"{val_ticker:<15} | {val_f1:.4f}")
            
    # Save the new Generalized Champion Model!
    joblib.dump(lgbm_model, "models/best_stock_model_optimized.pkl")
    print("\n🏆 Generalized LightGBM model saved to production!")
    print("   (Chart saved to src/analysis/supervisor_comparison_chart.png)")

if __name__ == "__main__":
    run_supervisor_validation()
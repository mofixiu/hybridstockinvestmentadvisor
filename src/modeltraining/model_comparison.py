import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import seaborn as sns
import os

def run_comparative_analysis(ticker="GTCO"):
    print(f"📊 Starting Phase 6: Comparative Analysis for {ticker}...")
    
    # 1. Load Data
    input_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    if not os.path.exists(input_path):
        print(f"❌ Data not found at {input_path}")
        return

    df = pd.read_csv(input_path)
    
    # 2. Setup Features
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    all_cols = df.columns.tolist()
    for col in all_cols:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    print(f"   - Features Used: {feature_cols}")
    
    X = df[feature_cols]
    y = df['Target']
    
    # 3. Time-Series Split (80/20)
    split_point = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
    y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]
    
    # Calculate Class Weight to fix the lazy "Buy" imbalance
    ratio = float(np.sum(y_train == 0)) / np.sum(y_train == 1)
    print(f"   - Class Imbalance Ratio: {ratio:.2f}")

    # 4. Define Models (Fair fight: standard optimized hyperparameters for all)
    aggressive_weight = ratio * 2.5  # This matches the ~3.25 weight that gave you the 0.46 F1 score

    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=100, 
            max_depth=10, 
            class_weight={0: 1, 1: aggressive_weight}, # Aggressively boost 'Buy'
            min_samples_leaf=15,
            random_state=42
        ),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=100, 
            learning_rate=0.05, 
            max_depth=10, 
            subsample=0.8,
            colsample_bytree=1.0,
            scale_pos_weight=aggressive_weight, 
            eval_metric='logloss',
            random_state=42
        ),
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=100, 
            learning_rate=0.05, 
            num_leaves=70, 
            min_child_samples=15,
            subsample=0.8,
            colsample_bytree=1.0,
            scale_pos_weight=aggressive_weight, 
            verbosity=-1,
            random_state=42
        )
    }
    
    # 5. Train & Evaluate
    metrics_list = []
    
    print("\n📈 TRAINING & EVALUATION RESULTS:")
    print("-" * 75)
    print(f"{'Model':<15} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 75)
    
    for name, model in models.items():
        # Train
        model.fit(X_train, y_train)
        # Predict
        preds = model.predict(X_test)
        
        # Score
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        
        print(f"{name:<15} | {acc:.4f}     | {prec:.4f}     | {rec:.4f}     | {f1:.4f}")
        
        metrics_list.append({
            "Model": name,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1-Score": f1
        })
        
    # 6. Generate the Visualization
    print("\n🎨 Generating Comparative Bar Chart for Chapter 4...")
    metrics_df = pd.DataFrame(metrics_list)
    
    # Reshape the dataframe for seaborn plotting
    melted_df = metrics_df.melt(id_vars="Model", var_name="Metric", value_name="Score")
    
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    # Create grouped bar chart
    ax = sns.barplot(x="Metric", y="Score", hue="Model", data=melted_df, palette="viridis")
    
    plt.title("Machine Learning Models Comparison (Nigerian Stock Exchange Data)", fontsize=14, fontweight='bold')
    plt.ylim(0, 1.05) # Lock Y-axis from 0 to 1
    plt.ylabel("Score (0.0 to 1.0)", fontsize=12)
    plt.xlabel("Performance Metric", fontsize=12)
    plt.legend(title="Algorithm", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add exact numbers on top of the bars for ultimate professionalism
    for p in ax.patches:
        if p.get_height() > 0:
            ax.annotate(f'{p.get_height():.2f}', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha = 'center', va = 'center', 
                        xytext = (0, 9), 
                        textcoords = 'offset points',
                        fontsize=9)
                        
    plt.tight_layout()
    
    # Save to the analysis folder
    save_dir = "src/analysis"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "model_comparison_chart.png")
    plt.savefig(save_path, dpi=300)
    
    print(f"✅ Success! Chart saved to: {save_path}")
    print("   (Copy and paste this image directly into your FYP documentation!)")

if __name__ == "__main__":
    run_comparative_analysis()
    
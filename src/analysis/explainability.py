import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt
import os

def explain_model(ticker="GTCO"):
    print(f"🔬 Running SHAP Analysis for {ticker}...")
    
    # 1. Load Data & Model
    data_path = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
    model_path = "models/best_stock_model_optimized.pkl"
    
    if not os.path.exists(data_path) or not os.path.exists(model_path):
        print("❌ Missing files.")
        return

    df = pd.read_csv(data_path)
    model = joblib.load(model_path)
    
    # 2. Prepare Features (Use the same columns as training)
    feature_cols = ['RSI', 'EMA_50', 'EMA_200', 'avg_sentiment']
    for col in df.columns:
        if any(x in col for x in ['MACD', 'BBL', 'BBM', 'BBU']):
            feature_cols.append(col)
            
    X = df[feature_cols]
    
    # 3. Initialize SHAP Explainer
    # LightGBM is a Tree model, so we use TreeExplainer (very fast)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    
    # Handle SHAP binary classification output (sometimes returns list of 2 arrays)
    # We want the values for Class 1 (Buy)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    # 4. PLOT 1: Summary Plot (Global Importance)
    # This shows which features matter most overall (e.g., Is RSI more important than Sentiment?)
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X, show=False)
    
    output_summary = f"src/analysis/{ticker}_shap_summary.png"
    plt.savefig(output_summary, bbox_inches='tight')
    print(f"✅ Summary Plot saved to {output_summary}")
    plt.close()

    # 5. PLOT 2: Force Plot (Local Explanation for TODAY)
    # This explains the LAST row in your data (Today's prediction)
    # "Why did you say HOLD today?"
    
    latest_row = X.iloc[-1]
    # We need the base value (average model output) to compare against
    expected_value = explainer.expected_value
    if isinstance(expected_value, list) or isinstance(expected_value, np.ndarray):
        expected_value = expected_value[1] # Class 1 base value

    # Generate a Force Plot (Interactive HTML)
    force_plot = shap.force_plot(
        expected_value, 
        shap_values[-1], 
        latest_row, 
        matplotlib=False,
        show=False
    )
    
    output_html = f"src/analysis/{ticker}_explanation_today.html"
    shap.save_html(output_html, force_plot)
    print(f"✅ Interactive Explanation saved to {output_html}")
    
    # 6. Text Explanation
    print("\n🧐 WHAT DROVE TODAY'S DECISION?")
    # Get top 3 features for the last prediction
    vals = list(zip(feature_cols, shap_values[-1]))
    vals.sort(key=lambda x: abs(x[1]), reverse=True) # Sort by impact magnitude
    
    for feature, impact in vals[:3]:
        direction = "Positive (+)" if impact > 0 else "Negative (-)"
        print(f"   - {feature}: {impact:.4f} impact ({direction})")

if __name__ == "__main__":
    import numpy as np # Needed for array checks
    explain_model("GTCO")
from fastapi import FastAPI
import pandas as pd
import os

# Initialize the API
app = FastAPI(
    title="HybStockAdvisor API",
    description="Backend API serving ML predictions for the Nigerian Stock Market",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"status": "Online", "message": "Welcome to the HybStockAdvisor Engine"}

@app.get("/api/forecast/{ticker}")
def get_forecast(ticker: str):
    print(f"📡 API Request received for: {ticker.upper()}")
    
    # Locate the Safety Index file generated in Week 9
    file_path = f"data/processed/{ticker.upper()}_SAFETY_INDEX.csv"
    
    if not os.path.exists(file_path):
        return {"error": "Data not found. Please run the AI pipeline for this ticker first."}
    
    # Read the data and get the latest 5 days
    df = pd.read_csv(file_path)
    latest_data = df.tail(5).to_dict(orient="records")
    
    # Return the data as a JSON object (which your app will easily read)
    return {
        "ticker": ticker.upper(),
        "status": "success",
        "data": latest_data
    }
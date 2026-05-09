#!/usr/bin/env python3
"""
Health check script to keep Render service alive
Pings the API health endpoint every 10 minutes
"""
import requests
import os
from datetime import datetime

# Your Render service URL - update this with your actual Render URL
RENDER_URL = os.getenv("RENDER_URL", "https://your-app.onrender.com")
HEALTH_ENDPOINT = f"{RENDER_URL}/"

def health_check():
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=10)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if response.status_code == 200:
            print(f"[{timestamp}] ✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"[{timestamp}] ⚠️  Health check returned status {response.status_code}")
            return False
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ❌ Health check failed: {str(e)}")
        return False

if __name__ == "__main__":
    health_check()

from fastapi import FastAPI
import pandas as pd
import numpy as np
import os
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
import random
import uuid
import smtplib
from google import genai
from google.genai import types
import glob
from typing import Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Initialize the API
app = FastAPI(
    title="HybStockAdvisor API",
    description="Backend API serving ML predictions for the Nigerian Stock Market",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"status": "Online", "message": "Welcome to the HybStockAdvisor Engine"}

# @app.get("/api/forecast/{ticker}")
# def get_forecast(ticker: str):
#     print(f"📡 API Request received for: {ticker.upper()}")
    
#     # Locate the Safety Index file generated in Week 9
#     file_path = f"data/processed/{ticker.upper()}_SAFETY_INDEX.csv"
    
#     if not os.path.exists(file_path):
#         return {"error": "Data not found. Please run the AI pipeline for this ticker first."}
    
#     # Read the data and get the latest 5 days
#     df = pd.read_csv(file_path)
#     latest_data = df.tail(5).to_dict(orient="records")
    
#     # Return the data as a JSON object (which your app will easily read)
#     return {
#         "ticker": ticker.upper(),
#         "status": "success",
#         "data": latest_data
#     }
# Import the database logic we just created
from src.api.database import PasswordReset, get_db, User

# Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Pydantic Models (To validate the incoming JSON from Flutter) ---
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str
    
class PortfolioCreate(BaseModel):
    user_id: int
    ticker: str
    quantity: float
    average_buy_price: float

class WatchlistCreate(BaseModel):
    user_id: int
    ticker: str
class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str
class ChatMessage(BaseModel):
    text: str
    current_ticker: Optional[str] = None  # 🚨 Added this so Flutter can pass the screen context
class RemoveItemRequest(BaseModel):
    user_id: int
    ticker: str
# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/auth/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user in the MySQL database."""
    # 1. Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # 2. Hash the password for security
    hashed_password = pwd_context.hash(user.password)
    
    # 3. Save to database
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "status": "success", 
        "message": "Account created successfully",
        "data": {"user_id": new_user.id, "username": new_user.username}
    }

@app.post("/api/auth/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """Verifies credentials and issues a simple token."""
    # 1. Find user by email
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # 2. Generate a simple token (For enterprise, use JWT. This is perfect for FYP).
    # We combine user_id and email so Flutter knows who is logged in.
    fake_token = f"auth_token_{db_user.id}_{db_user.username}"
    
    return {
        "status": "success",
        "message": "Login successful",
        "token": fake_token,
        "user_data": {
            "id": db_user.id,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,  
            "username": db_user.username,
            "email": db_user.email
        }
    }
from src.api.database import get_db, User, Portfolio, Watchlist
@app.get("/api/insights/{ticker}")
def get_insights(ticker: str):
    """Generates a text-based AI explanation from the technical data."""
    file_path = f"data/processed/{ticker}_SAFETY_INDEX.csv"
    if not os.path.exists(file_path):
        return {"status": "error", "error": "Data not found"}
    
    df = pd.read_csv(file_path)
    # Replace any NaNs to prevent JSON crashes
    latest = df.iloc[-1].replace([np.inf, -np.inf], np.nan).fillna(0)
    
    rec = latest['Recommendation']
    rsi = float(latest['RSI'])
    ema50 = float(latest['EMA_50'])
    close = float(latest['close'])
    
    # --- The Auto-Generated AI Text ---
    explanation = f"Our LightGBM model has analyzed {ticker}. "
    if close > ema50:
        explanation += f"The asset is currently trading at ₦{close:.2f}, which is above its 50-day moving average (₦{ema50:.2f}), indicating underlying bullish momentum. "
    else:
        explanation += f"The asset is trading at ₦{close:.2f}, below its 50-day moving average (₦{ema50:.2f}), showing bearish pressure. "
        
    if rsi > 70:
        explanation += f"However, with an RSI of {rsi:.1f}, the stock is technically overbought and may face an imminent price correction."
    elif rsi < 30:
        explanation += f"With an RSI of {rsi:.1f}, the stock is currently oversold, presenting a potential discounted entry opportunity."
    else:
        explanation += f"The RSI sits in neutral territory at {rsi:.1f}, suggesting stable price consolidation."

    # --- UI Impact Calculations (-1.0 to 1.0) ---
    # Convert RSI to an impact score. 50 is neutral (0). 30 is good (+0.4). 70 is bad (-0.4).
    rsi_impact = (50 - rsi) / 50 
    
    # Convert EMA to an impact score
    ema_pct_diff = (close - ema50) / ema50
    ema_impact = max(-1.0, min(1.0, ema_pct_diff * 10)) # Cap at -1 and 1
    
    return {
        "status": "success",
        "data": {
            "ticker": ticker,
            "recommendation": rec,
            "explanation": explanation,
            "ai_confidence": float(latest['AI_Score']),
            "market_stability": float(latest['Stability_Score']),
            "public_sentiment": float(latest['Sentiment_Rescaled']),
            "safety_index": float(latest['Safety_Index']),
            "rsi_impact": float(rsi_impact),
            "ema_impact": float(ema_impact)
        }
    }
@app.get("/api/forecast/{ticker}")
def get_forecast(ticker: str):
    file_path = f"data/processed/{ticker}_SAFETY_INDEX.csv"
    
    if not os.path.exists(file_path):
        return {"status": "error", "error": "Data not found. Please run the AI pipeline first."}
        
    try:
        df = pd.read_csv(file_path)
        
        # --- THE FIX: Replace NaN and Infinity with None so JSON doesn't crash ---
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.where(pd.notnull(df), None)
        # -------------------------------------------------------------------------
        
        # Get the last 5 days
        recent_data = df.tail(5).to_dict(orient="records")
        
        return {
            "status": "success",
            "data": recent_data
        }
    except Exception as e:
        # This will print the exact error in your terminal if it fails again
        print(f"API CRASH ERROR: {e}") 
        return {"status": "error", "error": str(e)}

# @app.get("/api/summary")
# def get_market_summary():
#     """Returns the latest price and 24h change for all analyzed stocks in one call."""
#     processed_dir = "data/processed"
#     summary = []
    
#     if not os.path.exists(processed_dir):
#         return {"status": "error", "message": "No processed data found"}
        
#     for file in os.listdir(processed_dir):
#         if file.endswith("_SAFETY_INDEX.csv"):
#             ticker = file.replace("_SAFETY_INDEX.csv", "")
#             try:
#                 df = pd.read_csv(os.path.join(processed_dir, file))
#                 if not df.empty:
#                     latest = df.iloc[-1]
#                     # Get yesterday to calculate the percentage change
#                     prev = df.iloc[-2] if len(df) > 1 else latest
#                     price = float(latest['close'])
#                     prev_price = float(prev['close'])
                    
#                     change_pct = ((price - prev_price) / prev_price) * 100 if prev_price != 0 else 0.0
                    
#                     summary.append({
#                         "symbol": ticker,
#                         "price": price,
#                         "change_pct": change_pct
#                     })
#             except Exception as e:
#                 continue
                
#     return {"status": "success", "data": summary}
@app.get("/api/summary")
def get_market_summary():
    """Returns the latest price, 24h change, Name, and Market Cap for all analyzed stocks."""
    processed_dir = "data/processed"
    summary = []
    
    # A tiny fallback dictionary just in case your CSVs don't have the 'Name' column yet
    fallback_names = {
        "GTCO": "Guaranty Trust Holding",
        "ZENITHBANK": "Zenith Bank Plc",
        "UBA": "United Bank for Africa",
        "DANGCEM": "Dangote Cement",
        "MTNN": "MTN Nigeria",
        "WEMABANK": "Wema Bank Plc"
    }
    
    if not os.path.exists(processed_dir):
        return {"status": "error", "message": "No processed data found"}
        
    for file in os.listdir(processed_dir):
        if file.endswith("_SAFETY_INDEX.csv"):
            ticker = file.replace("_SAFETY_INDEX.csv", "")
            try:
                df = pd.read_csv(os.path.join(processed_dir, file))
                if not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    price = float(latest['close'])
                    prev_price = float(prev['close'])
                    
                    change_pct = ((price - prev_price) / prev_price) * 100 if prev_price != 0 else 0.0
                    
                    # # Safely grab Name and Market Cap (Defaults to N/A if you haven't scraped it yet)
                    # latest_dict = latest.to_dict()
                    # company_name = latest_dict.get('Name', fallback_names.get(ticker, f"{ticker} Plc"))
                    # market_cap = latest_dict.get('Market_Cap', "N/A")
                    latest_dict = latest.to_dict()
                    company_name = latest_dict.get('Name', f"{ticker} Plc")
                    market_cap = latest_dict.get('Market_Cap', "--")
                    summary.append({
                        "symbol": ticker,
                        "name": str(company_name),
                        "market_cap": str(market_cap),
                        "price": price,
                        "change_pct": change_pct
                    })
            except Exception as e:
                continue
                
    return {"status": "success", "data": summary}

@app.post("/api/portfolio/add")
def add_to_portfolio(item: PortfolioCreate, db: Session = Depends(get_db)):
    new_entry = Portfolio(
        user_id=item.user_id,
        ticker=item.ticker,
        quantity=item.quantity,
        average_buy_price=item.average_buy_price
    )
    db.add(new_entry)
    db.commit()
    return {"status": "success"}
# ── Email Sending Utility & Template ─────────────────────────────
def send_otp_email(receiver_email: str, user_first_name: str, otp_code: str):
    """Sends a premium HTML email with the OTP."""
    
    # ⚠️ NOTE FOR DEFENSE: To actually send emails, replace these with a real Gmail address
    # and an "App Password" generated from your Google Account settings.
    # For testing right now, this function will just print the OTP to your terminal!
    SENDER_EMAIL = "your_email@gmail.com" 
    SENDER_PASSWORD = "your_app_password" 
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #F2F4F7; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <h2 style="color: #0A3D62; text-align: center; margin-bottom: 10px;">HybStockAdvisor</h2>
            <p style="color: #555; font-size: 16px;">Hello {user_first_name},</p>
            <p style="color: #555; font-size: 16px;">We received a request to reset the password for your account. Your password reset code is:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #0A3D62; background-color: rgba(10, 61, 98, 0.1); padding: 15px 30px; border-radius: 8px;">
                    {otp_code}
                </span>
            </div>
            
            <p style="color: #555; font-size: 14px;">This code will expire in <strong>15 minutes</strong>. If you did not request this, please ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">Secure your investments with AI.<br>The HybStockAdvisor Team</p>
        </div>
    </body>
    </html>
    """
    
    print(f"\n{'='*50}\n📧 MOCK EMAIL SENT TO: {receiver_email}\nOTP CODE: {otp_code}\n{'='*50}\n")
    
    # Uncomment the code below when you are ready to send real emails
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = "Your Password Reset Code - HybStockAdvisor"
        msg.attach(MIMEText(html_template, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")
   

# ── Password Reset Endpoints ─────────────────────────────────────

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
        
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=15)
    
    # Check if they already have an active reset request
    existing_reset = db.query(PasswordReset).filter(PasswordReset.email == req.email).first()
    if existing_reset:
        existing_reset.otp = otp
        existing_reset.expires_at = expiry
        existing_reset.reset_token = None # Clear any old tokens
    else:
        new_reset = PasswordReset(email=req.email, otp=otp, expires_at=expiry)
        db.add(new_reset)
        
    db.commit()
    
    # Send the email
    send_otp_email(user.email, user.first_name, otp)
    
    return {"status": "success", "message": "OTP sent to email"}

@app.post("/api/auth/verify-reset-otp")
def verify_otp(req: VerifyOtpRequest, db: Session = Depends(get_db)):
    reset_record = db.query(PasswordReset).filter(PasswordReset.email == req.email).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="No reset request found")
        
    if reset_record.otp != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
        
    if datetime.now() > reset_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired")
        
    # Success! Generate a secure token so they can change their password
    secure_token = str(uuid.uuid4())
    reset_record.reset_token = secure_token
    db.commit()
    
    return {"status": "success", "reset_token": secure_token}

@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_record = db.query(PasswordReset).filter(PasswordReset.reset_token == req.reset_token).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset session")
        
    # Find the user and update password
    user = db.query(User).filter(User.email == reset_record.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = pwd_context.hash(req.new_password)
    
    # Delete the reset record so it can't be used again
    db.delete(reset_record)
    db.commit()
    
    return {"status": "success", "message": "Password has been reset successfully"}
@app.post("/api/watchlist/add")
def add_to_watchlist(item: WatchlistCreate, db: Session = Depends(get_db)):
    # Check if already exists
    existing = db.query(Watchlist).filter_by(user_id=item.user_id, ticker=item.ticker).first()
    if existing:
        return {"status": "error", "detail": "Already in watchlist"}
        
    new_entry = Watchlist(user_id=item.user_id, ticker=item.ticker)
    db.add(new_entry)
    db.commit()
    return {"status": "success"}

# --- AI CHATBOT ENDPOINT ---

# Configure Gemini with your API Key

# @app.post("/api/chat")
# def ai_chat(req: ChatMessage):
#     user_message = req.text.upper()
#     context_data = ""
    
#     # 1. Context Injection: Check if they mentioned any stock we track
#     processed_dir = "data/processed"
#     if os.path.exists(processed_dir):
#         for file in os.listdir(processed_dir):
#             if file.endswith("_SAFETY_INDEX.csv"):
#                 ticker = file.replace("_SAFETY_INDEX.csv", "")
                
#                 # If the user's message contains the stock ticker (e.g., "GTCO")
#                 if ticker in user_message:
#                     try:
#                         df = pd.read_csv(os.path.join(processed_dir, file))
#                         latest = df.iloc[-1]
                        
#                         # Build a secret summary of the math for Gemini
#                         context_data += f"\nData for {ticker}: Price=₦{latest['close']:.2f}, RSI={latest['RSI']:.1f}, "
#                         context_data += f"50-EMA=₦{latest['EMA_50']:.2f}, 200-EMA=₦{latest['EMA_200']:.2f}, "
#                         context_data += f"Final Recommendation={latest['Recommendation']}, AI Confidence={latest['AI_Score']:.1f}%.\n"
#                     except Exception:
#                         pass
    
#     # 2. Build the System Prompt (The Chatbot's Personality)
#     system_prompt = f"""
#     You are Lexi, a professional, smart, and friendly AI financial assistant for the Nigerian Stock Exchange (NGX).
#     Keep your answers concise, conversational, and easy to understand for a beginner investor.
#     Format your text nicely. Do not use more than 4 sentences unless asked for detail.
    
#     Here is the live mathematical data for the stocks the user is asking about (if any):
#     {context_data if context_data else 'No specific stock data pulled. Answer general finance questions.'}
    
#     RULES:
#     - If the data shows a BUY, explain that it's because of strong technicals.
#     - If it shows a SELL, warn them about Overbought conditions (RSI > 70) or a Death Cross.
#     - Never invent fake prices. ONLY use the prices provided in the data above.
#     """
    
#     # 3. Call Gemini
#     try:
#         model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
#         response = model.generate_content(req.text)
#         return {"status": "success", "reply": response.text}
#     except Exception as e:
#         print(f"Gemini Error: {e}")
#         return {"status": "error", "reply": "Sorry, my AI servers are currently resting. Try again in a moment!"}
    
@app.post("/api/chat")
def ai_chat(req: ChatMessage):
    user_message = req.text.upper()
    context_data = ""
    processed_dir = "data/processed"
    
    target_tickers = []
    
    # 1. Did the app tell us what screen the user is looking at?
    if req.current_ticker:
        target_tickers.append(req.current_ticker.upper())
        
    # 2. Did they explicitly mention any other stocks in their text?
    if os.path.exists(processed_dir):
        for file in os.listdir(processed_dir):
            if file.endswith("_SAFETY_INDEX.csv"):
                ticker = file.replace("_SAFETY_INDEX.csv", "")
                if ticker in user_message and ticker not in target_tickers:
                    target_tickers.append(ticker)

    # 3. Build the Data Context for Gemini (NOW INCLUDES SAFETY INDEX!)
    for ticker in target_tickers:
        file_path = os.path.join(processed_dir, f"{ticker}_SAFETY_INDEX.csv")
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                latest = df.iloc[-1]
                
                context_data += f"\nData for {ticker} (Currently on screen): Price=₦{latest['close']:.2f}, RSI={latest['RSI']:.1f}, "
                context_data += f"50-EMA=₦{latest['EMA_50']:.2f}, 200-EMA=₦{latest['EMA_200']:.2f}, "
                context_data += f"Recommendation={latest['Recommendation']}, Safety Index={latest['Safety_Index']:.1f}/100, "
                context_data += f"AI Score={latest['AI_Score']:.1f}%, Market Stability={latest['Stability_Score']:.1f}%, Sentiment={latest['Sentiment_Rescaled']:.1f}%.\n"
            except Exception:
                pass
    
    # 4. Build the System Prompt (TEACHING IT YOUR CUSTOM MATH)
    system_prompt = f"""
    You are Lexi, a professional, smart, and friendly AI financial assistant for the NGX.
    Keep your answers concise, conversational, and easy to understand.
    
    Here is the live mathematical data for the stocks the user is asking about or looking at:
    {context_data if context_data else 'No specific stock data pulled. Answer general finance questions.'}
    
    CRITICAL RULES ON HOW TO EXPLAIN THE "SAFETY INDEX":
    If the user asks how the Safety Index or recommendation is calculated, YOU MUST EXPLAIN THIS EXACT FORMULA:
    1. AI Confidence (50% weight): Uses a deeply optimized LightGBM Machine Learning model to predict price action.
    2. Market Stability (30% weight): Uses the 14-day RSI (Relative Strength Index) to measure volatility.
    3. Public Sentiment (20% weight): Uses a custom "Naija-FinBERT" Natural Language Processing model to analyze news and social media sentiment.
    4. Financial Guardrails: The final score is penalized if the stock is overbought (RSI > 70) or in a bearish Death Cross (50-EMA < 200-EMA), and boosted for oversold conditions or Golden Crosses.
    
    GENERAL RULES:
    - Never invent fake prices or metrics. Rely solely on the context provided.
    - If the data says "BUY", explain it using the positive metrics provided.
    """
    
    # 5. Call Gemini using the NEW SDK
    try:
        # Initialize the new client with your API key
        client = genai.Client(api_key="AIzaSyAplxYC0QRP2bzCIgd3p273RsEiiLoHzPg")
        
        # Send the request using the new configuration format
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=req.text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            )
        )
        return {"status": "success", "reply": response.text}
        
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini Error: {error_msg}")
        
        # If we hit the Google speed limit, tell the user gracefully
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {
                "status": "error", 
                "reply": "I am receiving a lot of questions right now! 😅 Please wait about 60 seconds and ask me again."
            }
            
        return {"status": "error", "reply": "Sorry, my AI servers are currently resting. Try again in a moment!"}
    
@app.delete("/api/portfolio/remove")
def remove_from_portfolio(item: RemoveItemRequest, db: Session = Depends(get_db)):
    # 1. Look for the exact stock owned by this specific user
    db_item = db.query(Portfolio).filter(
        Portfolio.user_id == item.user_id, 
        Portfolio.ticker == item.ticker
    ).first()
    
    # 2. If it doesn't exist, throw a 404 error
    if not db_item:
        raise HTTPException(status_code=404, detail="Stock not found in portfolio")
        
    # 3. Delete it and save changes
    db.delete(db_item)
    db.commit()
    
    return {"status": "success", "message": f"{item.ticker} removed from portfolio"}

@app.delete("/api/watchlist/remove")
def remove_from_watchlist(item: RemoveItemRequest, db: Session = Depends(get_db)):
    # 1. Look for the exact stock watched by this specific user
    db_item = db.query(Watchlist).filter(
        Watchlist.user_id == item.user_id, 
        Watchlist.ticker == item.ticker
    ).first()
    
    # 2. If it doesn't exist, throw a 404 error
    if not db_item:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
        
    # 3. Delete it and save changes
    db.delete(db_item)
    db.commit()
    
    return {"status": "success", "message": f"{item.ticker} removed from watchlist"}

@app.get("/api/user/{user_id}/assets")
def get_user_assets(user_id: int, db: Session = Depends(get_db)):
    """Returns both the user's Portfolio and Watchlist in one call."""
    
    # 1. Get Portfolio from DB
    portfolio_db = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    # 2. Get Watchlist from DB
    watchlist_db = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    
    portfolio_list = []
    watchlist_list = []
    
    # --- Helper logic: We need to attach the LIVE PRICE to these saved tickers ---
    processed_dir = "data/processed"
    
    def get_live_stats(ticker):
        file_path = os.path.join(processed_dir, f"{ticker}_SAFETY_INDEX.csv")
        try:
            df = pd.read_csv(file_path)
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            price = float(latest['close'])
            prev_price = float(prev['close'])
            change_pct = ((price - prev_price) / prev_price) * 100 if prev_price != 0 else 0.0
            
            # Extract last 7 days of closing prices for the sparkline chart!
            spark_data = df['close'].tail(7).tolist()
            
            return price, change_pct, spark_data
        except:
            return 0.0, 0.0, [0.0]*7

    # Build Portfolio Output
    for p in portfolio_db:
        live_price, change_pct, spark = get_live_stats(p.ticker)
        portfolio_list.append({
            "id": p.id,
            "ticker": p.ticker,
            "quantity": float(p.quantity),
            "avg_buy_price": float(p.average_buy_price),
            "live_price": live_price,
            "change_pct": change_pct,
            "spark_data": spark
        })
        
    # Build Watchlist Output
    for w in watchlist_db:
        live_price, change_pct, spark = get_live_stats(w.ticker)
        watchlist_list.append({
            "id": w.id,
            "ticker": w.ticker,
            "live_price": live_price,
            "change_pct": change_pct,
            "spark_data": spark
        })

    return {
        "status": "success",
        "data": {
            "portfolio": portfolio_list,
            "watchlist": watchlist_list
        }

    }

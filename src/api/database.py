# from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, text
# from sqlalchemy.orm import declarative_base, sessionmaker

# # 1. Connection String for Local MySQL
# # Format: mysql+pymysql://username:password@host:port/database_name
# # Note: Default XAMPP/MAMP/DBngin uses user 'root' with NO password.
# DATABASE_URL = "mysql+pymysql://root:david001@127.0.0.1:3306/hybstockadvisor"

# engine = create_engine(DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()

# # 2. Python Representation of your MySQL 'users' Table
# class User(Base):
#     __tablename__ = "users"
    
#     id = Column(Integer, primary_key=True, index=True)
#     first_name = Column(String(100), nullable=False)
#     last_name = Column(String(100), nullable=False)
#     username = Column(String(50), unique=True, nullable=False)
#     email = Column(String(150), unique=True, nullable=False)
#     password_hash = Column(String(255), nullable=False)
#     risk_tolerance = Column(String(50), default="High")
#     created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

# # Dependency to get the DB session for our API routes
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import DateTime # Add DateTime to your imports at the top!

# 1. Connection String for Local MySQL
DATABASE_URL = "mysql+pymysql://root:david001@127.0.0.1:3306/hybstockadvisor"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 2. Python Representation of your MySQL 'users' Table
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    risk_tolerance = Column(String(50), default="High")
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

# 3. Python Representation of your MySQL 'portfolios' Table
class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    average_buy_price = Column(Float, nullable=False)
    added_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

# 4. Python Representation of your MySQL 'watchlists' Table
class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False)
    added_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False)
    otp = Column(String(6), nullable=False)
    reset_token = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=False)

# Dependency to get the DB session for our API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    is_subscribed = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)
    plan = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def is_active(self) -> bool:
        if not self.is_subscribed or not self.subscription_end:
            return False
        return self.subscription_end > datetime.utcnow()

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    amount_usd = Column(Float, nullable=False)
    currency = Column(String, nullable=False)  # USDT, BTC, ETH
    transaction_hash = Column(String, unique=True, nullable=True)
    status = Column(String, default="pending")  # pending, confirmed, rejected
    plan = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    coin_symbol = Column(String, nullable=False)
    analysis_result = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

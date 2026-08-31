from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_premium = Column(Boolean, default=False)
    subscription_expiry = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_hash = Column(String(200), unique=True)
    amount = Column(Float)
    currency = Column(String(20), default="USDT")
    network = Column(String(10))
    plan_type = Column(String(50))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    symbol = Column(String(20))
    condition_type = Column(String(50))
    threshold = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    symbol = Column(String(20))
    signal_type = Column(String(20))
    direction = Column(String(10))
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(String(200))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

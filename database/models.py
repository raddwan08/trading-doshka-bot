# database/models.py

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime
)

from database.db import Base


# =========================================
# Users
# =========================================

class User(Base):

    __tablename__ = "users"


    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )


    user_id = Column(
        Integer,
        unique=True,
        nullable=False
    )


    username = Column(
        String,
        nullable=True
    )


    plan = Column(
        String,
        default="free"
    )


    expire_date = Column(
        DateTime,
        nullable=True
    )


    is_active = Column(
        Boolean,
        default=False
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )



# =========================================
# Payments
# =========================================

class Payment(Base):

    __tablename__ = "payments"


    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )


    user_id = Column(
        Integer,
        nullable=False
    )


    plan = Column(
        String,
        nullable=False
    )


    amount = Column(
        Float,
        nullable=False
    )


    currency = Column(
        String,
        default="USDT"
    )


    network = Column(
        String,
        nullable=False
    )


    wallet = Column(
        String,
        nullable=False
    )


    status = Column(
        String,
        default="pending"
    )


    tx_hash = Column(
        String,
        unique=True,
        nullable=True
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    confirmed_at = Column(
        DateTime,
        nullable=True
    )



# =========================================
# Used Transactions
# =========================================

class UsedTransaction(Base):

    __tablename__ = "used_transactions"


    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )


    tx_hash = Column(
        String,
        unique=True,
        nullable=False
    )


    network = Column(
        String,
        nullable=False
    )


    amount = Column(
        Float,
        nullable=False
    )


    user_id = Column(
        Integer,
        nullable=False
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )



# =========================================
# Analysis History
# =========================================

class AnalysisHistory(Base):

    __tablename__ = "analysis_history"


    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )


    user_id = Column(
        Integer,
        nullable=False
    )


    symbol = Column(
        String,
        nullable=False
    )


    school = Column(
        String,
        nullable=False
    )


    result = Column(
        String,
        nullable=True
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

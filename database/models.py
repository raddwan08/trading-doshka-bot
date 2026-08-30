from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from .models import Base, User, Payment, Alert, Signal
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url="sqlite:///crypto_bot.db"):
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
    
    def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            return user
        except Exception as e:
            logger.error(f"Error: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def check_subscription(self, telegram_id):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user and user.is_premium and user.subscription_expiry:
                return user.subscription_expiry > datetime.utcnow()
            return False
        finally:
            session.close()
    
    def activate_subscription(self, telegram_id, plan_type, duration_days):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.is_premium = True
                user.subscription_expiry = datetime.utcnow() + timedelta(days=duration_days)
                session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def add_payment(self, telegram_id, transaction_hash, amount, network, plan_type):
        session = self.get_session()
        try:
            user = self.get_or_create_user(telegram_id)
            if not user:
                return None
            
            existing = session.query(Payment).filter_by(transaction_hash=transaction_hash).first()
            if existing:
                return existing
            
            payment = Payment(
                user_id=user.id,
                transaction_hash=transaction_hash,
                amount=amount,
                network=network,
                plan_type=plan_type,
                status="pending"
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            return payment
        except Exception as e:
            logger.error(f"Error: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_payment_by_hash(self, transaction_hash):
        session = self.get_session()
        try:
            return session.query(Payment).filter_by(transaction_hash=transaction_hash).first()
        finally:
            session.close()
    
    def confirm_payment(self, transaction_hash):
        session = self.get_session()
        try:
            payment = session.query(Payment).filter_by(transaction_hash=transaction_hash).first()
            if payment and payment.status == "pending":
                payment.status = "confirmed"
                payment.confirmed_at = datetime.utcnow()
                session.commit()
                return payment
            return None
        finally:
            session.close()
    
    def get_pending_payments(self):
        session = self.get_session()
        try:
            return session.query(Payment).filter_by(status='pending').all()
        finally:
            session.close()
    
    def create_alert(self, telegram_id, symbol, condition_type, threshold):
        session = self.get_session()
        try:
            user = self.get_or_create_user(telegram_id)
            if not user:
                return None
            
            alert = Alert(
                user_id=user.id,
                symbol=symbol,
                condition_type=condition_type,
                threshold=threshold,
                is_active=True
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert
        except Exception as e:
            logger.error(f"Error: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_active_alerts(self):
        session = self.get_session()
        try:
            return session.query(Alert).filter_by(is_active=True).all()
        finally:
            session.close()
    
    def get_user_alerts(self, telegram_id):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                return session.query(Alert).filter_by(user_id=user.id, is_active=True).all()
            return []
        finally:
            session.close()
    
    def delete_alert(self, alert_id, telegram_id):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                alert = session.query(Alert).filter_by(id=alert_id, user_id=user.id).first()
                if alert:
                    alert.is_active = False
                    session.commit()
                    return True
            return False
        finally:
            session.close()
    
    def get_user_by_id(self, user_id):
        session = self.get_session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            session.close()

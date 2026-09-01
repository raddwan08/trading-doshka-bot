from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from .models import Base, User, Payment, Alert, Signal

import logging


logger = logging.getLogger(__name__)


class DatabaseManager:

    def __init__(self, database_url="sqlite:///crypto_bot.db"):

        if database_url.startswith("postgres://"):

            database_url = database_url.replace(
                "postgres://",
                "postgresql://",
                1
            )

        self.engine = create_engine(
            database_url,
            pool_pre_ping=True
        )

        Base.metadata.create_all(
            self.engine
        )

        self.Session = sessionmaker(
            bind=self.engine
        )


    # =========================================================
    # SESSION
    # =========================================================

    def get_session(self):

        return self.Session()


    # =========================================================
    # USERS
    # =========================================================

    def get_or_create_user(
        self,
        telegram_id,
        username=None,
        first_name=None,
        last_name=None
    ):

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )

                session.add(
                    user
                )

                session.commit()

                session.refresh(
                    user
                )

            return user


        except Exception as e:

            logger.error(
                f"Error creating user: {e}"
            )

            session.rollback()

            return None


        finally:

            session.close()


    def get_user_by_telegram_id(
        self,
        telegram_id
    ):

        session = self.get_session()

        try:

            return session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


        except Exception as e:

            logger.error(
                f"Error getting user: {e}"
            )

            return None


        finally:

            session.close()


    def get_user_by_id(
        self,
        user_id
    ):

        session = self.get_session()

        try:

            return session.query(
                User
            ).filter_by(
                id=user_id
            ).first()


        except Exception as e:

            logger.error(
                f"Error getting user by ID: {e}"
            )

            return None


        finally:

            session.close()


    # =========================================================
    # SUBSCRIPTIONS
    # =========================================================

    def check_subscription(
        self,
        telegram_id
    ):

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if (
                user
                and user.is_premium
                and user.subscription_expiry
            ):

                return (
                    user.subscription_expiry
                    > datetime.utcnow()
                )


            return False


        except Exception as e:

            logger.error(
                f"Error checking subscription: {e}"
            )

            return False


        finally:

            session.close()


    def activate_subscription(
        self,
        telegram_id,
        plan_type,
        duration_days
    ):

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                logger.error(
                    f"User not found: {telegram_id}"
                )

                return False


            now = datetime.utcnow()


            # إذا كان الاشتراك ما زال فعالاً
            # نضيف الأيام الجديدة بعد تاريخ الانتهاء

            if (
                user.subscription_expiry
                and user.subscription_expiry > now
            ):

                start_date = (
                    user.subscription_expiry
                )

            else:

                start_date = now


            user.is_premium = True


            user.subscription_expiry = (
                start_date
                + timedelta(
                    days=duration_days
                )
            )


            session.commit()


            logger.info(
                f"Subscription activated | "
                f"User={telegram_id} | "
                f"Plan={plan_type} | "
                f"Days={duration_days}"
            )


            return True


        except Exception as e:

            logger.error(
                f"Error activating subscription: {e}"
            )

            session.rollback()

            return False


        finally:

            session.close()


    # =========================================================
    # PAYMENTS
    # =========================================================

    def create_pending_payment(
        self,
        telegram_id,
        amount,
        network,
        plan_type
    ):

        """
        إنشاء فاتورة دفع قبل وصول التحويل.

        transaction_hash سيكون فارغاً حتى يتم
        اكتشاف التحويل تلقائياً من البلوكشين.
        """

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                user = User(
                    telegram_id=telegram_id
                )

                session.add(
                    user
                )

                session.commit()

                session.refresh(
                    user
                )


            payment = Payment(

                user_id=user.id,

                transaction_hash=None,

                amount=float(
                    amount
                ),

                network=network.upper(),

                plan_type=plan_type,

                status="pending"
            )


            session.add(
                payment
            )


            session.commit()


            session.refresh(
                payment
            )


            logger.info(
                f"Pending payment created | "
                f"Payment ID={payment.id} | "
                f"User={telegram_id} | "
                f"Amount={amount} | "
                f"Network={network}"
            )


            return payment


        except Exception as e:

            logger.error(
                f"Error creating pending payment: {e}"
            )

            session.rollback()

            return None


        finally:

            session.close()


    def complete_payment(
        self,
        payment_id,
        transaction_hash
    ):

        """
        تأكيد الدفع وربط الفاتورة
        بمعاملة البلوكشين.
        """

        session = self.get_session()

        try:

            payment = session.query(
                Payment
            ).filter_by(
                id=payment_id
            ).first()


            if not payment:

                logger.error(
                    f"Payment not found: {payment_id}"
                )

                return None


            # =================================================
            # منع استخدام نفس المعاملة مرتين
            # =================================================

            existing = session.query(
                Payment
            ).filter_by(
                transaction_hash=transaction_hash
            ).first()


            if (
                existing
                and existing.id != payment_id
            ):

                logger.warning(
                    f"Transaction already used: "
                    f"{transaction_hash}"
                )

                return None


            # =================================================
            # تأكيد الدفع
            # =================================================

            payment.transaction_hash = (
                transaction_hash
            )


            payment.status = "confirmed"


            payment.confirmed_at = (
                datetime.utcnow()
            )


            session.commit()


            session.refresh(
                payment
            )


            logger.info(
                f"Payment confirmed | "
                f"Payment ID={payment_id} | "
                f"Hash={transaction_hash}"
            )


            return payment


        except Exception as e:

            logger.error(
                f"Error completing payment: {e}"
            )

            session.rollback()

            return None


        finally:

            session.close()


    def expire_payment(
        self,
        payment_id
    ):

        """
        إنهاء فاتورة الدفع
        إذا لم يتم الدفع خلال الوقت المحدد.
        """

        session = self.get_session()

        try:

            payment = session.query(
                Payment
            ).filter_by(
                id=payment_id
            ).first()


            if not payment:

                return False


            if payment.status == "pending":

                payment.status = "expired"

                session.commit()


                logger.info(
                    f"Payment expired: {payment_id}"
                )


            return True


        except Exception as e:

            logger.error(
                f"Error expiring payment: {e}"
            )

            session.rollback()

            return False


        finally:

            session.close()


    def add_payment(
        self,
        telegram_id,
        transaction_hash,
        amount,
        network,
        plan_type
    ):

        """
        توافق مع الكود القديم.
        ينشئ دفعة مؤكدة أو معلقة حسب الحاجة.
        """

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                user = User(
                    telegram_id=telegram_id
                )

                session.add(
                    user
                )

                session.commit()

                session.refresh(
                    user
                )


            existing = session.query(
                Payment
            ).filter_by(
                transaction_hash=transaction_hash
            ).first()


            if existing:

                return existing


            payment = Payment(

                user_id=user.id,

                transaction_hash=transaction_hash,

                amount=amount,

                network=network.upper(),

                plan_type=plan_type,

                status="pending"
            )


            session.add(
                payment
            )


            session.commit()


            session.refresh(
                payment
            )


            return payment


        except Exception as e:

            logger.error(
                f"Error adding payment: {e}"
            )

            session.rollback()

            return None


        finally:

            session.close()


    def get_payment_by_hash(
        self,
        transaction_hash
    ):

        session = self.get_session()

        try:

            return session.query(
                Payment
            ).filter_by(
                transaction_hash=transaction_hash
            ).first()


        except Exception as e:

            logger.error(
                f"Error getting payment: {e}"
            )

            return None


        finally:

            session.close()


    def get_payment_by_id(
        self,
        payment_id
    ):

        session = self.get_session()

        try:

            return session.query(
                Payment
            ).filter_by(
                id=payment_id
            ).first()


        except Exception as e:

            logger.error(
                f"Error getting payment: {e}"
            )

            return None


        finally:

            session.close()


    def confirm_payment(
        self,
        transaction_hash
    ):

        """
        دعم للكود القديم.
        """

        session = self.get_session()

        try:

            payment = session.query(
                Payment
            ).filter_by(
                transaction_hash=transaction_hash
            ).first()


            if (
                payment
                and payment.status == "pending"
            ):

                payment.status = "confirmed"

                payment.confirmed_at = (
                    datetime.utcnow()
                )

                session.commit()

                session.refresh(
                    payment
                )

                return payment


            return None


        except Exception as e:

            logger.error(
                f"Error confirming payment: {e}"
            )

            session.rollback()

            return None


        finally:

            session.close()


    def get_pending_payments(self):

        session = self.get_session()

        try:

            return session.query(
                Payment
            ).filter_by(
                status="pending"
            ).all()


        except Exception as e:

            logger.error(
                f"Error getting pending payments: {e}"
            )

            return []


        finally:

            session.close()


    # =========================================================
    # ALERTS
    # =========================================================

    def create_alert(
        self,
        telegram_id,
        symbol,
        condition_type,
        threshold
    ):

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                user = User(
                    telegram_id=telegram_id
                )

                session.add(
                    user
                )

                session.commit()

                session.refresh(
                    user
                )


            alert = Alert(

                user_id=user.id,

                symbol=symbol.upper(),

                condition_type=condition_type,

                threshold=threshold,

                is_active=True
            )


            session.add(
                alert
            )


            session.commit()


            session.refresh(
                alert
            )


            return alert


        except Exception as e:

            logger.error(
                f"Error creating alert: {e}"
            )

            session.rollback()

            return None


        finally:

            session.close()


    def get_active_alerts(self):

        session = self.get_session()

        try:

            return session.query(
                Alert
            ).filter_by(
                is_active=True
            ).all()


        except Exception as e:

            logger.error(
                f"Error getting active alerts: {e}"
            )

            return []


        finally:

            session.close()


    def get_user_alerts(
        self,
        telegram_id
    ):

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                return []


            return session.query(
                Alert
            ).filter_by(
                user_id=user.id,
                is_active=True
            ).all()


        except Exception as e:

            logger.error(
                f"Error getting user alerts: {e}"
            )

            return []


        finally:

            session.close()


    def delete_alert(
        self,
        alert_id,
        telegram_id
    ):

        session = self.get_session()

        try:

            user = session.query(
                User
            ).filter_by(
                telegram_id=telegram_id
            ).first()


            if not user:

                return False


            alert = session.query(
                Alert
            ).filter_by(
                id=alert_id,
                user_id=user.id
            ).first()


            if not alert:

                return False


            alert.is_active = False


            session.commit()


            return True


        except Exception as e:

            logger.error(
                f"Error deleting alert: {e}"
            )

            session.rollback()

            return False


        finally:

            session.close()

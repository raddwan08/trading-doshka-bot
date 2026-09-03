class FuturesService:

    def __init__(
        self,
        db,
        crypto_api
    ):

        self.db = db
        self.crypto_api = crypto_api


    async def send_signals(
        self,
        context
    ):

        print(
            "Futures signal check started"
        )

        # سيتم هنا لاحقاً:
        # تحليل السوق
        # إيجاد الفرص
        # إرسال الإشارات للمشتركين

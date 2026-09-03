import os
import logging
import pkgutil
import importlib

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import (
    analysis_keyboard,
    main_menu_keyboard
)

from services.chart_service import ChartService


logger = logging.getLogger(__name__)

WAITING_SYMBOL = 1


class AnalysisHandler:

    def __init__(
        self,
        db,
        crypto_api
    ):

        self.db = db
        self.crypto_api = crypto_api
        self.chart_service = ChartService()

        self.analysis_modules = (
            self.load_analysis_modules()
        )


    # =====================================
    # AUTO LOAD ANALYSIS SCHOOLS
    # =====================================

    def load_analysis_modules(self):

        modules = {}

        import analysis

        for module_info in pkgutil.iter_modules(
            analysis.__path__
        ):

            module_name = module_info.name


            # تجاهل الملفات الخاصة
            if module_name.startswith("_"):

                continue


            try:

                module = importlib.import_module(
                    f"analysis.{module_name}"
                )


                # يجب أن تحتوي المدرسة على analyze
                if hasattr(
                    module,
                    "analyze"
                ):

                    modules[module_name] = module


                    logger.info(
                        f"Loaded analysis school: "
                        f"{module_name}"
                    )


            except Exception as error:

                logger.exception(
                    f"Failed loading analysis "
                    f"school {module_name}: {error}"
                )


        return modules


    # =====================================
    # SHOW ANALYSIS MENU
    # =====================================

    async def show_analysis_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        message = update.effective_message


        await message.reply_text(

            "📊 مدارس التحليل\n\n"
            "اختر مدرسة التحليل:",

            reply_markup=analysis_keyboard()

        )


    # =====================================
    # HANDLE SCHOOL SELECTION
    # =====================================

    async def handle_analysis_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        query = update.callback_query


        if query is None:

            return ConversationHandler.END


        await query.answer()


        data = query.data


        # =================================
        # CANCEL
        # =================================

        if data == "analysis_cancel":

            context.user_data.clear()


            await query.edit_message_text(

                "❌ تم إلغاء التحليل.",

                reply_markup=main_menu_keyboard()

            )


            return ConversationHandler.END


        # =================================
        # BACK TO MAIN
        # =================================

        if data == "back_main":

            context.user_data.clear()


            await query.edit_message_text(

                "🏠 القائمة الرئيسية",

                reply_markup=main_menu_keyboard()

            )


            return ConversationHandler.END


        # =================================
        # ANALYSIS SCHOOL
        # =================================

        if not data.startswith(
            "analysis_"
        ):

            return ConversationHandler.END


        school_name = data.replace(
            "analysis_",
            ""
        )


        if school_name not in (
            self.analysis_modules
        ):

            await query.edit_message_text(

                "❌ مدرسة التحليل غير متوفرة."

            )


            return ConversationHandler.END


        module = self.analysis_modules[
            school_name
        ]


        # اسم المدرسة من الملف نفسه
        school_title = getattr(

            module,

            "SCHOOL_NAME",

            school_name.title()

        )


        context.user_data[
            "analysis_school"
        ] = school_name


        await query.edit_message_text(

            f"📊 {school_title}\n\n"

            "🪙 أرسل رمز العملة للتحليل\n\n"

            "مثال:\n"
            "BTC"

        )


        return WAITING_SYMBOL


    # =====================================
    # RECEIVE SYMBOL
    # =====================================

    async def receive_symbol(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):


        if update.message is None:

            return WAITING_SYMBOL


        if not update.message.text:

            return WAITING_SYMBOL


        school_name = context.user_data.get(

            "analysis_school"

        )


        if not school_name:

            await update.message.reply_text(

                "❌ لم يتم اختيار مدرسة التحليل.",

                reply_markup=main_menu_keyboard()

            )


            return ConversationHandler.END


        # =================================
        # GET MODULE
        # =================================

        module = self.analysis_modules.get(

            school_name

        )


        if module is None:

            await update.message.reply_text(

                "❌ مدرسة التحليل غير موجودة."

            )


            return ConversationHandler.END


        # =================================
        # CLEAN SYMBOL
        # =================================

        symbol = (
            update.message.text
            .strip()
            .upper()
        )


        symbol = (
            symbol
            .replace(
                "USDT",
                ""
            )
            .replace(
                "/",
                ""
            )
            .replace(
                " ",
                ""
            )
        )


        if not symbol:

            await update.message.reply_text(

                "❌ أرسل رمز عملة صحيحاً."

            )


            return WAITING_SYMBOL


        # =================================
        # LOADING
        # =================================

        await update.message.reply_text(

            f"⏳ جاري تحليل {symbol}..."

        )


        try:


            # =============================
            # GET DATA
            # =============================

            candles = []


            requires_candles = getattr(

                module,

                "REQUIRES_CANDLES",

                True

            )


            if requires_candles:


                candles = (
                    await self.crypto_api.get_klines(

                        symbol,

                        interval="4h",

                        limit=100

                    )
                )


                if not candles:

                    await update.message.reply_text(

                        f"❌ لا توجد بيانات للعملة "
                        f"{symbol}."

                    )


                    return ConversationHandler.END


                # =========================
                # RUN ANALYSIS
                # =========================

                result = module.analyze(

                    candles

                )


            else:


                # =========================
                # NON CANDLE ANALYSIS
                # Example: TVL
                # =========================

                if school_name == "tvl":

                    analysis_data = (
                        await self.crypto_api.get_tvl(

                            symbol

                        )
                    )


                else:

                    analysis_data = None


                result = module.analyze(

                    analysis_data

                )


            # =============================
            # VALIDATE RESULT
            # =============================

            if not result:

                await update.message.reply_text(

                    "❌ فشل إنشاء التحليل."

                )


                return ConversationHandler.END


            # =============================
            # BUILD MESSAGE
            # =============================

            message = (

                "📊 Doshka Trading Pro\n\n"

                f"🪙 العملة: {symbol}\n"

                f"🏫 المدرسة: "
                f"{result.get('school', school_name)}\n\n"

                f"🎯 الإشارة: "
                f"{result.get('signal', 'WAIT')}\n\n"

                f"{result.get('message', '')}"

            )


            # =============================
            # OPTIONAL RESULT DATA
            # =============================

            if result.get("rsi") is not None:

                message += (

                    f"\n\n📊 RSI: "

                    f"{result['rsi']}"

                )


            if result.get("support") is not None:

                message += (

                    f"\n📉 الدعم: "

                    f"{result['support']}"

                )


            if result.get("resistance") is not None:

                message += (

                    f"\n📈 المقاومة: "

                    f"{result['resistance']}"

                )


            if result.get(
                "volume_ratio"
            ) is not None:

                message += (

                    f"\n🐋 قوة الحجم: "

                    f"{result['volume_ratio']}x"

                )


            if result.get("pattern"):

                message += (

                    f"\n🦋 النموذج: "

                    f"{result['pattern']}"

                )


            # =============================
            # CREATE CHART
            # =============================

            chart_path = None


            try:


                chart_path = (
                    self.chart_service.create_chart(

                        symbol=symbol,

                        candles=candles,

                        school=school_name,

                        analysis_result=result

                    )
                )


            except Exception as error:


                logger.exception(

                    f"Chart error: {error}"

                )


            # =============================
            # SEND CHART
            # =============================

            if (

                chart_path

                and

                os.path.exists(
                    chart_path
                )

            ):


                with open(

                    chart_path,

                    "rb"

                ) as chart:


                    await update.message.reply_photo(

                        photo=chart,

                        caption=message

                    )


            else:


                await update.message.reply_text(

                    message

                )


            # =============================
            # CLEAN USER DATA
            # =============================

            context.user_data.pop(

                "analysis_school",

                None

            )


            return ConversationHandler.END


        except Exception as error:


            logger.exception(

                "Analysis error: %s",

                error

            )


            await update.message.reply_text(

                "❌ حدث خطأ أثناء تنفيذ التحليل."

            )


            context.user_data.pop(

                "analysis_school",

                None

            )


            return ConversationHandler.END

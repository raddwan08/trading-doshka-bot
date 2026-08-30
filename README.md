# Doshka Trading Pro — Railway + GitHub

نسخة معاد بناؤها من المشروع الحالي، مع فصل التحليل والدفع وقاعدة البيانات.

## أهم الإصلاحات

- جميع أزرار Telegram لها callback handlers واضحة.
- كل مدرسة تستخدم خوارزمية مختلفة فعليًا.
- BTC/ETH/SOL/... تدخل إلى نفس محرك السوق لكن نتائج المدرسة تعتمد على منطق المدرسة، وليست نتيجة ثابتة.
- USDT على Ethereum / BNB Smart Chain / Solana.
- منع استخدام TX مرتين.
- الطلب له مدة صلاحية.
- التحقق من وقت المعاملة حتى لا تُحتسب دفعة قديمة.
- EVM: فحص Transfer logs مع confirmations.
- Solana: البحث عن token accounts الخاصة بالمحفظة ثم فحص التحويلات.
- الأسرار لا توضع داخل GitHub.
- SQLite يعمل مع Railway Volume عبر `/data`.
- Dockerfile وrailway.toml جاهزان.

## Railway Variables

انسخ محتوى `.env.example` إلى Railway Raw Editor ثم ضع القيم الحقيقية:

BOT_TOKEN
ADMIN_ID
SQLITE_PATH=/data/subscriptions.db
SOL_WALLET
ETH_WALLET
BSC_WALLET
SOLANA_RPC_URL
ETH_RPC_URL
BSC_RPC_URL

ويمكن إبقاء عناوين USDT الافتراضية كما هي.

## Railway Volume

أنشئ Volume واربطه بالخدمة على `/data`.
هذا مهم حتى لا تضيع قاعدة SQLite عند إعادة نشر الحاوية.

## GitHub

ارفع الملفات إلى root المستودع الحالي `raddwan08/trading-doshka-bot` على branch `main`.

Railway يستطيع استخدام Dockerfile الموجود في root تلقائيًا.

## ملاحظة

لا يوجد كود يستطيع ضمان "خلو الأخطاء 100%" أو ضمان أرباح التداول. هذه النسخة مصممة لتكون قابلة للتشغيل والإدارة، لكن يجب اختبار كل شبكة دفع بمبلغ صغير قبل الإنتاج.

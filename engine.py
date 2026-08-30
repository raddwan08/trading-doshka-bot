
from __future__ import annotations

from math import isfinite
from statistics import mean, median
from typing import Callable


def closes(k): return [x["close"] for x in k]
def highs(k): return [x["high"] for x in k]
def lows(k): return [x["low"] for x in k]
def vols(k): return [x["volume"] for x in k]


def ema(values, period):
    if not values:
        return []
    alpha = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1 - alpha) * out[-1])
    return out


def rsi(values, period=14):
    if len(values) <= period:
        return [50.0] * len(values)
    gains, losses = [], []
    for a, b in zip(values[:-1], values[1:]):
        change = b - a
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result = [50.0] * period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss else 999.0
        result.append(100 - 100 / (1 + rs))
    result.append(result[-1] if result else 50.0)
    return result[-len(values):]


def macd(values):
    e12, e26 = ema(values, 12), ema(values, 26)
    line = [a - b for a, b in zip(e12, e26)]
    signal = ema(line, 9)
    return line, signal


def atr(k, period=14):
    if len(k) < 2:
        return 0.0
    tr = []
    for i in range(1, len(k)):
        tr.append(max(
            k[i]["high"] - k[i]["low"],
            abs(k[i]["high"] - k[i-1]["close"]),
            abs(k[i]["low"] - k[i-1]["close"]),
        ))
    return mean(tr[-period:]) if tr else 0.0


def pivots(k, left=3, right=3):
    ph, pl = [], []
    for i in range(left, len(k) - right):
        hi, lo = k[i]["high"], k[i]["low"]
        if hi == max(x["high"] for x in k[i-left:i+right+1]):
            ph.append((i, hi))
        if lo == min(x["low"] for x in k[i-left:i+right+1]):
            pl.append((i, lo))
    return ph, pl


def levels(k):
    ph, pl = pivots(k)
    resistance = [v for _, v in ph[-4:]]
    support = [v for _, v in pl[-4:]]
    if not support:
        support = [min(lows(k)[-50:])]
    if not resistance:
        resistance = [max(highs(k)[-50:])]
    return support, resistance


def direction(score):
    if score >= 2:
        return "شراء"
    if score <= -2:
        return "بيع"
    return "محايد"


def build_signal(k, school, symbol, score, rationale, confidence=None):
    price = k[-1]["close"]
    a = atr(k)
    support, resistance = levels(k)
    if score > 0:
        entry = [price, min(price * 0.998, price)]
        stop = max(min(support[-1], price - a * 1.3), price * 0.90)
        target = max(resistance[-1], price + a * 2.2)
    elif score < 0:
        entry = [price, max(price * 1.002, price)]
        stop = min(max(resistance[-1], price + a * 1.3), price * 1.10)
        target = min(support[-1], price - a * 2.2)
    else:
        entry = [price]
        stop = max(price - a * 1.5, price * 0.95)
        target = min(price + a * 1.5, price * 1.05)

    conf = confidence if confidence is not None else min(95, max(45, 55 + abs(score) * 6))
    return {
        "school": school,
        "symbol": symbol.upper(),
        "direction": direction(score),
        "score": score,
        "confidence": round(conf, 1),
        "entry": [round(x, 8) for x in entry],
        "stop_loss": round(float(stop), 8),
        "take_profit": round(float(target), 8),
        "sr": {
            "supports": [round(float(x), 8) for x in support],
            "resistances": [round(float(x), 8) for x in resistance],
        },
        "analysis": (
            f"🏫 <b>{school}</b>\n"
            f"🪙 <b>{symbol.upper()}/USDT</b>\n"
            f"📌 الاتجاه: <b>{direction(score)}</b>\n"
            f"🎯 الثقة: <b>{conf:.0f}%</b>\n"
            f"💵 الدخول: <b>{', '.join(f'{x:.6g}' for x in entry)}</b>\n"
            f"🛑 وقف الخسارة: <b>{stop:.6g}</b>\n"
            f"🎯 الهدف: <b>{target:.6g}</b>\n\n"
            f"{rationale}\n\n"
            "⚠️ التحليل آلي وتعليمي، وليس ضمانًا للربح."
        ),
    }


def classic(k, symbol):
    c = closes(k)
    e20, e50 = ema(c, 20), ema(c, 50)
    rr = rsi(c)[-1]
    ml, ms = macd(c)
    score = 0
    reasons = []
    if c[-1] > e20[-1] > e50[-1]:
        score += 2; reasons.append("السعر فوق EMA20 وEMA50 مع ترتيب صاعد.")
    elif c[-1] < e20[-1] < e50[-1]:
        score -= 2; reasons.append("السعر تحت EMA20 وEMA50 مع ترتيب هابط.")
    else:
        reasons.append("المتوسطات متداخلة، ما يعني أن الاتجاه أقل وضوحًا.")
    if rr < 30:
        score += 1; reasons.append(f"RSI={rr:.1f}: تشبع بيعي نسبي.")
    elif rr > 70:
        score -= 1; reasons.append(f"RSI={rr:.1f}: تشبع شرائي نسبي.")
    else:
        reasons.append(f"RSI={rr:.1f}: منطقة وسطية.")
    if ml[-1] > ms[-1]:
        score += 1; reasons.append("MACD أعلى من خط الإشارة.")
    else:
        score -= 1; reasons.append("MACD أدنى من خط الإشارة.")
    return build_signal(k, "التحليل الكلاسيكي", symbol, score, "\n".join("• " + x for x in reasons))


def wyckoff(k, symbol):
    c, v = closes(k), vols(k)
    recent = k[-20:]
    price_change = (c[-1] - c[-20]) / c[-20]
    avgv = mean(v[-30:])
    lastv = mean(v[-3:])
    score = 0
    reasons = []
    if price_change > 0.015 and lastv > avgv * 1.25:
        score += 2; reasons.append("ارتفاع سعري مدعوم بزيادة واضحة في الحجم؛ سلوك أقرب للتراكم/الطلب.")
    elif price_change < -0.015 and lastv > avgv * 1.25:
        score -= 2; reasons.append("هبوط مع حجم مرتفع؛ ضغط عرض/تصريف محتمل.")
    else:
        reasons.append("الحجم لا يعطي تأكيدًا قويًا على تراكم أو تصريف.")
    spread = recent[-1]["high"] - recent[-1]["low"]
    body = abs(recent[-1]["close"] - recent[-1]["open"])
    if spread and body / spread < 0.25 and recent[-1]["volume"] > avgv * 1.4:
        score += 1 if recent[-1]["close"] >= recent[-1]["open"] else -1
        reasons.append("شمعة ذات انتشار كبير وحجم مرتفع مع جسم صغير؛ قد تعكس امتصاصًا/صراعًا.")
    return build_signal(k, "وايكوف", symbol, score, "\n".join("• " + x for x in reasons))


def elliott(k, symbol):
    ph, pl = pivots(k, 4, 4)
    swings = [(i, v, "H") for i, v in ph[-5:]] + [(i, v, "L") for i, v in pl[-5:]]
    swings.sort()
    score = 0
    reasons = []
    if len(ph) >= 3 and ph[-1][1] > ph[-2][1] > ph[-3][1]:
        score += 2; reasons.append("تتابع قمم أعلى يدعم بنية موجية صاعدة.")
    elif len(ph) >= 3 and ph[-1][1] < ph[-2][1] < ph[-3][1]:
        score -= 2; reasons.append("تتابع قمم أدنى يدعم بنية موجية هابطة.")
    if len(pl) >= 3 and pl[-1][1] > pl[-2][1] > pl[-3][1]:
        score += 1; reasons.append("القيعان أعلى من السابقة.")
    elif len(pl) >= 3 and pl[-1][1] < pl[-2][1] < pl[-3][1]:
        score -= 1; reasons.append("القيعان أدنى من السابقة.")
    if swings:
        reasons.append("تم استخراج نقاط انعطاف محلية بدل إعطاء نفس التحليل لكل مدرسة.")
    else:
        reasons.append("عدد نقاط الانعطاف غير كافٍ لبنية موجية موثوقة.")
    return build_signal(k, "إليوت", symbol, score, "\n".join("• " + x for x in reasons))


def harmonic(k, symbol):
    ph, pl = pivots(k, 3, 3)
    pts = sorted([(i, v, "H") for i, v in ph] + [(i, v, "L") for i, v in pl])[-5:]
    score = 0
    reasons = []
    if len(pts) >= 5:
        vals = [p[1] for p in pts]
        x, a, b, c, d = vals
        xa = abs(a-x) or 1e-12
        ab = abs(b-a)
        bc = abs(c-b)
        cd = abs(d-c)
        r_ab = ab / xa
        r_bc = bc / ab if ab else 0
        r_cd = cd / bc if bc else 0
        near = lambda x, target, tol=0.18: abs(x-target) <= tol
        if near(r_ab, 0.618) and near(r_bc, 0.618) and near(r_cd, 1.618):
            score = 2
            reasons.append(f"نسب XABCD قريبة من تركيب هارموني: AB/XA={r_ab:.2f}, BC/AB={r_bc:.2f}, CD/BC={r_cd:.2f}.")
        elif near(r_ab, 0.786) and near(r_bc, 0.382) and near(r_cd, 1.272):
            score = -2
            reasons.append(f"نسب انعكاس هارموني محتملة: {r_ab:.2f}/{r_bc:.2f}/{r_cd:.2f}.")
        else:
            score = 1 if k[-1]["close"] > k[-20]["close"] else -1
            reasons.append(f"لم يكتمل نموذج XABCD واضح؛ النسب الحالية {r_ab:.2f}/{r_bc:.2f}/{r_cd:.2f}.")
    else:
        reasons.append("لا توجد خمس نقاط انعطاف كافية لاختبار XABCD.")
    return build_signal(k, "هارمونيك", symbol, score, "\n".join("• " + x for x in reasons))


def whales(k, symbol):
    v = vols(k)
    avg = mean(v[-30:])
    spikes = [i for i, x in enumerate(v[-30:]) if x > avg * 2]
    score = 0
    reasons = [f"تم رصد {len(spikes)} شمعة بحجم يتجاوز ضعفي المتوسط في آخر 30 شمعة."]
    if spikes:
        last = k[-30:][spikes[-1]]
        body = last["close"] - last["open"]
        score = 2 if body > 0 else -2
        reasons.append("آخر شذوذ حجمي يميل إلى الشراء." if body > 0 else "آخر شذوذ حجمي يميل إلى البيع.")
    else:
        score = 1 if k[-1]["close"] > k[-10]["close"] else -1
        reasons.append("لا يوجد نشاط حجمي استثنائي قوي؛ الاتجاه السعري يستخدم كإشارة ثانوية.")
    return build_signal(k, "الحيتان", symbol, score, "\n".join("• " + x for x in reasons))


def liquidity(k, symbol):
    # This is market-liquidity analysis based on volume/range, NOT on-chain TVL.
    ranges = [(x["high"] - x["low"]) / x["close"] for x in k[-30:] if x["close"]]
    v = vols(k)
    avg_range = median(ranges) if ranges else 0
    avg_vol = mean(v[-30:])
    current_range = (k[-1]["high"] - k[-1]["low"]) / k[-1]["close"]
    score = 0
    reasons = []
    if avg_range and current_range > avg_range * 1.5 and v[-1] > avg_vol * 1.5:
        score = 1 if k[-1]["close"] >= k[-1]["open"] else -1
        reasons.append("اتساع النطاق مع حجم مرتفع؛ السيولة النشطة/التقلب مرتفعان.")
    else:
        score = 1 if k[-1]["close"] > k[-10]["close"] else -1
        reasons.append("لا توجد قفزة سيولة استثنائية؛ تم الاعتماد على اتجاه الحركة والحجم.")
    reasons.append(f"نطاق الشمعة الحالية={current_range*100:.2f}% مقابل وسيط {avg_range*100:.2f}%.")
    return build_signal(k, "السيولة", symbol, score, "\n".join("• " + x for x in reasons))


FUNCS: dict[str, Callable] = {
    "wyckoff": wyckoff,
    "elliott": elliott,
    "harmonic": harmonic,
    "classic": classic,
    "whales": whales,
    "liquidity": liquidity,
}

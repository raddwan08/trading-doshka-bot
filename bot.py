import asyncio, io, logging, os, sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

BOT_TOKEN=os.getenv("BOT_TOKEN","")
ADMIN_ID=int(os.getenv("ADMIN_ID","0"))
SQLITE_PATH=os.getenv("SQLITE_PATH","data/subscriptions.db")
SOL_WALLET=os.getenv("SOL_WALLET","5JSJzkF9GU6GA28J57xxBvSngoaHtbLGGwQkKHGUu1Dt")
ETH_WALLET=os.getenv("ETH_WALLET","0xF79A1bEc46037dcA06077889F4bb1A111B67723e").lower()
BSC_WALLET=os.getenv("BSC_WALLET","0xF79A1bEc46037dcA06077889F4bb1A111B67723e").lower()
SOLANA_RPC_URL=os.getenv("SOLANA_RPC_URL","https://api.mainnet-beta.solana.com")
ETH_RPC_URL=os.getenv("ETH_RPC_URL","")
BSC_RPC_URL=os.getenv("BSC_RPC_URL","")
ETH_USDT_CONTRACT=os.getenv("ETH_USDT_CONTRACT","0xdAC17F958D2ee523a2206206994597C13D831ec7").lower()
BSC_USDT_CONTRACT=os.getenv("BSC_USDT_CONTRACT","0x55d398326f99059fF775485246999027B3197955").lower()
SOL_USDT_MINT=os.getenv("SOL_USDT_MINT","Es9vMFrzaCERmJfrF4H2FYD4zKQjX4q2Hqg2m4jQm7f")
PAYMENT_SCAN_SECONDS=int(os.getenv("PAYMENT_SCAN_SECONDS","20"))
MIN_CONFIRMATIONS=int(os.getenv("MIN_CONFIRMATIONS","3"))
if not BOT_TOKEN: raise SystemExit("BOT_TOKEN is required")
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s")
log=logging.getLogger("doshka")

PLANS={"1m":{"days":30,"price":20,"name":"شهر","emoji":"📅"},"3m":{"days":90,"price":50,"name":"3 أشهر","emoji":"💎"},"6m":{"days":180,"price":75,"name":"6 أشهر","emoji":"👑"},"1y":{"days":365,"price":125,"name":"سنة","emoji":"🏆"}}
NETWORKS={"sol":{"name":"Solana","wallet":SOL_WALLET},"eth":{"name":"Ethereum","wallet":ETH_WALLET},"bnb":{"name":"BSC","wallet":BSC_WALLET}}
COINS=["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX"]
SCHOOLS={
 "wyckoff":{"name":"وايكوف","emoji":"📊","timeframes":["1h","4h","1d"]},
 "elliott":{"name":"إليوت","emoji":"🌊","timeframes":["1h","4h","1d"]},
 "harmonic":{"name":"هارمونيك","emoji":"🦋","timeframes":["1h","4h","1d"]},
 "classic":{"name":"كلاسيكي","emoji":"📈","timeframes":["15m","1h","4h","1d"]},
 "whales":{"name":"الحيتان","emoji":"🐋","timeframes":["1h","4h","1d"]},
 "tvl":{"name":"السيولة","emoji":"🔒","timeframes":["1d"]}
}
class States(StatesGroup):
    custom=State()

bot=Bot(token=BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher(storage=MemoryStorage())

class DB:
    def __init__(self,p): self.p=p; self.lock=asyncio.Lock()
    def conn(self):
        return sqlite3.connect(self.p,timeout=30)
    async def init(self):
        os.makedirs(os.path.dirname(self.p) or ".",exist_ok=True)
        async with self.lock:
            c=self.conn(); c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,username TEXT,plan TEXT,start_date TEXT,expire_date TEXT,is_active INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,plan TEXT,network TEXT,created_at TEXT,status TEXT DEFAULT 'pending');
            CREATE TABLE IF NOT EXISTS used_transactions(tx_id TEXT PRIMARY KEY,user_id INTEGER,plan TEXT,network TEXT,amount REAL,created_at TEXT);
            """)
            if ADMIN_ID: c.execute("INSERT OR IGNORE INTO users(user_id,is_active) VALUES(?,1)",(ADMIN_ID,))
            c.commit(); c.close()
    async def active(self,u):
        if u==ADMIN_ID:return True
        async with self.lock:
            c=self.conn(); r=c.execute("SELECT expire_date,is_active FROM users WHERE user_id=?",(u,)).fetchone(); c.close()
        if not r or not r[1] or not r[0]: return False
        try:return datetime.fromisoformat(r[0])>datetime.now(timezone.utc)
        except:return False
    async def status(self,u):
        async with self.lock:
            c=self.conn(); r=c.execute("SELECT plan,expire_date,is_active FROM users WHERE user_id=?",(u,)).fetchone(); c.close()
        return r
    async def order(self,u,p,n):
        async with self.lock:
            c=self.conn(); c.execute("UPDATE orders SET status='cancelled' WHERE user_id=? AND status='pending'",(u,))
            c.execute("INSERT INTO orders(user_id,plan,network,created_at) VALUES(?,?,?,?)",(u,p,n,datetime.now(timezone.utc).isoformat()))
            c.commit(); c.close()
    async def pending(self,u):
        async with self.lock:
            c=self.conn(); r=c.execute("SELECT id,user_id,plan,network FROM orders WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",(u,)).fetchone(); c.close()
        return r
    async def claim(self,tx,u,p,n,a):
        async with self.lock:
            c=self.conn()
            try:
                c.execute("BEGIN IMMEDIATE")
                if c.execute("SELECT 1 FROM used_transactions WHERE tx_id=?",(tx,)).fetchone(): c.rollback(); return False
                c.execute("INSERT INTO used_transactions VALUES(?,?,?,?,?,?)",(tx,u,p,n,a,datetime.now(timezone.utc).isoformat()))
                c.execute("UPDATE orders SET status='paid' WHERE user_id=? AND status='pending'",(u,))
                c.commit(); return True
            finally:c.close()
    async def activate(self,u,p):
        now=datetime.now(timezone.utc); base=now
        async with self.lock:
            c=self.conn(); old=c.execute("SELECT expire_date,is_active FROM users WHERE user_id=?",(u,)).fetchone()
            if old and old[1] and old[0]:
                try:
                    d=datetime.fromisoformat(old[0]); base=max(base,d)
                except:pass
            exp=base+timedelta(days=PLANS[p]["days"])
            c.execute("""INSERT INTO users(user_id,plan,start_date,expire_date,is_active) VALUES(?,?,?,?,1)
            ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan,start_date=excluded.start_date,expire_date=excluded.expire_date,is_active=1""",(u,p,now.isoformat(),exp.isoformat()))
            c.commit(); c.close()
        return exp

db=DB(SQLITE_PATH)

async def rpc(url,method,params):
    if not url:return None
    try:
        t=aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=t) as s:
            async with s.post(url,json={"jsonrpc":"2.0","id":1,"method":method,"params":params}) as r:
                if r.status!=200:return None
                return await r.json()
    except Exception as e:log.warning("RPC: %s",e);return None

async def klines(sym,tf,limit=150):
    sym=sym.upper().replace("USDT","")
    if not sym.isalnum():return []
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as s:
            async with s.get("https://api.binance.com/api/v3/klines",params={"symbol":sym+"USDT","interval":tf,"limit":limit}) as r:
                if r.status!=200:return []
                d=await r.json()
        return [{"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4]),"volume":float(x[5]),"time":datetime.fromtimestamp(x[0]/1000)} for x in d]
    except Exception as e:log.warning("Binance: %s",e);return []

def ema(x,p):
    if not x:return []
    a=2/(p+1);o=[x[0]]
    for v in x[1:]:o.append(a*v+(1-a)*o[-1])
    return o
def sma(x,p):return float(np.mean(x[-p:])) if x else 0
def rsi(x,p=14):
    if len(x)<=p:return 50
    g=[max(b-a,0) for a,b in zip(x[:-1],x[1:])];l=[max(a-b,0) for a,b in zip(x[:-1],x[1:])]
    ag=sum(g[-p:])/p;al=sum(l[-p:])/p
    return 100 if al==0 else 100-100/(1+ag/al)
def atr(k,p=14):
    if len(k)<p+1:return 0
    pc=k[0]["close"];t=[]
    for x in k[1:]:
        t.append(max(x["high"]-x["low"],abs(x["high"]-pc),abs(x["low"]-pc)));pc=x["close"]
    return float(np.mean(t[-p:]))
def sr(k):
    hi=[x["high"] for x in k];lo=[x["low"] for x in k];cur=k[-1]["close"];lv=[]
    for i in range(2,len(k)-2):
        if hi[i]>hi[i-1] and hi[i]>hi[i+1]:lv.append(hi[i])
        if lo[i]<lo[i-1] and lo[i]<lo[i+1]:lv.append(lo[i])
    return {"supports":sorted({x for x in lv if x<cur},reverse=True)[:3],"resistances":sorted({x for x in lv if x>cur})[:3]}
def levels(k,act):
    cur=k[-1]["close"];a=atr(k) or cur*.02
    if act=="BUY":return [cur],cur-a*1.8,[cur+a*2.5,cur+a*4]
    if act=="SELL":return [cur],cur+a*1.8,[cur-a*2.5,cur-a*4]
    return [cur],cur-a,[cur+a*2]

def pack(sym,school,act,conf,details,k):
    e,sl,tp=levels(k,act);z=sr(k)
    txt=f"{SCHOOLS[school]['emoji']} <b>{SCHOOLS[school]['name']} — {sym}/USDT</b>\n\n{details}\n\nالتوصية: <b>{'🟢 شراء' if act=='BUY' else '🔴 بيع' if act=='SELL' else '⏳ انتظار'}</b>\nالثقة: <b>{conf}%</b>\n\n💡 الدخول: "+", ".join(f"${x:.8g}" for x in e)+f"\n🛑 الوقف: ${sl:.8g}\n🎯 الأهداف: "+", ".join(f"${x:.8g}" for x in tp)+"\n\n⚠️ التحليل آلي وليس ضمانًا للربح."
    return {"analysis":txt,"action":act,"entry":e,"stop_loss":sl,"take_profit":tp,"sr":z}

# Each school is an independent algorithm. Coin profile changes risk/thresholds.
RISK={"BTC":1,"ETH":1.05,"SOL":1.35,"BNB":.95,"XRP":1.25,"ADA":1.3,"DOGE":1.55,"AVAX":1.35}
def adj(sym,c):return max(50,min(95,round(c-(RISK.get(sym,1)-1)*8)))

def wyckoff(k,s):
    c=[x["close"] for x in k];v=[x["volume"] for x in k];vr=v[-1]/sma(v,20);chg=(c[-1]/sma(c,20)-1)*100
    act="BUY" if vr>1.6 and chg< -2 else "SELL" if vr>1.6 and chg>2 else "WAIT"
    return pack(s,"wyckoff",act,adj(s,82 if act!="WAIT" else 55),f"حجم/متوسط 20: {vr:.2f}x\nتغير السعر عن SMA20: {chg:.2f}%\nقراءة: {'امتصاص/تجميع' if act=='BUY' else 'توزيع' if act=='SELL' else 'لا توجد إشارة وايكوف واضحة'}",k)
def elliott(k,s):
    h=[x["high"] for x in k];l=[x["low"] for x in k];p=[]
    for i in range(2,len(k)-2):
        if h[i]>max(h[i-2:i]) and h[i]>=max(h[i+1:i+3]):p.append(("H",h[i]))
        elif l[i]<min(l[i-2:i]) and l[i]<=min(l[i+1:i+3]):p.append(("L",l[i]))
    last=p[-5:];bull=sum(last[i][1]>last[i-1][1] for i in range(1,len(last)));bear=sum(last[i][1]<last[i-1][1] for i in range(1,len(last)))
    act="BUY" if last and last[-1][0]=="L" and bull>=2 else "SELL" if last and last[-1][0]=="H" and bear>=2 else "WAIT"
    return pack(s,"elliott",act,adj(s,74 if act!="WAIT" else 55),f"نقاط محورية: {len(p)}\nقراءة الموجة: {'تصحيح قد ينتهي لصالح موجة دافعة' if act=='BUY' else 'موجة دافعة قد تنتهي ويبدأ تصحيح' if act=='SELL' else 'العد الموجي غير حاسم'}",k)
def harmonic(k,s):
    h=[x["high"] for x in k];l=[x["low"] for x in k];p=[]
    for i in range(2,len(k)-2):
        if h[i]>h[i-1] and h[i]>h[i+1]:p.append(h[i])
        elif l[i]<l[i-1] and l[i]<l[i+1]:p.append(l[i])
    act="WAIT";ratio="غير متاح"
    if len(p)>=5:
        X,A,B,C,D=p[-5:];xa=abs(A-X) or 1e-9;ab=abs(B-A);bc=abs(C-B);cd=abs(D-C)
        ratio=f"AB/XA={ab/xa:.2f}, BC/AB={bc/(ab or 1e-9):.2f}, CD/BC={cd/(bc or 1e-9):.2f}"
        if abs(ab/xa-.618)<.10 and .3<bc/(ab or 1e-9)<.9:
            act="BUY" if D<C else "SELL"
    return pack(s,"harmonic",act,adj(s,78 if act!="WAIT" else 55),f"النقاط: {len(p)}\nالنسب: {ratio}\nالنمط: {'تجمع نسب هارمونيك' if act!='WAIT' else 'لا يوجد تجمع كافٍ'}",k)
def classic(k,s):
    c=[x["close"] for x in k];e20=ema(c,20)[-1];e50=ema(c,50)[-1];rv=rsi(c);m=ema(c,12)[-1]-ema(c,26)[-1];sig=ema([a-b for a,b in zip(ema(c,12),ema(c,26))],9)[-1];hist=m-sig
    score=(2 if c[-1]>e20>e50 else -2 if c[-1]<e20<e50 else 0)+(2 if rv<35 else -2 if rv>65 else 0)+(1 if hist>0 else -1)
    act="BUY" if score>=3 else "SELL" if score<=-3 else "WAIT"
    return pack(s,"classic",act,adj(s,60+min(abs(score)*7,28)),f"EMA20/50: {e20:.6g}/{e50:.6g}\nRSI: {rv:.1f}\nMACD histogram: {hist:.6g}\nConfluence: {score}",k)
def whales(k,s):
    v=[x["volume"] for x in k];an=[i for i in range(len(k)-10,len(k)) if v[i]>sma(v[:-10],30)*2];flow=sum(1 if k[i]["close"]>k[i]["open"] else -1 for i in an)
    act="BUY" if len(an)>=2 and flow>0 else "SELL" if len(an)>=2 and flow<0 else "WAIT"
    return pack(s,"whales",act,adj(s,76 if act!="WAIT" else 55),f"انحرافات حجمية قوية: {len(an)}\nاتجاه الشموع عالية الحجم: {flow}\nملاحظة: الحجم لا يحدد هوية حوت بعينه.",k)
def tvl(k,s):
    v=[x["volume"] for x in k];c=[x["close"] for x in k];ratio=sma(v,7)/sma(v,30);trend=(c[-1]/sma(c,20)-1)*100
    act="BUY" if ratio>1.25 and trend>1 else "SELL" if ratio<.75 and trend<0 else "WAIT"
    return pack(s,"tvl",act,adj(s,70 if act!="WAIT" else 55),f"نسبة حجم 7/30 كمؤشر مشاركة: {ratio:.2f}x\nتغير السعر عن SMA20: {trend:.2f}%\nهذا مؤشر سوقي وليس TVL on-chain حقيقي.",k)
FUNCS={"wyckoff":wyckoff,"elliott":elliott,"harmonic":harmonic,"classic":classic,"whales":whales,"tvl":tvl}

def chart(k,sig,sym,school):
    fig,ax=plt.subplots(figsize=(12,7))
    d=[x["time"] for x in k]
    for i,x in enumerate(k):
        col="#26a69a" if x["close"]>=x["open"] else "#ef5350"
        ax.plot([d[i],d[i]],[x["low"],x["high"]],color=col,lw=1)
        ax.plot([d[i],d[i]],[x["open"],x["close"]],color=col,lw=4)
    for x in sig["sr"]["supports"]+sig["sr"]["resistances"]+sig["entry"]+[sig["stop_loss"]]+sig["take_profit"]:ax.axhline(x,alpha=.35)
    ax.set_title(f"{sym}/USDT — {school}");ax.grid(alpha=.2);ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    plt.setp(ax.get_xticklabels(),rotation=45,ha="right");plt.tight_layout();b=io.BytesIO();fig.savefig(b,format="png",dpi=130);plt.close(fig);b.seek(0);return b

async def evm_scan(rpc,wallet,contract):
    latest=await rpc_call(rpc,"eth_blockNumber",[])
    if not latest:return []
    n=int(latest["result"],16); start=max(0,n-3000)
    topic="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a8df523b3ef"
    wt="0x"+wallet[2:].rjust(64,"0")
    q=await rpc_call(rpc,"eth_getLogs",[{"fromBlock":hex(start),"toBlock":hex(n),"address":contract,"topics":[topic,None,wt]}])
    out=[]
    for x in (q or {}).get("result",[]):
        try:out.append((x["transactionHash"],int(x["data"],16)/1e6,int(x["blockNumber"],16),n))
        except:pass
    return out
async def rpc_call(url,m,p):
    return await rpc(url,m,p)
async def sol_scan():
    q=await rpc(SOLANA_RPC_URL,"getSignaturesForAddress",[SOL_WALLET,{"limit":100}]);out=[]
    for x in (q or {}).get("result",[]):
        if x.get("err") or not x.get("signature"):continue
        tx=await rpc(SOLANA_RPC_URL,"getTransaction",[x["signature"],{"encoding":"jsonParsed","maxSupportedTransactionVersion":0}])
        r=(tx or {}).get("result")
        if not r:continue
        meta=r.get("meta") or {}
        pre={(b.get("accountIndex"),b.get("mint")):int(b.get("uiTokenAmount",{}).get("amount",0)) for b in meta.get("preTokenBalances",[])}
        for b in meta.get("postTokenBalances",[]):
            if b.get("mint")!=SOL_USDT_MINT or (b.get("owner") or "").lower()!=SOL_WALLET.lower():continue
            post=int(b.get("uiTokenAmount",{}).get("amount",0));delta=post-pre.get((b.get("accountIndex"),b.get("mint")),0)
            if delta>0:out.append((x["signature"],delta/1e6,0,0))
    return out
async def payment(order):
    need=PLANS[order[2]]["price"];net=order[3]
    if net=="sol": cs=await sol_scan()
    else:cs=await evm_scan(ETH_RPC_URL if net=="eth" else BSC_RPC_URL,NETWORKS[net]["wallet"],ETH_USDT_CONTRACT if net=="eth" else BSC_USDT_CONTRACT)
    for tx,a,b,n in cs:
        if need*.999<=a<=need*1.001 and (net=="sol" or n-b+1>=MIN_CONFIRMATIONS):return tx,a
    return None

async def monitor():
    while True:
        try:
            async with db.lock:
                c=db.conn();rows=c.execute("SELECT id,user_id,plan,network FROM orders WHERE status='pending' LIMIT 50").fetchall();c.close()
            for o in rows:
                try:
                    found=await payment(o)
                    if found and await db.claim(found[0],o[1],o[2],o[3],found[1]):
                        exp=await db.activate(o[1],o[2])
                        await bot.send_message(o[1],f"🎉 <b>تم تأكيد دفعة USDT وتفعيل الاشتراك!</b>\n\n📦 {PLANS[o[2]]['name']}\n💵 {found[1]:.2f} USDT\n🌐 {NETWORKS[o[3]]['name']}\n📅 {exp.strftime('%Y-%m-%d %H:%M UTC')}",reply_markup=main_kb())
                except Exception:log.exception("payment order")
        except Exception:log.exception("monitor")
        await asyncio.sleep(PAYMENT_SCAN_SECONDS)

def main_kb():
    b=InlineKeyboardBuilder();b.row(InlineKeyboardButton(text="📊 التحليل الفني",callback_data="start_analysis"));b.row(InlineKeyboardButton(text="💎 الاشتراكات",callback_data="plans"));b.row(InlineKeyboardButton(text="ℹ️ مساعدة",callback_data="help"),InlineKeyboardButton(text="📋 حالتي",callback_data="status"));return b.as_markup()
def schools_kb():
    b=InlineKeyboardBuilder()
    for k,v in SCHOOLS.items():b.row(InlineKeyboardButton(text=f"{v['emoji']} {v['name']}",callback_data=f"school_{k}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="back_main"));return b.as_markup()
def tf_kb(s):
    b=InlineKeyboardBuilder()
    for tf in SCHOOLS[s]["timeframes"]:b.row(InlineKeyboardButton(text=f"⏰ {tf}",callback_data=f"tf_{s}_{tf}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="start_analysis"));return b.as_markup()
def coins_kb(s,tf):
    b=InlineKeyboardBuilder()
    for i in range(0,len(COINS),2):b.row(*[InlineKeyboardButton(text=f"💰 {x}",callback_data=f"an_{s}_{tf}_{x}") for x in COINS[i:i+2]])
    b.row(InlineKeyboardButton(text="🔍 عملة أخرى",callback_data=f"custom_{s}_{tf}"));b.row(InlineKeyboardButton(text="🔙",callback_data=f"school_{s}"));return b.as_markup()
def plans_kb():
    b=InlineKeyboardBuilder()
    for k,v in PLANS.items():b.row(InlineKeyboardButton(text=f"{v['emoji']} {v['name']} — ${v['price']} USDT",callback_data=f"sub_{k}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="back_main"));return b.as_markup()

@dp.message(Command("start"))
async def start(m:Message):await m.answer("🌟 <b>Doshka Trading Pro</b>\n\n📊 تحليل متعدد المدارس\n💵 اشتراك USDT تلقائي\n🔎 بدون إرسال TX Hash\n\nاختر:",reply_markup=main_kb())
@dp.callback_query(F.data=="back_main")
async def back(c:CallbackQuery):await c.message.edit_text("🌟 <b>Doshka Trading Pro</b>",reply_markup=main_kb());await c.answer()
@dp.callback_query(F.data=="start_analysis")
async def start_an(c):
    if not await db.active(c.from_user.id):await c.answer("❌ للمشتركين فقط",show_alert=True);return
    await c.message.edit_text("<b>📊 اختر المدرسة:</b>",reply_markup=schools_kb());await c.answer()
@dp.callback_query(F.data.startswith("school_"))
async def school(c):
    s=c.data[7:]
    if s not in SCHOOLS:return
    await c.message.edit_text(f"{SCHOOLS[s]['emoji']} <b>{SCHOOLS[s]['name']}</b>\nاختر الفترة:",reply_markup=tf_kb(s));await c.answer()
@dp.callback_query(F.data.startswith("tf_"))
async def tf(c):
    _,s,t=c.data.split("_",2);await c.message.edit_text("💰 <b>اختر العملة:</b>",reply_markup=coins_kb(s,t));await c.answer()
@dp.callback_query(F.data.startswith("custom_"))
async def custom(c,state:FSMContext):
    _,s,t=c.data.split("_",2);await state.update_data(s=s,t=t);await state.set_state(States.custom);await c.message.edit_text("🔍 أرسل رمز العملة مثل BTC");await c.answer()
@dp.message(StateFilter(States.custom))
async def custom_m(m:Message,state:FSMContext):
    d=await state.get_data();await state.clear();s=(m.text or "").upper().replace("USDT","").strip();await do_analysis(m,s,d["s"],d["t"])
@dp.callback_query(F.data.startswith("an_"))
async def analyze(c:CallbackQuery):
    _,s,t,x=c.data.split("_");await c.answer("⏳ جاري التحليل...");await do_analysis(c.message,x,s,t)
async def do_analysis(m,s,school,tf):
    if not await db.active(m.chat.id):await m.answer("❌ الاشتراك غير نشط.");return
    w=await m.answer("⏳ جاري جلب البيانات...")
    k=await klines(s,tf)
    if len(k)<60:await w.edit_text("❌ تعذر الحصول على بيانات كافية.");return
    sig=FUNCS[school](k,s);ch=chart(k[-100:],sig,s,SCHOOLS[school]["name"]);await w.delete()
    await m.answer_photo(BufferedInputFile(ch.read(),filename=f"{s}_{school}.png"),caption=sig["analysis"],reply_markup=main_kb())
@dp.callback_query(F.data=="plans")
async def plans(c:CallbackQuery):await c.message.edit_text("<b>💎 الاشتراكات — USDT فقط</b>\n\nاختر الباقة:",reply_markup=plans_kb());await c.answer()
@dp.callback_query(F.data.startswith("sub_"))
async def sub(c:CallbackQuery):
    p=c.data[4:];b=InlineKeyboardBuilder()
    for n in ("sol","eth","bnb"):b.row(InlineKeyboardButton(text=f"💵 USDT — {NETWORKS[n]['name']}",callback_data=f"net_{p}_{n}"))
    b.row(InlineKeyboardButton(text="🔙",callback_data="plans"));await c.message.edit_text(f"💳 <b>{PLANS[p]['name']}</b>\n💵 ${PLANS[p]['price']} USDT\n\nاختر الشبكة:",reply_markup=b.as_markup());await c.answer()
@dp.callback_query(F.data.startswith("net_"))
async def net(c:CallbackQuery):
    _,p,n=c.data.split("_");await db.order(c.from_user.id,p,n)
    await c.message.edit_text(f"💳 <b>الدفع</b>\n\n💵 ${PLANS[p]['price']} USDT\n🌐 {NETWORKS[n]['name']}\n\n📮 أرسل USDT إلى:\n<code>{NETWORKS[n]['wallet']}</code>\n\n🔎 لا ترسل TX Hash. البوت سيبحث عن الدفعة تلقائيًا.\n\nبعد التحويل اضغط «فحص الآن».",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 فحص الآن",callback_data="check")],[InlineKeyboardButton(text="🔙",callback_data="plans")]]));await c.answer()
@dp.callback_query(F.data=="check")
async def check(c:CallbackQuery):
    o=await db.pending(c.from_user.id)
    if not o:await c.answer("لا يوجد طلب دفع.",show_alert=True);return
    await c.answer("🔎 جاري الفحص...")
    f=await payment(o)
    if not f:await c.message.answer("❌ لم يتم العثور على دفعة USDT مكتملة بالمبلغ المطلوب حتى الآن.");return
    if not await db.claim(f[0],o[1],o[2],o[3],f[1]):await c.message.answer("⚠️ المعاملة مستخدمة مسبقًا.");return
    exp=await db.activate(o[1],o[2]);await c.message.answer(f"🎉 <b>تم التفعيل!</b>\n📦 {PLANS[o[2]]['name']}\n💵 {f[1]:.2f} USDT\n🌐 {NETWORKS[o[3]]['name']}\n📅 {exp.strftime('%Y-%m-%d %H:%M UTC')}",reply_markup=main_kb())
@dp.callback_query(F.data=="status")
async def status(c:CallbackQuery):
    r=await db.status(c.from_user.id);txt="❌ <b>لا يوجد اشتراك نشط.</b>" if not r or not r[2] else f"✅ <b>اشتراك نشط</b>\n\n📦 {PLANS.get(r[0],{}).get('name',r[0])}\n📅 {r[1]}"
    await c.message.edit_text(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙",callback_data="back_main")]]));await c.answer()
@dp.callback_query(F.data=="help")
async def help_(c:CallbackQuery):await c.message.edit_text("<b>📖 المدارس</b>\n\n📊 وايكوف — الحجم والسلوك السعري\n🌊 إليوت — المحاور وتسلسل الموجات\n🦋 هارمونيك — النسب\n📈 كلاسيكي — EMA/RSI/MACD\n🐋 الحيتان — شذوذ الحجم\n🔒 السيولة — مشاركة السوق\n\n💵 الدفع USDT على Solana/Ethereum/BSC.\n🔎 التحقق آلي بدون TX Hash.",reply_markup=main_kb());await c.answer()

async def main():
    await db.init();task=asyncio.create_task(monitor())
    try:
        await bot.delete_webhook(drop_pending_updates=True);await dp.start_polling(bot)
    finally:task.cancel();await bot.session.close()
if __name__=="__main__":asyncio.run(main())

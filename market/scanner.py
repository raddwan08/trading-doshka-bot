from market.signals import analyze_market



coins=[
"BTCUSDT",
"ETHUSDT",
"BNBUSDT",
"SOLUSDT",
"XRPUSDT"
]



def scan_market():


    results=[]


    for coin in coins:

        data=analyze_market(
            coin
        )

        results.append({

            "coin":coin,

            "signal":
            data["signal"],

            "strength":
            data["strength"]

        })


    return results

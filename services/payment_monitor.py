async def start_payment_monitor():

    while True:

        await check_solana_usdt()

        await check_ethereum_usdt()

        await check_bsc_usdt()

        await asyncio.sleep(20)

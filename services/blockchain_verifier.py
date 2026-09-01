import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import aiohttp


logger = logging.getLogger(__name__)


class BlockchainVerifier:

    def __init__(self):

        self.wallets = {

            "SOL": os.getenv(
                "SOL_WALLET",
                "5JSJzkF9GU6GA28J57xxBvSngoaHtbLGGwQkKHGUu1Dt"
            ),

            "ETH": os.getenv(
                "ETH_WALLET",
                "0xF79A1bEc46037dcA06077889F4bb1A111B67723e"
            ),

            "BSC": os.getenv(
                "BSC_WALLET",
                "0xF79A1bEc46037dcA06077889F4bb1A111B67723e"
            )
        }


        self.rpc_urls = {

            "ETH": os.getenv("ETH_RPC_URL"),

            "BSC": os.getenv("BSC_RPC_URL"),

            "SOL": os.getenv("SOL_RPC_URL")
        }


        self.sol_usdt_mint = os.getenv(
            "SOL_USDT_MINT"
        )


        self.evm_lookback_blocks = int(
            os.getenv(
                "EVM_LOOKBACK_BLOCKS",
                "500"
            )
        )


        self.payment_tolerance = Decimal(
            os.getenv(
                "PAYMENT_TOLERANCE",
                "0.000001"
            )
        )


        # USDT contracts
        self.usdt_contracts = {

            "ETH": (
                "0xdAC17F958D2ee523a2206206994597C13D831ec7"
            ),

            "BSC": (
                "0x55d398326f99059fF775485246999027B3197955"
            )
        }


    # =========================================================
    # RPC CALL
    # =========================================================

    async def _rpc_call(
        self,
        url,
        method,
        params
    ):

        if not url:

            raise ValueError(
                f"RPC URL is missing for {method}"
            )


        payload = {

            "jsonrpc": "2.0",

            "id": 1,

            "method": method,

            "params": params
        }


        timeout = aiohttp.ClientTimeout(
            total=20
        )


        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                url,
                json=payload
            ) as response:

                response.raise_for_status()

                data = await response.json()


                if "error" in data:

                    raise Exception(
                        str(data["error"])
                    )


                return data.get(
                    "result"
                )


    # =========================================================
    # WAIT FOR PAYMENT
    # =========================================================

    async def wait_for_payment(

        self,

        network,

        wallet,

        expected_amount,

        created_at,

        timeout_minutes=30,

        check_interval=20
    ):

        network = network.upper()


        expected_amount = Decimal(
            str(expected_amount)
        )


        if created_at.tzinfo is None:

            created_at = created_at.replace(
                tzinfo=timezone.utc
            )


        timeout_time = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                minutes=timeout_minutes
            )
        )


        logger.info(
            f"Waiting for payment | "
            f"Network={network} | "
            f"Wallet={wallet} | "
            f"Amount={expected_amount}"
        )


        while (
            datetime.now(
                timezone.utc
            )
            < timeout_time
        ):

            try:

                # =============================================
                # Ethereum
                # =============================================

                if network == "ETH":

                    result = (
                        await self._check_evm_payment(

                            network="ETH",

                            wallet=wallet,

                            expected_amount=expected_amount,

                            created_at=created_at
                        )
                    )


                # =============================================
                # Binance Smart Chain
                # =============================================

                elif network == "BSC":

                    result = (
                        await self._check_evm_payment(

                            network="BSC",

                            wallet=wallet,

                            expected_amount=expected_amount,

                            created_at=created_at
                        )
                    )


                # =============================================
                # Solana
                # =============================================

                elif network == "SOL":

                    result = (
                        await self._check_solana_payment(

                            wallet=wallet,

                            expected_amount=expected_amount,

                            created_at=created_at
                        )
                    )


                else:

                    return {

                        "found": False,

                        "status": "error",

                        "message": (
                            f"Unsupported network: "
                            f"{network}"
                        )
                    }


                # =============================================
                # Payment Found
                # =============================================

                if result:

                    return {

                        "found": True,

                        "status": "confirmed",

                        "tx_hash": result[
                            "tx_hash"
                        ],

                        "amount": str(
                            result[
                                "amount"
                            ]
                        ),

                        "network": network
                    }


            except Exception as e:

                logger.exception(
                    f"Blockchain check error "
                    f"({network}): {e}"
                )


            await asyncio.sleep(
                check_interval
            )


        return {

            "found": False,

            "status": "expired",

            "network": network
        }


    # =========================================================
    # EVM PAYMENT CHECK
    # =========================================================

    async def _check_evm_payment(

        self,

        network,

        wallet,

        expected_amount,

        created_at
    ):

        rpc_url = self.rpc_urls.get(
            network
        )


        contract = self.usdt_contracts.get(
            network
        )


        if not rpc_url:

            raise ValueError(
                f"{network}_RPC_URL is missing"
            )


        if not contract:

            raise ValueError(
                f"USDT contract missing for "
                f"{network}"
            )


        # آخر بلوك
        latest_block_hex = (
            await self._rpc_call(

                rpc_url,

                "eth_blockNumber",

                []
            )
        )


        latest_block = int(
            latest_block_hex,
            16
        )


        from_block = max(

            0,

            latest_block
            - self.evm_lookback_blocks
        )


        logger.info(
            f"Checking {network} blocks "
            f"{from_block} -> {latest_block}"
        )


        # ERC20 Transfer event
        transfer_topic = (
            "0xddf252ad"
            "1be2c89b69c2b068fc378daa"
            "952ba7f163c4a11628f55a4df523b3ef"
        )


        # Padding wallet address إلى 32 bytes

        wallet_topic = (

            "0x000000000000000000000000"

            + wallet.lower()
            .replace("0x", "")
        )


        logs = await self._rpc_call(

            rpc_url,

            "eth_getLogs",

            [

                {

                    "fromBlock": hex(
                        from_block
                    ),

                    "toBlock": hex(
                        latest_block
                    ),

                    "address": contract,

                    "topics": [

                        transfer_topic,

                        None,

                        wallet_topic
                    ]
                }

            ]
        )


        if not logs:

            return None


        # =====================================================
        # البحث عن التحويل الصحيح
        # =====================================================

        for log in reversed(logs):

            try:

                tx_hash = log.get(
                    "transactionHash"
                )


                # amount موجود في data

                raw_amount = int(
                    log[
                        "data"
                    ],
                    16
                )


                # USDT على Ethereum وBSC
                # عادة 6 decimals

                amount = (
                    Decimal(raw_amount)
                    / Decimal(
                        10 ** 6
                    )
                )


                if abs(
                    amount
                    - expected_amount
                ) > self.payment_tolerance:

                    continue


                # الحصول على البلوك

                block_number = int(
                    log[
                        "blockNumber"
                    ],
                    16
                )


                block = await self._rpc_call(

                    rpc_url,

                    "eth_getBlockByNumber",

                    [

                        hex(
                            block_number
                        ),

                        False
                    ]
                )


                if not block:

                    continue


                timestamp = datetime.fromtimestamp(

                    int(
                        block[
                            "timestamp"
                        ],
                        16
                    ),

                    tz=timezone.utc
                )


                # تجاهل أي دفعة قبل إنشاء الفاتورة

                if timestamp < created_at:

                    continue


                logger.info(
                    f"Payment found | "
                    f"Network={network} | "
                    f"TX={tx_hash} | "
                    f"Amount={amount}"
                )


                return {

                    "tx_hash": tx_hash,

                    "amount": amount
                }


            except Exception as e:

                logger.error(
                    f"Error reading {network} "
                    f"log: {e}"
                )

                continue


        return None


    # =========================================================
    # SOLANA PAYMENT CHECK
    # =========================================================

    async def _check_solana_payment(

        self,

        wallet,

        expected_amount,

        created_at
    ):

        rpc_url = self.rpc_urls.get(
            "SOL"
        )


        if not rpc_url:

            raise ValueError(
                "SOL_RPC_URL is missing"
            )


        if not self.sol_usdt_mint:

            raise ValueError(
                "SOL_USDT_MINT is missing"
            )


        # =============================================
        # الحصول على آخر التواقيع للمحفظة
        # =============================================

        signatures = (
            await self._rpc_call(

                rpc_url,

                "getSignaturesForAddress",

                [

                    wallet,

                    {

                        "limit": 50
                    }

                ]
            )
        )


        if not signatures:

            return None


        # =============================================
        # فحص المعاملات
        # =============================================

        for signature_data in signatures:

            try:

                signature = (
                    signature_data.get(
                        "signature"
                    )
                )


                block_time = (
                    signature_data.get(
                        "blockTime"
                    )
                )


                if not signature:

                    continue


                if block_time:

                    tx_time = (
                        datetime.fromtimestamp(

                            block_time,

                            tz=timezone.utc
                        )
                    )


                    if tx_time < created_at:

                        continue


                transaction = (
                    await self._rpc_call(

                        rpc_url,

                        "getTransaction",

                        [

                            signature,

                            {

                                "encoding": "jsonParsed",

                                "maxSupportedTransactionVersion": 0
                            }

                        ]
                    )
                )


                if not transaction:

                    continue


                meta = transaction.get(
                    "meta"
                )


                if not meta:

                    continue


                pre_balances = meta.get(
                    "preTokenBalances",
                    []
                )


                post_balances = meta.get(
                    "postTokenBalances",
                    []
                )


                # =========================================
                # مقارنة Token Balances
                # =========================================

                pre_map = {

                    item.get(
                        "accountIndex"
                    ): item

                    for item in pre_balances
                }


                post_map = {

                    item.get(
                        "accountIndex"
                    ): item

                    for item in post_balances
                }


                for account_index, post in post_map.items():

                    try:

                        # يجب أن يكون USDT

                        if post.get(
                            "mint"
                        ) != self.sol_usdt_mint:

                            continue


                        # صاحب الحساب يجب أن يكون محفظتنا

                        if post.get(
                            "owner"
                        ) != wallet:

                            continue


                        post_amount = Decimal(

                            str(

                                post[
                                    "uiTokenAmount"
                                ].get(

                                    "uiAmountString",

                                    "0"
                                )
                            )
                        )


                        pre = pre_map.get(
                            account_index
                        )


                        pre_amount = Decimal(
                            "0"
                        )


                        if pre:

                            pre_amount = Decimal(

                                str(

                                    pre[
                                        "uiTokenAmount"
                                    ].get(

                                        "uiAmountString",

                                        "0"
                                    )
                                )
                            )


                        received = (
                            post_amount
                            - pre_amount
                        )


                        if abs(

                            received
                            - expected_amount

                        ) <= self.payment_tolerance:


                            logger.info(

                                f"Solana payment found | "

                                f"TX={signature} | "

                                f"Amount={received}"
                            )


                            return {

                                "tx_hash": signature,

                                "amount": received
                            }


                    except Exception as e:

                        logger.error(

                            f"Error checking Solana "

                            f"balance: {e}"
                        )


            except Exception as e:

                logger.error(
                    f"Error checking Solana "
                    f"transaction: {e}"
                )

                continue


        return None

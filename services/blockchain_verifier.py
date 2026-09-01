import os
import asyncio
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

import aiohttp


logger = logging.getLogger(__name__)


class BlockchainVerifier:
    """
    مراقبة والتحقق من مدفوعات USDT تلقائياً.

    الشبكات المدعومة:
    - Ethereum
    - BSC
    - Solana

    الاستخدام:

    result = await verifier.check_payment(
        network="BSC",
        wallet="0x...",
        expected_amount=25.000001,
        created_at=datetime.now(timezone.utc)
    )
    """

    # ==========================================================
    # USDT Contracts
    # ==========================================================

    EVM_USDT_CONTRACTS = {
        "ETH": os.getenv(
            "ETH_USDT_CONTRACT",
            "0xdAC17F958D2ee523a2206206994597C13D831ec7"
        ),

        "BSC": os.getenv(
            "BSC_USDT_CONTRACT",
            "0x55d398326f99059fF775485246999027B3197955"
        )
    }

    # يجب وضع Mint الصحيح في متغير البيئة
    # SOL_USDT_MINT
    SOL_USDT_MINT = os.getenv(
        "SOL_USDT_MINT",
        ""
    )

    # ==========================================================
    # RPC URLs
    # ==========================================================

    RPC_URLS = {
        "ETH": os.getenv(
            "ETH_RPC_URL",
            ""
        ),

        "BSC": os.getenv(
            "BSC_RPC_URL",
            ""
        ),

        "SOL": os.getenv(
            "SOL_RPC_URL",
            "https://api.mainnet-beta.solana.com"
        )
    }

    # عدد الـ Blocks التي سيتم البحث فيها
    EVM_LOOKBACK_BLOCKS = int(
        os.getenv(
            "EVM_LOOKBACK_BLOCKS",
            "500"
        )
    )

    # الحد الأدنى من التطابق
    AMOUNT_TOLERANCE = Decimal(
        os.getenv(
            "PAYMENT_TOLERANCE",
            "0.000001"
        )
    )

    # Topic الخاص بـ ERC20 Transfer(address,address,uint256)
    TRANSFER_TOPIC = (
        "0xddf252ad1be2c89b69c2b068fc378daa"
        "952ba7f163c4a11628f55a4df523b3ef"
    )

    def __init__(self):
        logger.info(
            "BlockchainVerifier initialized"
        )

    # ==========================================================
    # دالة عامة للتحقق من الدفع
    # ==========================================================

    async def check_payment(
        self,
        network: str,
        wallet: str,
        expected_amount,
        created_at=None
    ):
        """
        يبحث عن دفعة USDT تلقائياً.

        Parameters:
            network:
                SOL / ETH / BSC

            wallet:
                عنوان المحفظة المستقبلة

            expected_amount:
                المبلغ المطلوب

            created_at:
                وقت إنشاء الفاتورة

        Returns:
            dict
        """

        network = network.upper()

        try:

            expected_amount = Decimal(
                str(expected_amount)
            )

        except (
            InvalidOperation,
            ValueError
        ):

            logger.error(
                f"Invalid expected amount: "
                f"{expected_amount}"
            )

            return self._error_response(
                "INVALID_AMOUNT"
            )

        logger.info(
            f"Checking payment | "
            f"Network={network} | "
            f"Wallet={wallet} | "
            f"Amount={expected_amount}"
        )

        if network == "ETH":

            return await self._check_evm_payment(
                network="ETH",
                wallet=wallet,
                expected_amount=expected_amount,
                created_at=created_at
            )

        if network == "BSC":

            return await self._check_evm_payment(
                network="BSC",
                wallet=wallet,
                expected_amount=expected_amount,
                created_at=created_at
            )

        if network == "SOL":

            return await self._check_solana_payment(
                wallet=wallet,
                expected_amount=expected_amount,
                created_at=created_at
            )

        return self._error_response(
            "UNSUPPORTED_NETWORK"
        )

    # ==========================================================
    # EVM RPC
    # ==========================================================

    async def _rpc_call(
        self,
        url,
        method,
        params
    ):
        """
        تنفيذ JSON-RPC request.
        """

        if not url:

            raise ValueError(
                "RPC URL is not configured"
            )

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }

        timeout = aiohttp.ClientTimeout(
            total=30
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
                f"RPC error: {data['error']}"
            )

        return data.get(
            "result"
        )

    # ==========================================================
    # التحقق من Ethereum و BSC
    # ==========================================================

    async def _check_evm_payment(
        self,
        network,
        wallet,
        expected_amount,
        created_at
    ):

        try:

            rpc_url = self.RPC_URLS.get(
                network
            )

            contract = self.EVM_USDT_CONTRACTS.get(
                network
            )

            if not rpc_url:

                logger.error(
                    f"RPC URL missing for {network}"
                )

                return self._error_response(
                    "RPC_NOT_CONFIGURED"
                )

            if not contract:

                return self._error_response(
                    "USDT_CONTRACT_NOT_CONFIGURED"
                )

            # ==================================================
            # الحصول على آخر Block
            # ==================================================

            latest_block_hex = await self._rpc_call(
                rpc_url,
                "eth_blockNumber",
                []
            )

            latest_block = int(
                latest_block_hex,
                16
            )

            from_block = max(
                0,
                latest_block - self.EVM_LOOKBACK_BLOCKS
            )

            # ==================================================
            # تجهيز عنوان المستلم في Topic
            # ==================================================

            clean_wallet = wallet.lower()

            if clean_wallet.startswith(
                "0x"
            ):
                clean_wallet = clean_wallet[2:]

            if len(clean_wallet) != 40:

                return self._error_response(
                    "INVALID_WALLET"
                )

            recipient_topic = (
                "0x"
                + "0" * 24
                + clean_wallet
            )

            # ==================================================
            # البحث عن Transfer events
            # ==================================================

            filter_data = {
                "fromBlock": hex(
                    from_block
                ),

                "toBlock": "latest",

                "address": contract,

                "topics": [
                    self.TRANSFER_TOPIC,
                    None,
                    recipient_topic
                ]
            }

            logs = await self._rpc_call(
                rpc_url,
                "eth_getLogs",
                [filter_data]
            )

            if not logs:

                return self._pending_response(
                    network
                )

            logger.info(
                f"{len(logs)} payment events found "
                f"on {network}"
            )

            # ==================================================
            # فحص كل تحويل
            # ==================================================

            for log in reversed(logs):

                try:

                    amount_raw = int(
                        log["data"],
                        16
                    )

                    # USDT على ETH و BSC عادة 6 decimals
                    amount = (
                        Decimal(amount_raw)
                        / Decimal("1000000")
                    )

                    if not self._amount_matches(
                        amount,
                        expected_amount
                    ):

                        continue

                    block_number = int(
                        log["blockNumber"],
                        16
                    )

                    block = await self._rpc_call(
                        rpc_url,
                        "eth_getBlockByNumber",
                        [
                            hex(block_number),
                            False
                        ]
                    )

                    if not block:

                        continue

                    block_timestamp = datetime.fromtimestamp(
                        int(
                            block["timestamp"],
                            16
                        ),
                        tz=timezone.utc
                    )

                    # ==========================================
                    # تجاهل التحويلات قبل إنشاء الفاتورة
                    # ==========================================

                    if created_at:

                        invoice_time = (
                            self._normalize_datetime(
                                created_at
                            )
                        )

                        if (
                            block_timestamp
                            < invoice_time
                        ):

                            continue

                    tx_hash = log.get(
                        "transactionHash"
                    )

                    logger.info(
                        f"Valid payment found | "
                        f"Network={network} | "
                        f"Amount={amount} | "
                        f"Hash={tx_hash}"
                    )

                    return {
                        "found": True,
                        "status": "confirmed",
                        "network": network,
                        "token": "USDT",
                        "amount": float(amount),
                        "amount_decimal": str(amount),
                        "tx_hash": tx_hash,
                        "block_number": block_number,
                        "timestamp": block_timestamp.isoformat()
                    }

                except Exception as log_error:

                    logger.exception(
                        f"Error processing payment log: "
                        f"{log_error}"
                    )

                    continue

            return self._pending_response(
                network
            )

        except Exception as e:

            logger.exception(
                f"EVM payment check error: {e}"
            )

            return {
                "found": False,
                "status": "error",
                "network": network,
                "error": str(e)
            }

    # ==========================================================
    # Solana RPC
    # ==========================================================

    async def _check_solana_payment(
        self,
        wallet,
        expected_amount,
        created_at
    ):

        try:

            rpc_url = self.RPC_URLS.get(
                "SOL"
            )

            if not rpc_url:

                return self._error_response(
                    "RPC_NOT_CONFIGURED"
                )

            if not self.SOL_USDT_MINT:

                logger.error(
                    "SOL_USDT_MINT is not configured"
                )

                return self._error_response(
                    "SOL_USDT_MINT_NOT_CONFIGURED"
                )

            # ==================================================
            # الحصول على حساب USDT الخاص بالمحفظة
            # ==================================================

            token_accounts_result = (
                await self._rpc_call(
                    rpc_url,
                    "getTokenAccountsByOwner",
                    [
                        wallet,
                        {
                            "mint": self.SOL_USDT_MINT
                        },
                        {
                            "encoding": "jsonParsed"
                        }
                    ]
                )
            )

            token_accounts = (
                token_accounts_result.get(
                    "value",
                    []
                )
            )

            if not token_accounts:

                return self._pending_response(
                    "SOL"
                )

            # ==================================================
            # فحص كل Token Account
            # ==================================================

            for account in token_accounts:

                token_account = account.get(
                    "pubkey"
                )

                if not token_account:

                    continue

                signatures_result = (
                    await self._rpc_call(
                        rpc_url,
                        "getSignaturesForAddress",
                        [
                            token_account,
                            {
                                "limit": 30
                            }
                        ]
                    )
                )

                for signature_data in (
                    signatures_result
                ):

                    signature = signature_data.get(
                        "signature"
                    )

                    block_time = signature_data.get(
                        "blockTime"
                    )

                    if not signature:

                        continue

                    # ==========================================
                    # التحقق من وقت الفاتورة
                    # ==========================================

                    if (
                        created_at
                        and block_time
                    ):

                        tx_time = (
                            datetime.fromtimestamp(
                                block_time,
                                tz=timezone.utc
                            )
                        )

                        invoice_time = (
                            self._normalize_datetime(
                                created_at
                            )
                        )

                        if (
                            tx_time
                            < invoice_time
                        ):

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

                    if meta.get(
                        "err"
                    ) is not None:

                        continue

                    pre_balances = (
                        meta.get(
                            "preTokenBalances",
                            []
                        )
                    )

                    post_balances = (
                        meta.get(
                            "postTokenBalances",
                            []
                        )
                    )

                    amount_received = (
                        self._calculate_solana_received(
                            token_account,
                            pre_balances,
                            post_balances
                        )
                    )

                    if amount_received <= Decimal(
                        "0"
                    ):

                        continue

                    if not self._amount_matches(
                        amount_received,
                        expected_amount
                    ):

                        continue

                    logger.info(
                        f"Valid Solana payment found | "
                        f"Amount={amount_received} | "
                        f"Hash={signature}"
                    )

                    return {
                        "found": True,
                        "status": "confirmed",
                        "network": "SOL",
                        "token": "USDT",
                        "amount": float(
                            amount_received
                        ),
                        "amount_decimal": str(
                            amount_received
                        ),
                        "tx_hash": signature,
                        "timestamp": (
                            datetime.fromtimestamp(
                                block_time,
                                tz=timezone.utc
                            ).isoformat()
                            if block_time
                            else None
                        )
                    }

            return self._pending_response(
                "SOL"
            )

        except Exception as e:

            logger.exception(
                f"Solana payment check error: {e}"
            )

            return {
                "found": False,
                "status": "error",
                "network": "SOL",
                "error": str(e)
            }

    # ==========================================================
    # حساب المبلغ المستلم في Solana
    # ==========================================================

    def _calculate_solana_received(
        self,
        token_account,
        pre_balances,
        post_balances
    ):

        try:

            pre_amount = Decimal("0")
            post_amount = Decimal("0")

            for balance in pre_balances:

                if balance.get(
                    "accountIndex"
                ) is None:
                    continue

                if (
                    balance.get(
                        "mint"
                    )
                    != self.SOL_USDT_MINT
                ):
                    continue

                amount_info = balance.get(
                    "uiTokenAmount",
                    {}
                )

                pre_amount += Decimal(
                    str(
                        amount_info.get(
                            "uiAmountString",
                            "0"
                        )
                    )
                )

            for balance in post_balances:

                if (
                    balance.get(
                        "mint"
                    )
                    != self.SOL_USDT_MINT
                ):
                    continue

                amount_info = balance.get(
                    "uiTokenAmount",
                    {}
                )

                post_amount += Decimal(
                    str(
                        amount_info.get(
                            "uiAmountString",
                            "0"
                        )
                    )
                )

            received = (
                post_amount - pre_amount
            )

            return received

        except Exception as e:

            logger.error(
                f"Solana amount calculation error: {e}"
            )

            return Decimal("0")

    # ==========================================================
    # مقارنة المبالغ
    # ==========================================================

    def _amount_matches(
        self,
        received_amount,
        expected_amount
    ):

        difference = abs(
            received_amount
            - expected_amount
        )

        return (
            difference
            <= self.AMOUNT_TOLERANCE
        )

    # ==========================================================
    # مراقبة الدفع حتى النجاح أو انتهاء الوقت
    # ==========================================================

    async def wait_for_payment(
        self,
        network,
        wallet,
        expected_amount,
        created_at=None,
        timeout_minutes=30,
        check_interval=20
    ):
        """
        مراقبة الدفع تلقائياً.

        لا يحتاج المستخدم إلى إرسال Transaction Hash.

        يفحص الشبكة كل check_interval ثانية.
        """

        logger.info(
            f"Starting payment monitor | "
            f"Network={network} | "
            f"Amount={expected_amount}"
        )

        total_seconds = (
            timeout_minutes * 60
        )

        elapsed = 0

        while elapsed < total_seconds:

            result = await self.check_payment(
                network=network,
                wallet=wallet,
                expected_amount=expected_amount,
                created_at=created_at
            )

            if result.get(
                "found"
            ):

                return result

            if result.get(
                "status"
            ) == "error":

                logger.warning(
                    f"Payment check error: "
                    f"{result}"
                )

            await asyncio.sleep(
                check_interval
            )

            elapsed += check_interval

        return {
            "found": False,
            "status": "expired",
            "network": network,
            "token": "USDT"
        }

    # ==========================================================
    # أدوات مساعدة
    # ==========================================================

    def _normalize_datetime(
        self,
        value
    ):

        if isinstance(
            value,
            str
        ):

            value = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            )

        if value.tzinfo is None:

            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    def _pending_response(
        self,
        network
    ):

        return {
            "found": False,
            "status": "pending",
            "network": network,
            "token": "USDT"
        }

    def _error_response(
        self,
        error
    ):

        return {
            "found": False,
            "status": "error",
            "error": error
        }

    # ==========================================================
    # توافق مع الكود القديم
    # ==========================================================

    async def verify_transaction(
        self,
        network,
        tx_hash
    ):

        logger.warning(
            "verify_transaction is deprecated. "
            "Use automatic payment monitoring."
        )

        return {
            "hash": tx_hash,
            "status": "pending",
            "amount": 0,
            "token": "USDT",
            "network": network
        }

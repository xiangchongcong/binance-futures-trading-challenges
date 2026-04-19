from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import requests

from app.core.config import AppSettings, get_settings
from app.exchange.exceptions import BinanceAPIError, BinanceClientError, BinanceRequestError

logger = logging.getLogger(__name__)

MAINNET_REST_BASE_URL = "https://fapi.binance.com"
TESTNET_REST_BASE_URL = "https://testnet.binancefuture.com"


class BinanceFuturesClient:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.api_key = settings.credentials.api_key
        self.api_secret = settings.credentials.api_secret
        self.use_testnet = settings.credentials.use_testnet
        self.base_url = TESTNET_REST_BASE_URL if self.use_testnet else MAINNET_REST_BASE_URL
        self.timeout = settings.exchange.request_timeout_seconds
        self.recv_window = settings.exchange.recv_window

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        if self.api_key:
            self.session.headers["X-MBX-APIKEY"] = self.api_key

    def ping(self) -> dict[str, Any]:
        self._request("GET", "/fapi/v1/ping")
        return {
            "success": True,
            "base_url": self.base_url,
            "use_testnet": self.use_testnet,
        }

    def get_server_time(self) -> dict[str, Any]:
        response = self._request("GET", "/fapi/v1/time")
        return {
            "server_time": response["serverTime"],
        }

    def get_account_info(self) -> dict[str, Any]:
        response = self._request("GET", "/fapi/v3/account", signed=True)
        assets = response.get("assets", [])
        positions = response.get("positions", [])
        return {
            "fee_tier": response.get("feeTier"),
            "can_trade": response.get("canTrade"),
            "can_deposit": response.get("canDeposit"),
            "can_withdraw": response.get("canWithdraw"),
            "multi_assets_margin": response.get("multiAssetsMargin"),
            "total_wallet_balance": response.get("totalWalletBalance"),
            "total_unrealized_profit": response.get("totalUnrealizedProfit"),
            "total_margin_balance": response.get("totalMarginBalance"),
            "total_initial_margin": response.get("totalInitialMargin"),
            "total_position_initial_margin": response.get("totalPositionInitialMargin"),
            "total_open_order_initial_margin": response.get("totalOpenOrderInitialMargin"),
            "available_balance": response.get("availableBalance"),
            "max_withdraw_amount": response.get("maxWithdrawAmount"),
            "asset_count": len(assets),
            "position_count": len(positions),
        }

    def get_balance(self) -> list[dict[str, Any]]:
        response = self._request("GET", "/fapi/v3/balance", signed=True)
        return [
            {
                "asset": item.get("asset"),
                "balance": item.get("balance"),
                "available_balance": item.get("availableBalance"),
                "cross_wallet_balance": item.get("crossWalletBalance"),
                "cross_unrealized_pnl": item.get("crossUnPnl"),
                "max_withdraw_amount": item.get("maxWithdrawAmount"),
                "margin_available": item.get("marginAvailable"),
                "update_time": item.get("updateTime"),
            }
            for item in response
        ]

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {"symbol": symbol.upper()} if symbol else None
        response = self._request("GET", "/fapi/v3/positionRisk", params=params, signed=True)
        positions = []
        for item in response:
            position_amt = self._to_decimal(item.get("positionAmt"))
            if position_amt == Decimal("0"):
                continue
            positions.append(
                {
                    "symbol": item.get("symbol"),
                    "position_side": item.get("positionSide"),
                    "position_amt": item.get("positionAmt"),
                    "entry_price": item.get("entryPrice"),
                    "break_even_price": item.get("breakEvenPrice"),
                    "mark_price": item.get("markPrice"),
                    "unrealized_profit": item.get("unRealizedProfit"),
                    "liquidation_price": item.get("liquidationPrice"),
                    "notional": item.get("notional"),
                    "leverage": item.get("leverage"),
                    "margin_type": item.get("marginType"),
                    "isolated_margin": item.get("isolatedMargin"),
                    "update_time": item.get("updateTime"),
                }
            )
        return positions

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {"symbol": symbol.upper()} if symbol else None
        response = self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
        return [self._normalize_order(item) for item in response]

    def get_order(
        self,
        symbol: str,
        *,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        params = self._build_order_lookup_params(
            symbol=symbol,
            order_id=order_id,
            client_order_id=client_order_id,
        )
        response = self._request("GET", "/fapi/v1/order", params=params, signed=True)
        return self._normalize_order(response)

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float | Decimal,
        price: str | float | Decimal | None = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        new_client_order_id: str | None = None,
        dry_run: bool | None = None,
    ) -> dict[str, Any]:
        normalized_side = side.upper()
        normalized_order_type = order_type.upper()
        self._validate_side(normalized_side)
        self._validate_supported_order_type(normalized_order_type)
        self._validate_order_capability(normalized_order_type)

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": normalized_side,
            "type": normalized_order_type,
            "quantity": self._stringify_decimal(quantity),
            "reduceOnly": self._stringify_bool(reduce_only),
            "newOrderRespType": "RESULT",
        }

        if new_client_order_id:
            params["newClientOrderId"] = new_client_order_id

        if normalized_order_type == "LIMIT":
            if price is None:
                raise BinanceClientError("price is required for LIMIT orders")
            params["price"] = self._stringify_decimal(price)
            params["timeInForce"] = time_in_force.upper()
        elif price is not None:
            raise BinanceClientError("price should only be provided for LIMIT orders")

        effective_dry_run = self.settings.execution.dry_run if dry_run is None else dry_run
        if effective_dry_run:
            return {
                "dry_run": True,
                "base_url": self.base_url,
                "payload": params,
            }

        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        return self._normalize_order(response)

    def cancel_order(
        self,
        symbol: str,
        *,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        params = self._build_order_lookup_params(
            symbol=symbol,
            order_id=order_id,
            client_order_id=client_order_id,
        )
        response = self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
        return self._normalize_order(response)

    def cancel_all_orders(self, symbol: str) -> dict[str, Any]:
        response = self._request(
            "DELETE",
            "/fapi/v1/allOpenOrders",
            params={"symbol": symbol.upper()},
            signed=True,
        )
        return {
            "symbol": symbol.upper(),
            "code": response.get("code"),
            "message": response.get("msg"),
        }

    def change_leverage(self, symbol: str, leverage: int) -> dict[str, Any]:
        if leverage < 1 or leverage > 125:
            raise BinanceClientError("leverage must be between 1 and 125.")
        response = self._request(
            "POST",
            "/fapi/v1/leverage",
            params={"symbol": symbol.upper(), "leverage": leverage},
            signed=True,
        )
        return {
            "symbol": response.get("symbol"),
            "leverage": response.get("leverage"),
            "max_notional_value": response.get("maxNotionalValue"),
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> Any:
        request_params = {key: value for key, value in (params or {}).items() if value is not None}
        headers: dict[str, str] = {}

        if signed:
            self._require_credentials()
            request_params["timestamp"] = self._timestamp_ms()
            request_params["recvWindow"] = self.recv_window
            request_params["signature"] = self._sign(request_params)
            headers["X-MBX-APIKEY"] = self.api_key

        url = f"{self.base_url}{path}"
        sanitized_params = self._sanitize_params(request_params)
        logger.info("Binance REST request method=%s path=%s params=%s", method, path, sanitized_params)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=request_params,
                timeout=self.timeout,
                headers=headers,
            )
        except requests.RequestException as exc:
            raise BinanceRequestError(
                f"Failed to call Binance Futures REST API path={path}: {exc}"
            ) from exc

        payload = self._decode_json(response)
        if response.status_code >= 400:
            error_message = self._extract_error_message(payload, response.text)
            logger.error(
                "Binance REST error method=%s path=%s status=%s code=%s message=%s",
                method,
                path,
                response.status_code,
                payload.get("code") if isinstance(payload, dict) else None,
                error_message,
            )
            raise BinanceAPIError(
                error_message,
                status_code=response.status_code,
                error_code=payload.get("code") if isinstance(payload, dict) else None,
                response_payload=payload,
            )

        return payload

    def _require_credentials(self) -> None:
        if not self.api_key or not self.api_secret:
            raise BinanceClientError(
                "BINANCE_API_KEY and BINANCE_API_SECRET are required for signed Binance requests."
            )

    def _sign(self, params: dict[str, Any]) -> str:
        query_string = urlencode(params, doseq=True)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _timestamp_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _decode_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise BinanceRequestError(
                f"Binance returned a non-JSON response with status={response.status_code}."
            ) from exc

    @staticmethod
    def _extract_error_message(payload: Any, fallback_text: str) -> str:
        if isinstance(payload, dict):
            code = payload.get("code")
            message = payload.get("msg")
            if code is not None and message:
                return f"Binance API error code={code}: {message}"
            if message:
                return str(message)
        return fallback_text

    @staticmethod
    def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(params)
        for key in ("signature",):
            if key in sanitized:
                sanitized[key] = "***"
        return sanitized

    @staticmethod
    def _normalize_order(order: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": order.get("symbol"),
            "order_id": order.get("orderId"),
            "client_order_id": order.get("clientOrderId"),
            "status": order.get("status"),
            "side": order.get("side"),
            "type": order.get("type"),
            "orig_type": order.get("origType"),
            "price": order.get("price"),
            "avg_price": order.get("avgPrice"),
            "orig_qty": order.get("origQty"),
            "executed_qty": order.get("executedQty"),
            "cum_quote": order.get("cumQuote"),
            "time_in_force": order.get("timeInForce"),
            "reduce_only": order.get("reduceOnly"),
            "position_side": order.get("positionSide"),
            "update_time": order.get("updateTime"),
        }

    def _validate_order_capability(self, order_type: str) -> None:
        if order_type == "MARKET" and not self.settings.execution.allow_market_order:
            raise BinanceClientError("MARKET orders are disabled by configuration.")
        if order_type == "LIMIT" and not self.settings.execution.allow_limit_order:
            raise BinanceClientError("LIMIT orders are disabled by configuration.")

    @staticmethod
    def _validate_side(side: str) -> None:
        if side not in {"BUY", "SELL"}:
            raise BinanceClientError("side must be BUY or SELL.")

    @staticmethod
    def _validate_supported_order_type(order_type: str) -> None:
        if order_type not in {"MARKET", "LIMIT"}:
            raise BinanceClientError("order_type must be MARKET or LIMIT.")

    @staticmethod
    def _build_order_lookup_params(
        *,
        symbol: str,
        order_id: int | None,
        client_order_id: str | None,
    ) -> dict[str, Any]:
        if order_id is None and client_order_id is None:
            raise BinanceClientError("Either order_id or client_order_id must be provided.")

        params: dict[str, Any] = {"symbol": symbol.upper()}
        if order_id is not None:
            params["orderId"] = order_id
        if client_order_id is not None:
            params["origClientOrderId"] = client_order_id
        return params

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        return Decimal(str(value))

    @staticmethod
    def _stringify_decimal(value: str | float | Decimal) -> str:
        return str(value)

    @staticmethod
    def _stringify_bool(value: bool) -> str:
        return "true" if value else "false"


def create_binance_futures_client(settings: AppSettings | None = None) -> BinanceFuturesClient:
    return BinanceFuturesClient(settings or get_settings())

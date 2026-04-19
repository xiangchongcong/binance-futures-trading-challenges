class BinanceClientError(RuntimeError):
    """Base exception for Binance client failures."""


class BinanceRequestError(BinanceClientError):
    """Raised when the HTTP request to Binance fails before a valid response."""


class BinanceAPIError(BinanceClientError):
    """Raised when Binance returns an API error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: int | None = None,
        response_payload: object | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_payload = response_payload

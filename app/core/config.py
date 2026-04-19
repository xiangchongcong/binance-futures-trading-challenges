from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config" / "config.example.yaml"


class AppConfig(BaseModel):
    name: str = "binance-futures-trading-challenges"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


class ExchangeConfig(BaseModel):
    symbol: str = "BTCUSDT"
    default_leverage: int = 5
    recv_window: int = 5000
    request_timeout_seconds: float = 10.0


class ExecutionConfig(BaseModel):
    max_single_order_notional_usdt: float = 100.0
    max_open_exposure_usdt: float = 500.0
    allow_market_order: bool = True
    allow_limit_order: bool = True
    dry_run: bool = True


class RiskConfig(BaseModel):
    max_daily_loss_pct: float = 3.0
    max_consecutive_losses: int = 3
    max_api_failures: int = 5


class MonitoringConfig(BaseModel):
    kline_interval: str = "1m"
    volatility_threshold_pct: float = 1.5
    reconnect_delay_seconds: int = 5


class ServiceConfig(BaseModel):
    enable_api: bool = True
    enable_market_monitor: bool = True
    enable_user_stream: bool = True


class YamlConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig = Field(default_factory=AppConfig)
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_use_testnet: bool = True
    app_config_file: str = str(DEFAULT_CONFIG_PATH)


class BinanceCredentials(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    use_testnet: bool = True


class AppSettings(BaseModel):
    app: AppConfig
    exchange: ExchangeConfig
    execution: ExecutionConfig
    risk: RiskConfig
    monitoring: MonitoringConfig
    service: ServiceConfig
    credentials: BinanceCredentials


class ConfigLoadError(RuntimeError):
    """Raised when environment or YAML configuration cannot be loaded."""


def _resolve_config_path(env_settings: EnvSettings) -> Path:
    configured_path = Path(env_settings.app_config_file)
    if not configured_path.is_absolute():
        configured_path = BASE_DIR / configured_path

    if configured_path.exists():
        return configured_path

    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    return EXAMPLE_CONFIG_PATH


def _load_yaml_config(config_path: Path) -> YamlConfig:
    with config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}
    try:
        return YamlConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigLoadError(
            f"Invalid YAML config at {config_path}. "
            "Please update config/config.yaml to match config/config.example.yaml."
        ) from exc


def build_config_summary(settings: AppSettings) -> dict[str, object]:
    return {
        "app": {
            "name": settings.app.name,
            "host": settings.app.host,
            "port": settings.app.port,
            "log_level": settings.app.log_level,
        },
        "exchange": {
            "symbol": settings.exchange.symbol,
            "default_leverage": settings.exchange.default_leverage,
            "use_testnet": settings.credentials.use_testnet,
            "recv_window": settings.exchange.recv_window,
            "request_timeout_seconds": settings.exchange.request_timeout_seconds,
        },
        "execution": {
            "dry_run": settings.execution.dry_run,
            "allow_market_order": settings.execution.allow_market_order,
            "allow_limit_order": settings.execution.allow_limit_order,
            "max_single_order_notional_usdt": settings.execution.max_single_order_notional_usdt,
            "max_open_exposure_usdt": settings.execution.max_open_exposure_usdt,
        },
        "risk": {
            "max_daily_loss_pct": settings.risk.max_daily_loss_pct,
            "max_consecutive_losses": settings.risk.max_consecutive_losses,
            "max_api_failures": settings.risk.max_api_failures,
        },
        "monitoring": {
            "kline_interval": settings.monitoring.kline_interval,
            "volatility_threshold_pct": settings.monitoring.volatility_threshold_pct,
            "reconnect_delay_seconds": settings.monitoring.reconnect_delay_seconds,
        },
        "service": settings.service.model_dump(),
        "credentials": {
            "api_key_configured": bool(settings.credentials.api_key),
            "api_secret_configured": bool(settings.credentials.api_secret),
        },
    }


@lru_cache
def get_env_settings() -> EnvSettings:
    return EnvSettings()


@lru_cache
def get_config_path() -> Path:
    return _resolve_config_path(get_env_settings())


@lru_cache
def get_settings() -> AppSettings:
    env_settings = get_env_settings()
    yaml_config = _load_yaml_config(get_config_path())

    return AppSettings(
        app=yaml_config.app,
        exchange=yaml_config.exchange,
        execution=yaml_config.execution,
        risk=yaml_config.risk,
        monitoring=yaml_config.monitoring,
        service=yaml_config.service,
        credentials=BinanceCredentials(
            api_key=env_settings.binance_api_key,
            api_secret=env_settings.binance_api_secret,
            use_testnet=env_settings.binance_use_testnet,
        ),
    )

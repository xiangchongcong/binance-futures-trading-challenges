from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config" / "config.example.yaml"


class ApiServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class ExchangeConfig(BaseModel):
    name: str = "binance_futures"
    base_url: str = "https://fapi.binance.com"
    websocket_url: str = "wss://fstream.binance.com/ws"
    recv_window_ms: int = 5000


class RiskControlConfig(BaseModel):
    enabled: bool = True
    max_daily_loss_pct: float = 5.0
    pause_on_error: bool = True


class MonitoringConfig(BaseModel):
    account_poll_interval_seconds: int = 15
    market_poll_interval_seconds: int = 5


class StrategyRuntimeConfig(BaseModel):
    enabled: bool = False
    mode: str = "manual"
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT"])


class RuntimeConfig(BaseModel):
    service_name: str = "binance-futures-trading-challenges"
    api: ApiServerConfig = Field(default_factory=ApiServerConfig)
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    risk: RiskControlConfig = Field(default_factory=RiskControlConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    strategy: StrategyRuntimeConfig = Field(default_factory=StrategyRuntimeConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "binance-futures-trading-challenges"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"
    binance_api_key: str = ""
    binance_api_secret: str = ""
    app_config_file: str = str(DEFAULT_CONFIG_PATH)


def _resolve_config_path(settings: Settings) -> Path:
    configured_path = Path(settings.app_config_file)
    if not configured_path.is_absolute():
        configured_path = BASE_DIR / configured_path

    if configured_path.exists():
        return configured_path

    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    return EXAMPLE_CONFIG_PATH


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_runtime_config() -> RuntimeConfig:
    settings = get_settings()
    config_path = _resolve_config_path(settings)
    with config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}
    return RuntimeConfig.model_validate(raw_config)

import json

import typer
import uvicorn

from app.core.config import ConfigLoadError, build_config_summary, get_config_path, get_settings
from app.core.logging import setup_logging
from app.exchange import (
    BinanceAPIError,
    BinanceClientError,
    BinanceRequestError,
    create_binance_futures_client,
)

cli = typer.Typer(
    help="CLI for the Binance futures trading challenges service.",
    no_args_is_help=True,
)


def _print_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _handle_exchange_error(exc: Exception) -> None:
    typer.echo(f"Exchange command failed: {exc}")
    raise typer.Exit(code=1)


def _get_exchange_client():
    try:
        get_settings()
    except ConfigLoadError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    return create_binance_futures_client()


@cli.command()
def serve(
    host: str | None = typer.Option(None, help="Bind host for the HTTP server."),
    port: int | None = typer.Option(None, help="Bind port for the HTTP server."),
    reload: bool = typer.Option(False, help="Enable auto reload for local development."),
) -> None:
    """Run the FastAPI service locally."""
    setup_logging()
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=host or settings.app.host,
        port=port or settings.app.port,
        reload=reload,
    )


@cli.command("show-config")
def show_config() -> None:
    """Print loaded environment and YAML configuration."""
    try:
        settings = get_settings()
    except ConfigLoadError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    payload = settings.model_dump(exclude={"credentials": {"api_key", "api_secret"}})
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@cli.command("check-config")
def check_config() -> None:
    """Validate and print a concise config summary."""
    try:
        settings = get_settings()
    except ConfigLoadError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    summary = build_config_summary(settings)
    typer.echo(f"Config file: {get_config_path()}")
    typer.echo(json.dumps(summary, indent=2, ensure_ascii=False))
    typer.echo("Config validation passed.")


@cli.command("ping-exchange")
def ping_exchange() -> None:
    """Verify Binance Futures REST connectivity."""
    client = _get_exchange_client()
    try:
        payload = {
            "ping": client.ping(),
            "server_time": client.get_server_time(),
        }
    except (BinanceAPIError, BinanceClientError, BinanceRequestError) as exc:
        _handle_exchange_error(exc)
    _print_json(payload)


@cli.command("show-balance")
def show_balance() -> None:
    """Show futures account balances."""
    client = _get_exchange_client()
    try:
        payload = {
            "account": client.get_account_info(),
            "balances": client.get_balance(),
        }
    except (BinanceAPIError, BinanceClientError, BinanceRequestError) as exc:
        _handle_exchange_error(exc)
    _print_json(payload)


@cli.command("show-positions")
def show_positions(
    symbol: str | None = typer.Option(None, help="Optional symbol filter, e.g. BTCUSDT."),
) -> None:
    """Show current futures positions."""
    client = _get_exchange_client()
    try:
        payload = client.get_positions(symbol=symbol)
    except (BinanceAPIError, BinanceClientError, BinanceRequestError) as exc:
        _handle_exchange_error(exc)
    _print_json(payload)


@cli.command("show-open-orders")
def show_open_orders(
    symbol: str | None = typer.Option(None, help="Optional symbol filter, e.g. BTCUSDT."),
) -> None:
    """Show current open orders."""
    client = _get_exchange_client()
    try:
        payload = client.get_open_orders(symbol=symbol)
    except (BinanceAPIError, BinanceClientError, BinanceRequestError) as exc:
        _handle_exchange_error(exc)
    _print_json(payload)


@cli.command("change-leverage")
def change_leverage(
    leverage: int = typer.Argument(..., help="Target leverage, from 1 to 125."),
    symbol: str | None = typer.Option(None, help="Optional symbol override."),
) -> None:
    """Change leverage for a symbol."""
    client = _get_exchange_client()
    target_symbol = symbol or get_settings().exchange.symbol
    try:
        payload = client.change_leverage(symbol=target_symbol, leverage=leverage)
    except (BinanceAPIError, BinanceClientError, BinanceRequestError) as exc:
        _handle_exchange_error(exc)
    _print_json(payload)


@cli.command("place-order")
def place_order(
    side: str = typer.Argument(..., help="BUY or SELL."),
    order_type: str = typer.Argument(..., help="MARKET or LIMIT."),
    quantity: str = typer.Argument(..., help="Order quantity."),
    symbol: str | None = typer.Option(None, help="Optional symbol override."),
    price: str | None = typer.Option(None, help="Required for LIMIT orders."),
    time_in_force: str = typer.Option("GTC", "--time-in-force", help="Only used for LIMIT orders."),
    reduce_only: bool = typer.Option(False, help="Set order as reduce-only."),
    new_client_order_id: str | None = typer.Option(None, help="Optional custom client order id."),
    dry_run: bool | None = typer.Option(
        None,
        "--dry-run/--execute",
        help="Override configured dry-run behavior.",
    ),
) -> None:
    """Place a manual futures order."""
    client = _get_exchange_client()
    target_symbol = symbol or get_settings().exchange.symbol
    try:
        payload = client.place_order(
            symbol=target_symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
            new_client_order_id=new_client_order_id,
            dry_run=dry_run,
        )
    except (BinanceAPIError, BinanceClientError, BinanceRequestError) as exc:
        _handle_exchange_error(exc)
    _print_json(payload)


if __name__ == "__main__":
    cli()

import json

import typer
import uvicorn

from app.core.config import get_runtime_config, get_settings
from app.core.logging import setup_logging

cli = typer.Typer(
    help="CLI for the Binance futures trading challenges service.",
    no_args_is_help=True,
)


@cli.command()
def serve(
    host: str | None = typer.Option(None, help="Bind host for the HTTP server."),
    port: int | None = typer.Option(None, help="Bind port for the HTTP server."),
    reload: bool = typer.Option(False, help="Enable auto reload for local development."),
) -> None:
    """Run the FastAPI service locally."""
    setup_logging()
    runtime_config = get_runtime_config()
    uvicorn.run(
        "main:app",
        host=host or runtime_config.api.host,
        port=port or runtime_config.api.port,
        reload=reload or runtime_config.api.reload,
    )


@cli.command("show-config")
def show_config() -> None:
    """Print loaded environment and YAML configuration."""
    settings = get_settings()
    runtime_config = get_runtime_config()
    payload = {
        "settings": settings.model_dump(exclude={"binance_api_key", "binance_api_secret"}),
        "runtime_config": runtime_config.model_dump(),
    }
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cli()

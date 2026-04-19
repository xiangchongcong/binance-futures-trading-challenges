import json

import typer
import uvicorn

from app.core.config import ConfigLoadError, build_config_summary, get_config_path, get_settings
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


if __name__ == "__main__":
    cli()

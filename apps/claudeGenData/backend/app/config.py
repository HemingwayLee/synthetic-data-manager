from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "claudeGenData"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    # The path prefix nginx serves this app under (e.g. "/claudeGenData"). nginx strips it before proxying; FastAPI
    # only uses it to build correct URLs (the docs page's openapi.json link).
    root_path: str = ""
    # Only needed when the frontend runs on another origin; through nginx (or the Vite proxy) it's same-origin.
    cors_origins: list[str] = ["http://localhost:5101"]

    # Claude Code (Agent SDK) settings
    claude_workspace: str = "/workspace"
    claude_default_model: str = "claude-opus-5-5"
    claude_allowed_tools: list[str] = [
        "Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebSearch", "WebFetch", "TodoWrite",
    ]

    # Business document generation
    bizdoc_data_dir: str = "/data/bizdoc"
    bizdoc_concurrency: int = 2
    # Each finished batch is packed into <exports_dir>/<unix seconds>.tar.gz for other systems (see app/exports.py).
    exports_dir: str = "/data/exports"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "app2"
    database_url: str = "postgresql+psycopg://app2:app2@localhost:5432/app2"
    # The path prefix nginx serves this app under (e.g. "/app2"). nginx strips it before proxying; FastAPI only
    # uses it to build correct URLs (the docs page's openapi.json link).
    root_path: str = ""

    # The script each run executes: generate.sh <N> <folder> [seed].
    generate_script: str = "/generator/generate.sh"
    # Each run writes its image + mask pairs to <output_dir>/<run id>/; run records live in <output_dir>/.runs/.
    output_dir: str = "/output"
    # Largest N accepted for one run, and how many runs may generate at once (the rest wait).
    max_count: int = 100_000
    max_concurrent_runs: int = 2


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "randomHtmlTables"
    database_url: str = "postgresql+psycopg://randomHtmlTables:randomHtmlTables@localhost:5432/randomHtmlTables"
    # The path prefix nginx serves this app under (e.g. "/randomHtmlTables"). nginx strips it before proxying; FastAPI only
    # uses it to build correct URLs (the docs page's openapi.json link).
    root_path: str = ""

    # The script each run executes: generate.sh <N> <folder> [seed].
    generate_script: str = "/generator/generate.sh"
    # Each run writes its image + mask pairs to <output_dir>/<run id>/; run records live in <output_dir>/.runs/.
    output_dir: str = "/output"
    # Largest N accepted for one run, and how many runs may generate at once (the rest wait).
    max_count: int = 100_000
    max_concurrent_runs: int = 2
    # Each finished run is also packed into <exports_dir>/<unix seconds>.tar.gz for other systems (see app/exports.py).
    exports_dir: str = "/output/exports"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "app"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    # The path prefix nginx serves this app under (e.g. "/app2"). nginx strips it before proxying; FastAPI only
    # uses it to build correct URLs (the docs page's openapi.json link).
    root_path: str = ""


settings = Settings()

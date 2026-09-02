from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    platform_database_url: str = "postgresql+asyncpg://platform:platform@localhost:55431/platform"
    lab_admin_host: str = "localhost"
    lab_public_host: str = "localhost"
    lab_admin_port: int = 55432
    lab_public_port: int = 55432
    lab_admin_user: str = "lab_admin"
    lab_admin_password: str = "lab_admin"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

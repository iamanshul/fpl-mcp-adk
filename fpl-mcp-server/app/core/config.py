#app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Defines the applications configuration settings.
    Pydantic automatically reads these from env varibles or .env file.
    
    Args:
        BaseSettings (_type_): _description_
    """
    GCP_PROJECT_ID: str
    FPL_API_BASE_URL: str
    SYNC_INTERVAL_HOURS: int = 2
    SYNC_SECRET: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    Using lru_cache ensures the settings are loaded only once.

    Returns:
        Settings: settings
    """
    return Settings()
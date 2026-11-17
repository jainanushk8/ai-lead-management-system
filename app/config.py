"""
app/config.py
Central configuration for the application.

HOW IT WORKS:
- Uses pydantic-settings to load values from the .env file at the project root.
- Every module in the application imports `settings` from this file.
- Changing a value in .env changes the behavior everywhere without touching code.
- Default values are provided so the app runs even without a .env file.

INTERVIEW NOTES:
- pydantic-settings validates types at startup. If OLLAMA_TIMEOUT_SECONDS is set
  to "abc" in .env, the app will refuse to start with a clear validation error
  rather than crashing at runtime.
- env_file_encoding is set to utf-8 for Windows compatibility.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "AI-Powered Lead Management & Automation System"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Database ---
    DATABASE_PATH: str = "./leads.db"

    # --- Ollama / Hermes LLM ---
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "hermes3:3b"
    OLLAMA_TIMEOUT_SECONDS: int = 120

    # --- Concurrency ---
    MAX_CONCURRENT_INFERENCES: int = 1

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton instance used throughout the application.
settings = Settings()

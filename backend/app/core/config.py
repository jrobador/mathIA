import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file variables
load_dotenv()

class Settings(BaseSettings):
    # Core
    API_HOST: str = os.getenv("API_HOST", "azure") # Default to azure
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000") # For generating static file URLs

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_CHAT_DEPLOYMENT: str | None = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    AZURE_TENANT_ID: str | None = os.getenv("AZURE_TENANT_ID") # For AAD

    # Stability AI (Optional)
    STABILITY_API_KEY: str | None = os.getenv("STABILITY_API_KEY")
    STABILITY_API_HOST: str = os.getenv("STABILITY_API_HOST", "https://api.stability.ai")
    STABILITY_ENGINE_ID: str = os.getenv("STABILITY_ENGINE_ID", "stable-diffusion-ultra")

    # Azure Speech (Optional)
    AZURE_SPEECH_KEY: str | None = os.getenv("AZURE_SPEECH_KEY")
    AZURE_SPEECH_REGION: str | None = os.getenv("AZURE_SPEECH_REGION")

    class Config:
        # If using a .env file locally for development
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" # Ignore extra fields from .env

settings = Settings()

# Basic validation for Azure OpenAI settings if host is Azure
if settings.API_HOST == "azure":
    if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_CHAT_DEPLOYMENT:
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_CHAT_DEPLOYMENT must be set when API_HOST is 'azure'")
    # Add check for key or tenant ID depending on your auth method
    if not settings.AZURE_OPENAI_API_KEY and not settings.AZURE_TENANT_ID:
         print("Warning: Neither AZURE_OPENAI_API_KEY nor AZURE_TENANT_ID is set for Azure OpenAI AAD auth.")
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify that the required environment variables are set
required_vars = [
    'AZURE_OPENAI_ENDPOINT',
    'AZURE_OPENAI_API_KEY',
    'AZURE_OPENAI_CHAT_DEPLOYMENT'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"WARNING: The following required environment variables are not set: {', '.join(missing_vars)}")
    print("The application may not function properly.")

# General configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Allowed URLs for CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# Azure DALL-E configuration (image generation)
AZURE_DALLE_ENDPOINT = os.getenv("AZURE_DALLE_ENDPOINT")
AZURE_DALLE_API_KEY = os.getenv("AZURE_DALLE_API_KEY")

# Azure Speech configuration (text-to-speech)
AZURE_SPEECH_SUBSCRIPTION_KEY = os.getenv("AZURE_SPEECH_SUSCRIPTION_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# Function to check if a service is properly configured
def is_service_configured(service: str) -> bool:
    """
    Checks if a specific service is properly configured.
    
    Args:
        service: Name of the service ("openai", "dalle", "speech")
        
    Returns:
        True if the service is properly configured, False otherwise
    """
    if service == "openai":
        return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_CHAT_DEPLOYMENT)
    elif service == "dalle":
        return bool(AZURE_DALLE_ENDPOINT and AZURE_DALLE_API_KEY)
    elif service == "speech":
        return bool(AZURE_SPEECH_SUBSCRIPTION_KEY and AZURE_SPEECH_REGION)
    else:
        return False
    
OPENAI_AVAILABLE = is_service_configured("openai")
DALLE_AVAILABLE = is_service_configured("dalle")
SPEECH_AVAILABLE = is_service_configured("speech")
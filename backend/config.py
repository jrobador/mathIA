import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Verificar que las variables de entorno obligatorias están configuradas
required_vars = [
    'AZURE_OPENAI_ENDPOINT',
    'AZURE_OPENAI_API_KEY',
    'AZURE_OPENAI_CHAT_DEPLOYMENT'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"ADVERTENCIA: Las siguientes variables de entorno obligatorias no están configuradas: {', '.join(missing_vars)}")
    print("La aplicación puede no funcionar correctamente.")

# Configuración general
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# URLs permitidas para CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Configuración de Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# Configuración de Azure DALL-E (generación de imágenes)
AZURE_DALLE_ENDPOINT = os.getenv("AZURE_DALLE_ENDPOINT")
AZURE_DALLE_API_KEY = os.getenv("AZURE_DALLE_API_KEY")

# Configuración de Azure Speech (texto a voz)
AZURE_SPEECH_SUBSCRIPTION_KEY = os.getenv("AZURE_SPEECH_SUSCRIPTION_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# Función para comprobar si un servicio está correctamente configurado
def is_service_configured(service: str) -> bool:
    """
    Comprueba si un servicio específico está correctamente configurado.
    
    Args:
        service: Nombre del servicio ("openai", "dalle", "speech")
        
    Returns:
        True si el servicio está correctamente configurado, False en caso contrario
    """
    if service == "openai":
        return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_CHAT_DEPLOYMENT)
    elif service == "dalle":
        return bool(AZURE_DALLE_ENDPOINT and AZURE_DALLE_API_KEY)
    elif service == "speech":
        return bool(AZURE_SPEECH_SUBSCRIPTION_KEY and AZURE_SPEECH_REGION)
    else:
        return False

# Verificar qué servicios están disponibles
OPENAI_AVAILABLE = is_service_configured("openai")
DALLE_AVAILABLE = is_service_configured("dalle")
SPEECH_AVAILABLE = is_service_configured("speech")

print(f"Servicios disponibles - OpenAI: {OPENAI_AVAILABLE}, DALL-E: {DALLE_AVAILABLE}, Speech: {SPEECH_AVAILABLE}")
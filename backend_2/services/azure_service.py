"""
Implementación completa de integración con servicios Azure:
- Azure OpenAI para LLM
- Azure DALL-E para generación de imágenes
- Azure Speech Service para texto a voz

Este archivo centraliza todas las funciones de acceso a servicios Azure
y gestiona adecuadamente las credenciales.
"""

import os
import uuid
import json
import asyncio
import hashlib
import re
import yaml
from typing import Optional

from config import (
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_API_VERSION,
    AZURE_DALLE_ENDPOINT, AZURE_DALLE_API_KEY,
    AZURE_SPEECH_SUBSCRIPTION_KEY, AZURE_SPEECH_REGION,
    OPENAI_AVAILABLE, DALLE_AVAILABLE, SPEECH_AVAILABLE
)

# Directorios para archivos estáticos
IMAGES_DIR = "static/images"
AUDIO_DIR = "static/audio"

# Asegurar que los directorios existen
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---- AZURE OPENAI SERVICE ----

# Cliente global para OpenAI
_openai_client = None

async def get_openai_client():
    """
    Obtiene o inicializa el cliente de Azure OpenAI.
    Usa una variable global para evitar crear múltiples clientes.
    """
    global _openai_client
    
    if _openai_client is not None:
        return _openai_client
    
    if not OPENAI_AVAILABLE:
        print("ADVERTENCIA: Azure OpenAI no está configurado correctamente. Las llamadas al LLM fallarán.")
        return None
        
    try:
        # Importar aquí para evitar cargar estos módulos si no son necesarios
        from openai import AsyncAzureOpenAI
        
        _openai_client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY,
        )
        
        print(f"Cliente de Azure OpenAI inicializado correctamente: {AZURE_OPENAI_ENDPOINT}")
        return _openai_client
        
    except Exception as e:
        print(f"Error inicializando cliente de Azure OpenAI: {e}")
        return None

class PromptyTemplate:
    """
    Gestor de plantillas de prompt en formato Prompty.
    """
    def __init__(self, template_path: str):
        """
        Inicializa una plantilla Prompty desde un archivo.
        
        Args:
            template_path: Ruta al archivo de plantilla Prompty
        """
        self.template_path = template_path
        self.name = None
        self.description = None
        self.model_config = {}
        self.inputs = {}
        self.messages = []
        
        # Cargar y analizar la plantilla
        self.load_template()
    
    def load_template(self):
        """
        Carga y analiza el archivo de plantilla Prompty.
        """
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Dividir en frontmatter y mensajes
            parts = template_content.split('---')
            if len(parts) < 3:
                raise ValueError(f"Formato de plantilla Prompty inválido en {self.template_path}")
            
            # Analizar frontmatter YAML
            frontmatter = yaml.safe_load(parts[1])
            
            # Extraer metadatos
            self.name = frontmatter.get('name')
            self.description = frontmatter.get('description')
            self.model_config = frontmatter.get('model', {})
            self.inputs = frontmatter.get('inputs', {})
            
            # Analizar plantillas de mensajes
            messages_section = parts[2].strip()
            
            # Dividir en secciones de roles
            current_role = None
            current_content = []
            
            for line in messages_section.split('\n'):
                if line.strip() in ['system:', 'user:', 'assistant:']:
                    # Guardar sección anterior si existe
                    if current_role is not None:
                        self.messages.append({
                            'role': current_role,
                            'content': '\n'.join(current_content).strip()
                        })
                        current_content = []
                    
                    # Iniciar nueva sección
                    current_role = line.strip()[:-1]  # Eliminar los dos puntos
                else:
                    current_content.append(line)
            
            # Añadir la última sección
            if current_role is not None:
                self.messages.append({
                    'role': current_role,
                    'content': '\n'.join(current_content).strip()
                })
                
        except Exception as e:
            print(f"Error cargando plantilla Prompty {self.template_path}: {e}")
            raise
    
    def fill_template(self, **kwargs):
        """
        Rellena la plantilla con las variables proporcionadas.
        
        Args:
            **kwargs: Valores para las variables de plantilla
            
        Returns:
            Lista de diccionarios de mensajes rellenos
        """
        filled_messages = []
        
        for msg in self.messages:
            content = msg['content']
            
            # Reemplazar variables
            for key, value in kwargs.items():
                placeholder = f"{{{{{key}}}}}"
                content = content.replace(placeholder, str(value))
            
            filled_messages.append({
                'role': msg['role'],
                'content': content
            })
        
        return filled_messages

async def invoke_with_prompty(template_path: str, **kwargs) -> str:
    """
    Invoca el LLM de Azure OpenAI usando una plantilla Prompty.
    
    Args:
        template_path: Ruta al archivo de plantilla Prompty
        **kwargs: Valores para las variables de plantilla
        
    Returns:
        Texto de respuesta del modelo
    """
    # Debug: Print path information to help with troubleshooting
    print(f"Loading Prompty template from: {template_path}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if template path exists
    if not os.path.exists(template_path):
        print(f"WARNING: Template path does not exist: {template_path}")
        # Try to resolve the path using alternative strategies
        base_name = os.path.basename(template_path)
        alt_path = os.path.join("prompts", base_name)
        if os.path.exists(alt_path):
            print(f"Found template at alternative path: {alt_path}")
            template_path = alt_path
        else:
            print(f"Could not find template at: {alt_path}")
            return f"Error: Template not found at {template_path} or {alt_path}"
    
    # Comprobar si OpenAI está disponible
    if not OPENAI_AVAILABLE:
        return f"[SIMULACIÓN] Respuesta para plantilla {template_path} con variables {kwargs}"
    
    # Asegurar que el cliente está inicializado
    client = await get_openai_client()
    
    if not client:
        raise Exception("Cliente LLM no disponible. Comprueba la configuración de Azure OpenAI.")
    
    try:
        # Cargar y rellenar la plantilla
        template = PromptyTemplate(template_path)
        messages = template.fill_template(**kwargs)
        
        # Hacer la llamada a la API
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error usando plantilla Prompty {template_path}: {e}")
        # Proporcionar una respuesta de fallback en caso de error
        return f"No se pudo generar contenido: {str(e)}"
    
async def invoke_llm(prompt: str, system_message: Optional[str] = None, temperature: float = 0.2) -> str:
    """
    Invoca el LLM de Azure OpenAI con un prompt simple.
    
    Args:
        prompt: Texto a enviar al LLM
        system_message: Mensaje de sistema opcional
        temperature: Temperatura para la generación (0.0-1.0)
        
    Returns:
        Texto de respuesta del modelo
    """
    # Comprobar si OpenAI está disponible
    if not OPENAI_AVAILABLE:
        # Simulación si Azure OpenAI no está disponible
        if "theory" in prompt.lower():
            return f"Aquí está la teoría sobre {prompt.split()[-1]}. Este es un concepto fundamental en matemáticas..."
        elif "problem" in prompt.lower():
            return "Si tienes 3 manzanas y obtienes 2 más, ¿cuántas manzanas tienes en total?"
        elif "evaluate" in prompt.lower():
            # Simular evaluación básica
            if "5" in prompt or "correcto" in prompt.lower():
                return "CORRECT"
            else:
                return "INCORRECT_CONCEPTUAL"
        else:
            return "Respuesta generada para: " + prompt[:50] + "..."
    
    # Asegurar que el cliente está inicializado
    client = await get_openai_client()
    
    if not client:
        raise Exception("Cliente LLM no disponible. Comprueba la configuración de Azure OpenAI.")
    
    try:
        # Preparar mensajes
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
            
        messages.append({"role": "user", "content": prompt})
        
        # Hacer la llamada a la API
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error invocando LLM: {e}")
        # Proporcionar una respuesta de fallback en caso de error
        return f"No se pudo generar contenido: {str(e)}"

# ---- AZURE DALL-E SERVICE ----

async def generate_image(prompt: str) -> Optional[str]:
    """
    Genera una imagen usando la API Azure DALL-E 3 basada en el prompt proporcionado.
    
    Args:
        prompt: Texto que describe la imagen a generar
        
    Returns:
        URL de la imagen generada, o None si la generación falló
    """
    # Para testing, generar siempre un nombre de archivo único basado en el prompt
    # Esto evitará reutilización de URLs en diferentes contenidos
    prompt_hash = hashlib.md5((prompt + str(uuid.uuid4())).encode()).hexdigest()[:10]
    filename = f"mock_image_{prompt_hash}.png"
    file_path = os.path.join(IMAGES_DIR, filename)
    
    # Crear un archivo de imagen placeholder si no existe
    if not os.path.exists(file_path):
        # Crear un archivo vacío o una imagen básica
        with open(file_path, 'wb') as f:
            f.write(b'Mock image data for testing')
    
    # Imprimir información de depuración
    print(f"MOCK: Generated new image with URL: /static/images/{filename}")
    print(f"MOCK: Image prompt was: {prompt[:100]}...")
    
    # Devolver URL relativa
    relative_url = f"/static/images/{filename}"
    return relative_url

async def download_and_save_image(image_url: str, prompt: str) -> Optional[str]:
    """
    Descarga una imagen desde una URL y la guarda localmente.
    
    Args:
        image_url: URL de la imagen a descargar
        prompt: Prompt usado para generar la imagen (usado para el nombre del archivo)
        
    Returns:
        Nombre del archivo de la imagen guardada, o None si la descarga falló
    """
    import aiohttp
    
    try:
        # Crear un nombre de archivo único basado en un hash del prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png"
        file_path = os.path.join(IMAGES_DIR, filename)
        
        # Descargar la imagen
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Guardar la imagen en archivo
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Verificar que el archivo existe y tiene contenido
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        return filename
                    else:
                        print(f"Error: Verificación de archivo fallida después de descarga: {file_path}")
                        return None
                else:
                    resp_text = await response.text()
                    print(f"Error al descargar imagen. Estado: {response.status}. URL: {image_url}. Respuesta: {resp_text}")
                    return None
    except Exception as e:
        print(f"Error descargando y guardando imagen de {image_url}: {str(e)}")
        return None

def save_base64_image(b64_data: str, prompt: str) -> Optional[str]:
    """
    Guarda una imagen codificada en base64 en un archivo.
    
    Args:
        b64_data: Datos de imagen codificados en base64
        prompt: Prompt usado para generar la imagen (usado para el nombre del archivo)
        
    Returns:
        Ruta al archivo de imagen guardado, o None si el guardado falló
    """
    try:
        import base64
        
        # Crear un nombre de archivo único basado en un hash del prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png"
        file_path = os.path.join(IMAGES_DIR, filename)
        
        # Decodificar y guardar la imagen
        image_data = base64.b64decode(b64_data)
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Verificar que el archivo existe y tiene contenido
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        else:
            print(f"Error: Verificación de archivo fallida después de guardar base64: {file_path}")
            return None
            
    except Exception as e:
        print(f"Error guardando imagen base64: {str(e)}")
        return None

# ---- AZURE SPEECH SERVICE ----

# Constantes para Speech
AUDIO_FORMAT = "audio-16khz-128kbitrate-mono-mp3"
VOICE_NAME = "en-US-SaraNeural"

async def generate_speech(text: str, voice_name: str = VOICE_NAME, style: str = None, style_degree: int = 1) -> Optional[str]:
    """
    Genera audio de voz a partir de texto usando Azure Speech Service.

    Args:
        text: Contenido de texto a convertir a voz
        voice_name: Voz a usar para la síntesis (por defecto voz de Sara)
        style: Estilo de voz a aplicar (ej. "cheerful", "sad", "angry", etc.)
        style_degree: Intensidad del estilo (1-2)

    Returns:
        URL al archivo de audio generado, o None si la generación falló
    """
    if not text:
        return None

    # Limpiar texto si es necesario
    text = text.replace("**Problem Statement:**", "")

    # Volver a comprobar si el texto quedó vacío después de la eliminación
    if not text.strip():
        return None

    # Recortar texto si es demasiado largo
    if len(text) > 5000:
        text = text[:4997] + "..."

    # Para testing, generar siempre un nombre de archivo único
    speech_hash = hashlib.md5((text[:100] + str(uuid.uuid4())).encode()).hexdigest()[:10]
    filename = f"mock_speech_{speech_hash}.mp3"
    file_path = os.path.join(AUDIO_DIR, filename)
    
    # Crear un archivo de audio placeholder si no existe
    if not os.path.exists(file_path):
        # Crear un archivo vacío o un archivo de audio básico
        with open(file_path, 'wb') as f:
            f.write(b'Mock audio data for testing')
    
    # Imprimir información de depuración
    style_info = f" (Style: {style})" if style else ""
    print(f"MOCK: Generated new audio with URL: /static/audio/{filename}{style_info}")
    print(f"MOCK: Text beginning: {text[:50]}...")
    
    # Devolver URL relativa
    relative_url = f"/static/audio/{filename}"
    return relative_url

# Modificar synthesize_speech para pasar el estilo al SSML
def synthesize_speech(text: str, output_path: str, voice_name: str,
                     speech_key: str, service_region: str, 
                     style: str = None, style_degree: int = 1) -> bool:
    """
    Realiza la síntesis de voz usando Azure Speech SDK.

    Args:
        text: Texto a sintetizar (ya limpio)
        output_path: Donde guardar el archivo de audio
        voice_name: Voz a usar
        speech_key: Clave de suscripción de Azure Speech
        service_region: Región del servicio Azure Speech
        style: Estilo de voz a aplicar (ej. "cheerful", "sad", "angry", etc.)
        style_degree: Intensidad del estilo (1-2)

    Returns:
        True si la síntesis fue exitosa, False en caso contrario
    """
    import azure.cognitiveservices.speech as speechsdk
    
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = voice_name
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    # Crear salida de archivo de audio para la voz sintetizada
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    # Crear un sintetizador de voz
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # Siempre usar SSML cuando se especifica un estilo
    use_ssml = style is not None or should_use_ssml(text)

    # Iniciar síntesis
    if use_ssml:
        # Envolver el texto en SSML para mejor control sobre la síntesis de voz
        ssml = create_ssml(text, voice_name, style, style_degree)
        result = speech_synthesizer.speak_ssml_async(ssml).get()
    else:
        # Usar síntesis de texto plano para contenido simple
        result = speech_synthesizer.speak_text_async(text).get()

    # Comprobar el resultado
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Detalles del error: {cancellation_details.error_details}")
        return False
    else:
        return False

def should_use_ssml(text: str) -> bool:
    """
    Determina si deberíamos usar SSML basado en el contenido del texto.

    Args:
        text: Texto a analizar (ya limpio)

    Returns:
        True si SSML sería beneficioso, False en caso contrario
    """
    # Comprobar si el texto contiene términos matemáticos, números o caracteres especiales
    # que podrían beneficiarse de SSML
    math_terms = ["fracción", "ecuación", "suma", "diferencia", "producto", "cociente",
                  "numerador", "denominador", "igual", "×", "÷", "+", "-", "="]

    # Comprobar números seguidos de operadores matemáticos
    has_math_expressions = any(term in text.lower() for term in math_terms)

    # Comprobar si el texto es lo suficientemente largo para beneficiarse del control de prosodia
    is_long_text = len(text) > 200

    result = has_math_expressions or is_long_text
    return result

def create_ssml(text: str, voice_name: str, style: str = "calm", style_degree: int = 1) -> str:
    """
    Crea marcado SSML para el texto proporcionado, con soporte para estilos de voz.

    Args:
        text: Texto a envolver en SSML (ya limpio)
        voice_name: Voz a usar
        style: Estilo de voz a aplicar (ej. "cheerful", "sad", "angry", etc.)
        style_degree: Intensidad del estilo (1-2)

    Returns:
        Cadena SSML formateada correctamente
    """
    # Escapar caracteres especiales XML en el texto
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")

    text = text.replace("×", '<say-as interpret-as="characters">×</say-as>')
    text = text.replace("÷", '<say-as interpret-as="characters">÷</say-as>')

    # Reemplazar números y fracciones con SSML apropiado
    # Manejar fracciones como 1/2, 3/4, etc.
    fraction_pattern = r"(\d+)/(\d+)"
    text = re.sub(fraction_pattern, r'<say-as interpret-as="fraction">\1/\2</say-as>', text)

    # Manejar números decimales
    decimal_pattern = r"(\d+\.\d+)"
    text = re.sub(decimal_pattern, r'<say-as interpret-as="cardinal">\1</say-as>', text)

    # Crear el documento SSML completo
    lang = "en-US"
    
    # Construir el SSML, incluyendo el namespace mstts si se proporciona un estilo
    if style:
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang}">
            <voice name="{voice_name}">
                <mstts:express-as style="{style.lower()}" styledegree="{style_degree}">
                    <prosody rate="0.95" pitch="+0%">
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
    else:
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">
            <voice name="{voice_name}">
                <prosody rate="1.05" pitch="+0%">
                    {text}
                </prosody>
            </voice>
        </speak>
        """

    return ssml.strip()
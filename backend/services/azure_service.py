"""
Complete integration implementation with Azure services:
- Azure OpenAI for LLM
- Azure DALL-E for imaging
- Azure Speech Service for text-to-speech

This file centralizes all Azure service access functions and properly manages credentials.
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

IMAGES_DIR = "static/images"
AUDIO_DIR = "static/audio"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---- AZURE OPENAI SERVICE ----

_openai_client = None

async def get_openai_client():
    """
    Gets or initializes the Azure OpenAI client.
    Uses a global variable to avoid creating multiple clients.
    """
    global _openai_client
    
    if _openai_client is not None:
        return _openai_client
    
    if not OPENAI_AVAILABLE:
        print("WARNING: Azure OpenAI is not properly configured. LLM calls will fail.")
        return None
        
    try:
        # Import here to avoid loading these modules if not needed
        from openai import AsyncAzureOpenAI
        
        _openai_client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key=AZURE_OPENAI_API_KEY,
        )
        
        print(f"Azure OpenAI client successfully initialized: {AZURE_OPENAI_ENDPOINT}")
        return _openai_client
        
    except Exception as e:
        print(f"Error initializing Azure OpenAI client: {e}")
        return None

class PromptyTemplate:
    """
    Manager for Prompty format templates.
    """
    def __init__(self, template_path: str):
        """
        Initializes a Prompty template from a file.
        
        Args:
            template_path: Path to the Prompty template file
        """
        self.template_path = template_path
        self.name = None
        self.description = None
        self.model_config = {}
        self.inputs = {}
        self.messages = []
        
        # Load and parse the template
        self.load_template()
    
    def load_template(self):
        """
        Loads and parses the Prompty template file.
        """
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Split into frontmatter and messages
            parts = template_content.split('---')
            if len(parts) < 3:
                raise ValueError(f"Invalid Prompty template format in {self.template_path}")
            
            # Parse frontmatter YAML
            frontmatter = yaml.safe_load(parts[1])
            
            # Extract metadata
            self.name = frontmatter.get('name')
            self.description = frontmatter.get('description')
            self.model_config = frontmatter.get('model', {})
            self.inputs = frontmatter.get('inputs', {})
            
            # Parse message templates
            messages_section = parts[2].strip()
            
            # Split into role sections
            current_role = None
            current_content = []
            
            for line in messages_section.split('\n'):
                if line.strip() in ['system:', 'user:', 'assistant:']:
                    # Save the previous section if it exists
                    if current_role is not None:
                        self.messages.append({
                            'role': current_role,
                            'content': '\n'.join(current_content).strip()
                        })
                        current_content = []
                    
                    # Start a new section
                    current_role = line.strip()[:-1]  # Remove the colon
                else:
                    current_content.append(line)
            
            # Add the last section
            if current_role is not None:
                self.messages.append({
                    'role': current_role,
                    'content': '\n'.join(current_content).strip()
                })
                
        except Exception as e:
            print(f"Error loading Prompty template {self.template_path}: {e}")
            raise
    
    def fill_template(self, **kwargs):
        """
        Fills the template with the provided variables.
        
        Args:
            **kwargs: Values for the template variables
            
        Returns:
            List of dictionaries with filled messages
        """
        filled_messages = []
        
        for msg in self.messages:
            content = msg['content']
            
            # Replace variables
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
    Invokes the Azure OpenAI LLM using a Prompty template.

    Args:
    template_path: Path to the Prompty template file
    **kwargs: Values for template variables

    Returns:
    Model response text
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
    
    # Check if OpenAI is available
    if not OPENAI_AVAILABLE:
        return f"[SIMULATION] Response for template {template_path} with variables {kwargs}"
    
    # Ensure the client is initialized
    client = await get_openai_client()
    
    if not client:
        raise Exception("LLM client is not available. Check Azure OpenAI configuration.")
    
    try:
        # Load and fill the template
        template = PromptyTemplate(template_path)
        messages = template.fill_template(**kwargs)
        
        # Make the API call
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error using Prompty template {template_path}: {e}")
        # Provide a fallback response in case of error
        return f"Could not generate content: {str(e)}"
    
    
import os
import json
import hashlib
from typing import Optional, Dict, Any

# Assume these are set elsewhere, e.g., from environment variables or a config file
OPENAI_AVAILABLE = os.getenv("AZURE_OPENAI_API_KEY") is not None
DALLE_AVAILABLE = os.getenv("AZURE_DALLE_API_KEY") is not None
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4") # Example deployment name
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01") # Example API version

AZURE_DALLE_ENDPOINT = os.getenv("AZURE_DALLE_ENDPOINT")
AZURE_DALLE_API_KEY = os.getenv("AZURE_DALLE_API_KEY")

# Directory to save images (ensure it exists)
IMAGES_DIR = os.path.join("static", "images")
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

_openai_client = None

async def get_openai_client():
    """Initializes and returns the async OpenAI client."""
    global _openai_client
    if _openai_client is None and OPENAI_AVAILABLE:
        try:
            # Lazy import openai only if needed and available
            from openai import AsyncAzureOpenAI
            _openai_client = AsyncAzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
            )
        except ImportError:
            print("OpenAI library not installed. Please install with: pip install openai")
            global OPENAI_AVAILABLE
            OPENAI_AVAILABLE = False # Mark as unavailable if import fails
        except Exception as e:
            print(f"Error initializing Azure OpenAI client: {e}")
            OPENAI_AVAILABLE = False # Mark as unavailable on init error
    return _openai_client


async def invoke_llm(prompt: str, system_message: Optional[str] = None, temperature: float = 0.2) -> str:
    """
    Invokes the Azure OpenAI LLM with a simple prompt.

    Args:
        prompt: Text to send to the LLM
        system_message: Optional system message
        temperature: Temperature for generation (0.0-1.0)

    Returns:
        Response text from the model
    """
    # Check if OpenAI is available
    if not OPENAI_AVAILABLE:
        # Simulation if Azure OpenAI is not available
        if "theory" in prompt.lower():
            return f"Here is the theory about {prompt.split()[-1]}. This is a fundamental concept in mathematics..."
        elif "problem" in prompt.lower():
            return "If you have 3 apples and get 2 more, how many apples do you have in total?"
        elif "evaluate" in prompt.lower():
            # Simulate basic evaluation
            if "5" in prompt or "correct" in prompt.lower():
                return "CORRECT"
            else:
                return "INCORRECT_CONCEPTUAL"
        else:
            return "Generated response for: " + prompt[:50] + "..."

    # Ensure the client is initialized
    client = await get_openai_client()

    if not client:
        raise Exception("LLM client not available. Check Azure OpenAI configuration.")

    try:
        # Prepare messages
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        # Make the API call
        response = await client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=temperature,
        )

        # Check if response and choices are valid
        if response.choices and response.choices[0].message and response.choices[0].message.content:
             return response.choices[0].message.content
        else:
             # Handle cases where the response structure is unexpected
             print(f"Unexpected LLM response structure: {response}")
             return "Error: Received an unexpected response format from the LLM."


    except Exception as e:
        print(f"Error invoking LLM: {e}")
        # Provide a fallback response in case of error
        return f"Could not generate content: {str(e)}"

# ---- AZURE DALL-E SERVICE ----

async def generate_image(prompt: str) -> Optional[str]:
    """
    Generates an image using the Azure DALL-E 3 API based on the provided prompt.

    Args:
        prompt: Text describing the image to generate

    Returns:
        URL of the generated image, or None if generation failed
    """
    # Check if DALL-E is available
    if not DALLE_AVAILABLE:
        # Generate a simulated image URL for testing
        filename = f"placeholder_{hashlib.md5(prompt.encode()).hexdigest()[:10]}.png"
        file_path = os.path.join(IMAGES_DIR, filename)

        # Create a placeholder image file if it doesn't exist
        if not os.path.exists(file_path):
            # Create an empty file or basic image data
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (200, 100), color = (73, 109, 137))
                d = ImageDraw.Draw(img)
                try:
                    d.text((10,10), "Placeholder", fill=(255,255,0)) 
                except IOError:
                     d.text((10,10), "Placeholder", fill=(255,255,0)) 
                img.save(file_path)
            except ImportError:
                 # Fallback if Pillow is not installed
                 with open(file_path, 'wb') as f:
                     f.write(b'Placeholder image data') # Very basic fallback
            except Exception as e:
                 print(f"Error creating placeholder image: {e}")
                 # Even more basic fallback: create empty file
                 with open(file_path, 'wb') as f:
                     f.write(b'')


        # Return relative URL
        relative_url = f"/static/images/{filename}" 
        return relative_url

    # Import aiohttp only if needed
    try:
        import aiohttp
    except ImportError:
        print("aiohttp library not installed. Please install with: pip install aiohttp")
        return None # Cannot make request without aiohttp

    # Prepare the API request
    api_version = "2024-02-01"  # API version for DALL-E 3 (check Azure docs for latest)
    # Correct endpoint construction for image generation
    # Note: Deployment name ('dall-e-3' in this case) should match your Azure deployment
    url = f"{AZURE_DALLE_ENDPOINT}/openai/deployments/dall-e-3/images/generations?api-version={api_version}"


    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_DALLE_API_KEY
    }

    # Prepare the request payload
    payload = {
        "model": "dall-e-3",  # Model specified in payload might be redundant if using deployment name in URL, but often included
        "prompt": prompt,
        "size": "1024x1024",  # Default size
        "style": "vivid",     # Can be 'vivid' or 'natural'
        "quality": "standard",  # Can be 'standard' or 'hd'
        "n": 1                # Number of images to generate
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()

                    # Extract the image URL or base64 data from the response
                    if result.get('data') and len(result['data']) > 0:
                        data_item = result['data'][0]

                        image_url = data_item.get('url')
                        if image_url:
                            # Try to download and save the image locally
                            image_filename = await download_and_save_image(image_url, prompt)
                            if image_filename:
                                # Return the local URL (relative path)
                                relative_url = f"/static/images/{image_filename}" # Match placeholder logic
                                return relative_url

                            # Fallback to using the original URL if download fails
                            print(f"Warning: Failed to download image from {image_url}. Returning original URL.")
                            return image_url # Return the Azure URL as a fallback
                        else:
                            # Handle case where image data is base64 encoded
                            image_b64 = data_item.get('b64_json')
                            if image_b64:
                                # Save the image to a file
                                image_path = save_base64_image(image_b64, prompt)
                                if image_path:
                                    # Convert to a URL relative to the API server (adjust based on server setup)
                                    relative_url = f"/static/images/{os.path.basename(image_path)}" # Match placeholder logic
                                    return relative_url

                    # If we get here, we couldn't find the image data
                    print(f"Error: Image URL or base64 data not found in the response. Full response: {json.dumps(result)}")
                    return None
                else:
                    error_text = await response.text()
                    print(f"Error generating image. Status: {response.status}. Response: {error_text}")
                    # Attempt to parse error for more details
                    try:
                        error_json = json.loads(error_text)
                        print(f"Parsed error details: {error_json}")
                    except json.JSONDecodeError:
                         pass # Keep the raw text if not JSON
                    return None
    except aiohttp.ClientConnectorError as e:
         print(f"Connection Error during image generation: {str(e)}. Check endpoint: {AZURE_DALLE_ENDPOINT}")
         return None
    except Exception as e:
        print(f"Exception during image generation: {str(e)}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return None

async def download_and_save_image(image_url: str, prompt: str) -> Optional[str]:
    """
    Downloads an image from a URL and saves it locally.

    Args:
        image_url: URL of the image to download
        prompt: Prompt used to generate the image (used for the filename)

    Returns:
        Filename of the saved image, or None if download failed
    """
    try:
        import aiohttp
    except ImportError:
        print("aiohttp library not installed. Cannot download image.")
        return None

    try:
        # Create a unique filename based on a hash of the prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png" 
        file_path = os.path.join(IMAGES_DIR, filename)

        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()

                    # Save the image to file
                    with open(file_path, 'wb') as f:
                        f.write(image_data)

                    # Verify that the file exists and has content
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        print(f"Image successfully saved to: {file_path}")
                        return filename
                    else:
                        print(f"Error: File verification failed after download: {file_path}")
                        # Attempt to remove potentially corrupted/empty file
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return None
                else:
                    resp_text = await response.text()
                    print(f"Error downloading image. Status: {response.status}. URL: {image_url}. Response: {resp_text}")
                    return None
    except aiohttp.ClientError as e:
        print(f"Network error downloading image from {image_url}: {str(e)}")
        return None
    except IOError as e:
         print(f"File system error saving image to {file_path}: {str(e)}")
         return None
    except Exception as e:
        print(f"Error downloading and saving image from {image_url}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def save_base64_image(b64_data: str, prompt: str) -> Optional[str]:
    """
    Saves a base64 encoded image to a file.

    Args:
        b64_data: Base64 encoded image data
        prompt: Prompt used to generate the image (used for the filename)

    Returns:
        Path to the saved image file, or None if saving failed
    """
    try:
        import base64

        # Create a unique filename based on a hash of the prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png" 
        file_path = os.path.join(IMAGES_DIR, filename)

        # Decode and save the image
        image_data = base64.b64decode(b64_data)

        with open(file_path, 'wb') as f:
            f.write(image_data)

        # Verify that the file exists and has content
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
             print(f"Base64 image successfully saved to: {file_path}")
             return file_path # Return the full path here, consistent with docstring
        else:
            print(f"Error: File verification failed after saving base64: {file_path}")
             # Attempt to remove potentially corrupted/empty file
            if os.path.exists(file_path):
                os.remove(file_path)
            return None

    except base64.binascii.Error as e:
         print(f"Error decoding base64 data: {str(e)}")
         return None
    except IOError as e:
         print(f"File system error saving base64 image to {file_path}: {str(e)}")
         return None
    except Exception as e:
        print(f"Error saving base64 image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# ---- AZURE SPEECH SERVICE ----

# Constants for Speech
AUDIO_FORMAT = "audio-16khz-128kbitrate-mono-mp3"
VOICE_NAME = "en-US-SaraNeural"

async def generate_speech(text: str, voice_name: str = VOICE_NAME, style: str = None, style_degree: int = 1) -> Optional[str]:
    """
    Generates voice audio from text using Azure Speech Service.

    Args:
        text: Text content to convert to speech
        voice_name: Voice to use for synthesis (default is Sara voice)
        style: Voice style to apply such as cheerful, sad, angry
        style_degree: Style intensity (1-2)

    Returns:
        URL to the generated audio file, or None if generation failed
    """
    if not text:
        return None

    # Clean text by removing markdown formatting
    cleaned_text = text
    
    # Remove Problem Statement formatting
    cleaned_text = cleaned_text.replace("Problem Statement:", "")
    
    # Remove all asterisks (markdown formatting)
    cleaned_text = re.sub(r'\*+', '', cleaned_text)
    
    # Remove all numbering symbols
    cleaned_text = re.sub(r'#', '', cleaned_text)
    
    # Remove explanatory parentheticals like (e.g., example)
    cleaned_text = re.sub(r'\(e\.g\.[^)]*\)', '', cleaned_text)
    
    # Check if text is empty after cleaning
    if not cleaned_text.strip():
        return None

    # Truncate text if too long
    if len(cleaned_text) > 5000:
        cleaned_text = cleaned_text[:4997] + "..."

    # Check if Speech is available
    if not SPEECH_AVAILABLE:
        # Generate a simulated audio URL for testing
        filename = f"speech_{hashlib.md5(cleaned_text.encode()).hexdigest()[:10]}.mp3"
        file_path = os.path.join(AUDIO_DIR, filename)
        
        # Create a placeholder audio file if it doesn't exist
        if not os.path.exists(file_path):
            with open(file_path, 'wb') as f:
                f.write(b'Placeholder audio data')
        
        # Return relative URL
        relative_url = f"/static/audio/{filename}"
        return relative_url

    # Generate a unique filename for this audio
    filename = f"speech_{uuid.uuid4().hex}.mp3"
    file_path = os.path.join(AUDIO_DIR, filename)

    try:
        audio_result = await asyncio.to_thread(
            synthesize_speech,
            cleaned_text,  
            file_path,
            voice_name,
            AZURE_SPEECH_SUBSCRIPTION_KEY,
            AZURE_SPEECH_REGION,
            style=style,
            style_degree=style_degree
        )

        if audio_result:
            # Build relative URL
            relative_url = f"/static/audio/{filename}"
            return relative_url
        else:
            return None
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None

def synthesize_speech(text: str, output_path: str, voice_name: str,
                     speech_key: str, service_region: str, 
                     style: str = None, style_degree: int = 1) -> bool:
    """
    Performs speech synthesis using Azure Speech SDK.

    Args:
        text: Text to synthesize (already cleaned)
        output_path: Where to save the audio file
        voice_name: Voice to use
        speech_key: Azure Speech subscription key
        service_region: Azure Speech service region
        style: Voice style to apply (e.g., "cheerful", "sad", "friendly")
        style_degree: Style intensity (1-2)

    Returns:
        True if synthesis was successful, False otherwise
    """
    import azure.cognitiveservices.speech as speechsdk
    
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = voice_name
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    # Create audio output for the synthesized voice
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    # Create a speech synthesizer
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # Always use SSML when a style is specified or if the text requires it
    use_ssml = style is not None or should_use_ssml(text)

    # Start synthesis
    if use_ssml:
        # Wrap the text in SSML for better control over speech synthesis
        ssml = create_ssml(text, voice_name, style, style_degree)
        result = speech_synthesizer.speak_ssml_async(ssml).get()
    else:
        # Use plain text synthesis for simple content
        result = speech_synthesizer.speak_text_async(text).get()

    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Speech synthesized successfully and saved to {output_path}")
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
        return False
    else:
        print(f"Speech synthesis result: {result.reason}")
        return False

def should_use_ssml(text: str) -> bool:
    """
    Determines if we should use SSML based on the text content.

    Args:
        text: Text to analyze (already cleaned)

    Returns:
        True if SSML would be beneficial, False otherwise
    """
    # Check if the text contains mathematical terms, numbers or special characters
    # that could benefit from SSML
    math_terms = ["fraction", "equation", "sum", "difference", "product", "quotient",
                  "numerator", "denominator", "equals", "×", "÷", "+", "-", "="]

    # Check for numbers followed by mathematical operators
    has_math_expressions = any(term in text.lower() for term in math_terms)

    # Check if the text is long enough to benefit from prosody control
    is_long_text = len(text) > 200

    result = has_math_expressions or is_long_text
    return result

def create_ssml(text: str, voice_name: str, style: str = 'calm', style_degree: int = 1) -> str:
    """
    Creates SSML markup for the provided text, with support for voice styles.

    Args:
        text: Text to wrap in SSML (already cleaned)
        voice_name: Voice to use
        style: Voice style to apply (e.g., "cheerful", "sad", "friendly")
        style_degree: Style intensity (1-2)

    Returns:
        Properly formatted SSML string
    """
    # Escape special XML characters in the text
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")

    # Handle special characters for better pronunciation
    text = text.replace("×", '<say-as interpret-as="characters">×</say-as>')
    text = text.replace("÷", '<say-as interpret-as="characters">÷</say-as>')

    # Replace numbers and fractions with appropriate SSML
    # Handle fractions like 1/2, 3/4, etc.
    fraction_pattern = r"(\d+)/(\d+)"
    text = re.sub(fraction_pattern, r'<say-as interpret-as="fraction">\1/\2</say-as>', text)

    # Handle decimal numbers
    decimal_pattern = r"(\d+\.\d+)"
    text = re.sub(decimal_pattern, r'<say-as interpret-as="cardinal">\1</say-as>', text)

    # Determine language based on voice name
    lang = "en-US"
    
    # Build the SSML, including mstts namespace if a style is provided
    if style:
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang}">
            <voice name="{voice_name}">
                <mstts:express-as style="{style.lower()}" styledegree="{style_degree}">
                    <prosody rate="0.9" pitch="+0%">
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
                <prosody rate="0.9" pitch="+0%">
                    {text}
                </prosody>
            </voice>
        </speak>
        """

    return ssml.strip()
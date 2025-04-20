"""
Azure Speech Service Integration

This module provides text-to-speech functionality using Azure Speech Services.
It converts text content into natural-sounding speech audio files.
"""

import os
import uuid
import logging
import asyncio
import azure.cognitiveservices.speech as speechsdk
from app.core.config import settings
from urllib.parse import urljoin

# Set up logging with more detail
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a file handler for detailed logging
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/azure_speech_debug.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Constants
AUDIO_DIR = "static/audio"
AUDIO_FORMAT = "audio-16khz-128kbitrate-mono-mp3"
VOICE_NAME = "en-US-Emma2:DragonHDLatestNeural"
STRING_TO_REMOVE = "**Problem Statement:***" # Define the string to remove

# Ensure the audio directory exists
os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_speech(text: str, voice_name: str = VOICE_NAME) -> str | None:
    """
    Generates speech audio from text using Azure Speech Service.

    Args:
        text: The text content to convert to speech
        voice_name: The voice to use for synthesis (defaults to Emma neural voice)

    Returns:
        URL to the generated audio file, or None if generation failed
    """
    logger.debug(f"=== STARTING SPEECH GENERATION ===")
    logger.debug(f"Voice name: {voice_name}")

    if not text:
        logger.warning("Empty text provided to speech generator")
        return None

    # --- MODIFICATION START ---
    # Remove the specific "**Problem Statement:***" string from the text
    original_length = len(text)
    text = text.replace(STRING_TO_REMOVE, "")
    if len(text) < original_length:
        logger.debug(f"Removed '{STRING_TO_REMOVE}' from input text.")
    # --- MODIFICATION END ---

    # Log text content (truncated for large text)
    if len(text) > 500:
        logger.debug(f"Input text (cleaned, truncated): {text[:500]}...")
        logger.debug(f"Total cleaned text length: {len(text)} characters")
    else:
        logger.debug(f"Input text (cleaned): {text}")

    # Re-check if text became empty after removal
    if not text.strip():
        logger.warning("Text became empty after removing specified string.")
        return None

    # Trim text if it's too long
    if len(text) > 5000:
        logger.warning(f"Cleaned text too long ({len(text)} chars), trimming to 5000 chars")
        text = text[:4997] + "..."

    # Check for required settings
    if not settings.AZURE_SPEECH_SUSCRIPTION_KEY or not settings.AZURE_SPEECH_REGION:
        logger.warning("Azure Speech credentials not configured. Cannot generate speech.")
        logger.debug(f"Speech region configured: {bool(settings.AZURE_SPEECH_REGION)}")
        logger.debug(f"Speech key configured: {bool(settings.AZURE_SPEECH_SUSCRIPTION_KEY)}")
        return None

    # Generate a unique filename for this audio
    filename = f"speech_{uuid.uuid4().hex}.mp3"
    file_path = os.path.join(AUDIO_DIR, filename)
    logger.debug(f"Target file path: {file_path}")

    try:
        # Run the speech synthesis in a separate thread to avoid blocking
        logger.debug("Starting speech synthesis on separate thread...")
        audio_result = await asyncio.to_thread(
            synthesize_speech,
            text, # Pass the cleaned text
            file_path,
            voice_name,
            settings.AZURE_SPEECH_SUSCRIPTION_KEY,
            settings.AZURE_SPEECH_REGION
        )

        if audio_result:
            logger.debug("Speech synthesis succeeded")
            # Construct URL relative to the API server
            relative_url = f"/static/audio/{filename}"
            audio_url = urljoin(settings.BASE_URL, relative_url)
            logger.debug(f"Final audio URL to return: {audio_url}")

            # Verify the file exists and has content
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                logger.debug(f"Verified audio file exists with size: {os.path.getsize(file_path)} bytes")
            else:
                logger.error(f"Audio file verification failed: exists={os.path.exists(file_path)}, size={os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")

            return audio_url
        else:
            logger.error("Speech synthesis failed")
            return None
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return None

def synthesize_speech(text: str, output_path: str, voice_name: str,
                     speech_key: str, service_region: str) -> bool:
    """
    Performs the actual speech synthesis using Azure Speech SDK.

    Args:
        text: The text to synthesize (already cleaned)
        output_path: Where to save the audio file
        voice_name: The voice to use
        speech_key: Azure Speech subscription key
        service_region: Azure Speech service region

    Returns:
        True if synthesis was successful, False otherwise
    """
    # Note: The text received here should already have "**Problem Statement:***" removed
    logger.debug(f"=== SPEECH SYNTHESIS DETAILS ===")
    logger.debug(f"Service region: {service_region}")
    logger.debug(f"Voice name: {voice_name}")
    logger.debug(f"Output path: {output_path}")
    logger.debug(f"Synthesizing text (first 100 chars): {text[:100]}...") # Log cleaned text

    # Configure speech service
    logger.debug("Creating speech configuration...")
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = voice_name
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    # Create an audio file output for the synthesized speech
    logger.debug("Creating audio output configuration...")
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    # Create a speech synthesizer
    logger.debug("Creating speech synthesizer...")
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # Check if we should use SSML for better pronunciation
    logger.debug("Checking if SSML should be used...")
    use_ssml = should_use_ssml(text)
    logger.debug(f"Use SSML: {use_ssml}")

    # Start synthesis
    logger.debug("Starting speech synthesis...")
    if use_ssml:
        # Wrap the text in SSML for better control over speech synthesis
        ssml = create_ssml(text, voice_name) # create_ssml receives cleaned text
        logger.debug(f"SSML document size: {len(ssml)} characters")
        logger.debug(f"SSML document preview: {ssml[:200]}...")

        logger.debug("Calling speak_ssml_async...")
        result = speech_synthesizer.speak_ssml_async(ssml).get()
    else:
        # Use plain text synthesis for simple content
        logger.debug("Calling speak_text_async...")
        result = speech_synthesizer.speak_text_async(text).get() # speak_text_async receives cleaned text

    # Check the result
    logger.debug(f"Synthesis result reason: {result.reason}")

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        logger.debug(f"Speech synthesis completed successfully")

        # Log audio properties
        audio_data_length = len(result.audio_data) if hasattr(result, 'audio_data') else "unknown"
        logger.debug(f"Audio data size: {audio_data_length}")

        # Check if file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.debug(f"Audio file created with size: {file_size} bytes")
        else:
            logger.error(f"Audio file was not created at {output_path}")

        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        logger.error(f"Speech synthesis canceled: {cancellation_details.reason}")
        logger.debug(f"Cancellation code: {cancellation_details.error_code}")

        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            logger.error(f"Error details: {cancellation_details.error_details}")
        return False
    else:
        logger.warning(f"Unknown result reason: {result.reason}")
        return False

def should_use_ssml(text: str) -> bool:
    """
    Determines if we should use SSML based on text content.

    Args:
        text: The text to analyze
            (already cleaned of "**Problem Statement:***")

    Returns:
        True if SSML would be beneficial, False otherwise
    """
    logger.debug(f"Analyzing text for SSML decision...")

    # Check if text contains math terms, numbers, or special characters that might benefit from SSML
    math_terms = ["fraction", "equation", "sum", "difference", "product", "quotient",
                  "numerator", "denominator", "equal", "×", "÷", "+", "-", "="]

    # Check for numbers followed by mathematical operators
    has_math_expressions = any(term in text.lower() for term in math_terms)
    logger.debug(f"Text contains math terms: {has_math_expressions}")

    # Check if the text is long enough to benefit from prosody control
    is_long_text = len(text) > 200
    logger.debug(f"Text is long (>200 chars): {is_long_text}")

    result = has_math_expressions or is_long_text
    logger.debug(f"Decision to use SSML: {result}")
    return result

def create_ssml(text: str, voice_name: str) -> str:
    """
    Creates SSML markup for the provided text.

    Args:
        text: The text to wrap in SSML
            (already cleaned of "**Problem Statement:***")
        voice_name: The voice to use

    Returns:
        Properly formatted SSML string
    """
    logger.debug(f"Creating SSML document...")

    # Escape any XML special characters in the text
    text = text.replace("&", "&").replace("<", "<").replace(">", ">").replace("'", "'")
    logger.debug(f"Text escaped for XML")

    # Improve pronunciation of mathematical terms
    logger.debug(f"Applying SSML enhancements for mathematical terms...")
    original_text = text # Keep track for logging purposes

    text = text.replace("×", '<say-as interpret-as="characters">×</say-as>')
    text = text.replace("÷", '<say-as interpret-as="characters">÷</say-as>')

    # Replace numbers and fractions with proper SSML
    import re

    # Handle fractions like 1/2, 3/4, etc.
    logger.debug(f"Applying SSML for fractions...")
    fraction_pattern = r"(\d+)/(\d+)"
    text = re.sub(fraction_pattern, r'<say-as interpret-as="fraction">\1/\2</say-as>', text)

    # Handle decimal numbers
    logger.debug(f"Applying SSML for decimals...")
    decimal_pattern = r"(\d+\.\d+)"
    text = re.sub(decimal_pattern, r'<say-as interpret-as="cardinal">\1</say-as>', text)

    # Log how many replacements were made
    if text != original_text:
        logger.debug(f"Applied SSML replacements to text")

    # Create the complete SSML document
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{voice_name}">
            <prosody rate="1.15" pitch="+5%">
                {text}
            </prosody>
        </voice>
    </speak>
    """

    logger.debug(f"SSML document created")
    return ssml.strip()
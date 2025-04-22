"""
Azure Speech Service Integration

This module provides text-to-speech functionality using Azure Speech Services.
It converts text content into natural-sounding speech audio files.
"""

import os
import uuid
import asyncio
import azure.cognitiveservices.speech as speechsdk
from app.core.config import settings
from urllib.parse import urljoin

# Constants
AUDIO_DIR = "static/audio"
AUDIO_FORMAT = "audio-16khz-128kbitrate-mono-mp3"
VOICE_NAME = "en-US-Emma2:DragonHDLatestNeural"
STRING_TO_REMOVE = "**Problem Statement:**" # Define the string to remove

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

    if not text:
        return None

    text = text.replace(STRING_TO_REMOVE, "")

    # Re-check if text became empty after removal
    if not text.strip():
        return None

    # Trim text if it's too long
    if len(text) > 5000:
        text = text[:4997] + "..."

    # Check for required settings
    if not settings.AZURE_SPEECH_SUSCRIPTION_KEY or not settings.AZURE_SPEECH_REGION:
        return None

    # Generate a unique filename for this audio
    filename = f"speech_{uuid.uuid4().hex}.mp3"
    file_path = os.path.join(AUDIO_DIR, filename)

    try:

        audio_result = await asyncio.to_thread(
            synthesize_speech,
            text, # Pass the cleaned text
            file_path,
            voice_name,
            settings.AZURE_SPEECH_SUSCRIPTION_KEY,
            settings.AZURE_SPEECH_REGION
        )

        if audio_result:
            # Construct URL relative to the API server
            relative_url = f"/static/audio/{filename}"
            audio_url = urljoin(settings.BASE_URL, relative_url)

            return audio_url
        else:
            return None
    except Exception as e:
        import traceback
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

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = voice_name
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    # Create an audio file output for the synthesized speech
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

    # Create a speech synthesizer
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    # Check if we should use SSML for better pronunciation
    use_ssml = should_use_ssml(text)

    # Start synthesis
    if use_ssml:
        # Wrap the text in SSML for better control over speech synthesis
        ssml = create_ssml(text, voice_name) # create_ssml receives cleaned text

        result = speech_synthesizer.speak_ssml_async(ssml).get()
    else:
        # Use plain text synthesis for simple content
        result = speech_synthesizer.speak_text_async(text).get() # speak_text_async receives cleaned text

    # Check the result

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:

        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details


        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
        return False
    else:
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

    # Check if text contains math terms, numbers, or special characters that might benefit from SSML
    math_terms = ["fraction", "equation", "sum", "difference", "product", "quotient",
                  "numerator", "denominator", "equal", "×", "÷", "+", "-", "="]

    # Check for numbers followed by mathematical operators
    has_math_expressions = any(term in text.lower() for term in math_terms)

    # Check if the text is long enough to benefit from prosody control
    is_long_text = len(text) > 200

    result = has_math_expressions or is_long_text
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

    # Escape any XML special characters in the text
    text = text.replace("&", "&").replace("<", "<").replace(">", ">").replace("'", "'")

    text = text.replace("×", '<say-as interpret-as="characters">×</say-as>')
    text = text.replace("÷", '<say-as interpret-as="characters">÷</say-as>')

    # Replace numbers and fractions with proper SSML
    import re

    # Handle fractions like 1/2, 3/4, etc.
    fraction_pattern = r"(\d+)/(\d+)"
    text = re.sub(fraction_pattern, r'<say-as interpret-as="fraction">\1/\2</say-as>', text)

    # Handle decimal numbers
    decimal_pattern = r"(\d+\.\d+)"
    text = re.sub(decimal_pattern, r'<say-as interpret-as="cardinal">\1</say-as>', text)

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

    return ssml.strip()
import os
import azure.cognitiveservices.speech as speechsdk

AZURE_SPEECH_SUSCRIPTION_KEY=""
AZURE_SPEECH_REGION=""


# Constants
AUDIO_FORMAT = "audio-16khz-128kbitrate-mono-mp3"
VOICE_NAME = "en-US-SaraNeural"
AUDIO_DIR = "audio_files"  # Directory to save audio files
OUTPUT_FILENAME = "theme.mp3"

# Ensure the audio directory exists
os.makedirs(AUDIO_DIR, exist_ok=True)

def create_ssml(text: str, voice_name: str, style: str = None, style_degree: int = 1) -> str:
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

    # Determine language based on voice name
    lang = "es-ES" if "es-ES" in voice_name else "en-US"
    
    # Build SSML, including mstts namespace if a style is provided
    if style:
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang}">
            <voice name="{voice_name}">
                <mstts:express-as style="{style.lower()}" styledegree="{style_degree}">
                    <prosody rate="1.05" pitch="+0%">
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
                <prosody rate="0.8" pitch="+0%">
                    {text}
                </prosody>
            </voice>
        </speak>
        """

    return ssml.strip()

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

    # Always use SSML when a style is specified
    if style is not None:
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

def main():
    # Your Azure Speech subscription information
    # Replace with your actual key and region
    speech_key = AZURE_SPEECH_SUSCRIPTION_KEY
    service_region = AZURE_SPEECH_REGION
    
    # Text to synthesize
    text = "Choose Your Adventure! Will you explore a Magical School, rule a Royal Kingdom, join Superheroes on exciting missions, or—better yet—create your own adventure? The choice is yours!"
    
    # Output path
    output_path = os.path.join(AUDIO_DIR, OUTPUT_FILENAME)
    
    # Generate speech with a friendly style
    style = "calm"  # Can be: cheerful, empathetic, friendly, etc.
    style_degree = 1    # Style intensity (1-2)
    
    # Call the synthesize function
    success = synthesize_speech(
        text=text,
        output_path=output_path,
        voice_name=VOICE_NAME,
        speech_key=speech_key,
        service_region=service_region,
        style=style,
        style_degree=style_degree
    )
    
    if success:
        print(f"Audio file created successfully at: {output_path}")
    else:
        print("Failed to create audio file")

if __name__ == "__main__":
    main()
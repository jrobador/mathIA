"""
Azure DALL-E 3 Integration

This module provides functionality to generate images using Azure's DALL-E 3 service.
"""

from app.core.config import settings
import aiohttp
import os
import logging
import base64
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_image(prompt: str) -> str | None:
    """
    Generates an image using Azure DALL-E 3 API based on the provided prompt.
    
    Args:
        prompt: The text prompt describing the image to generate
        
    Returns:
        The URL of the generated image, or None if generation failed
    """
    logger.info(f"Generating image with DALL-E 3: {prompt[:50]}...")
    
    # Check if required settings are available
    if not settings.AZURE_DALLE_ENDPOINT or not settings.AZURE_DALLE_API_KEY:
        logger.warning("Azure OpenAI credentials not configured. Cannot generate image.")
        return None
    
    # Prepare the API request
    api_version = "2024-02-01"  # The API version for DALL-E 3
    url = f"{settings.AZURE_DALLE_ENDPOINT}/openai/deployments/dall-e-3/images/generations?api-version={api_version}"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_DALLE_API_KEY
    }
    
    # Prepare the request payload
    payload = {
        "model": "dall-e-3",
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
                    
                    # Extract the image URL from the response
                    if result.get('data') and len(result['data']) > 0:
                        image_url = result['data'][0].get('url')
                        if image_url:
                            logger.info(f"Successfully generated image")
                            return image_url
                        else:
                            # Handle case where image data is base64 encoded
                            image_b64 = result['data'][0].get('b64_json')
                            if image_b64:
                                # Save the image to a file
                                image_path = save_base64_image(image_b64, prompt)
                                logger.info(f"Saved generated image to {image_path}")
                                
                                # Convert to a URL relative to the API server
                                relative_url = f"/static/images/{os.path.basename(image_path)}"
                                full_url = urljoin(settings.BASE_URL, relative_url)
                                return full_url
                    
                    # If we got here, we couldn't find the image data
                    logger.error(f"No image URL found in the response")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"Error generating image. Status: {response.status}, Response: {error_text}")
                    return None
    except Exception as e:
        logger.error(f"Exception during image generation: {str(e)}")
        return None

def save_base64_image(b64_data: str, prompt: str) -> str:
    """
    Saves a base64 encoded image to a file.
    
    Args:
        b64_data: Base64 encoded image data
        prompt: The prompt used to generate the image (used for filename)
        
    Returns:
        The path to the saved image file
    """
    # Create directory if it doesn't exist
    os.makedirs("static/images", exist_ok=True)
    
    # Create a unique filename based on a hash of the prompt
    import hashlib
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
    filename = f"dalle3_{prompt_hash}.png"
    file_path = os.path.join("static/images", filename)
    
    # Decode and save the image
    try:
        image_data = base64.b64decode(b64_data)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        return file_path
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        return None
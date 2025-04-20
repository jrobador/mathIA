"""
Azure DALL-E 3 Integration

This module provides functionality to generate images using Azure's DALL-E 3 service.
"""

from app.core.config import settings
import aiohttp
import os
import logging
import base64
import json
from urllib.parse import urljoin

# Set up logging with more detail
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a file handler for detailed logging
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/azure_image_debug.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Ensure the images directory exists
os.makedirs("static/images", exist_ok=True)

async def generate_image(prompt: str) -> str | None:
    """
    Generates an image using Azure DALL-E 3 API based on the provided prompt.
    
    Args:
        prompt: The text prompt describing the image to generate
        
    Returns:
        The URL of the generated image, or None if generation failed
    """
    logger.debug(f"=== STARTING IMAGE GENERATION ===")
    logger.debug(f"Full prompt: {prompt}")
    logger.debug(f"Azure DALLE endpoint: {settings.AZURE_DALLE_ENDPOINT}")
    
    # Check if required settings are available
    if not settings.AZURE_DALLE_ENDPOINT or not settings.AZURE_DALLE_API_KEY:
        logger.warning("Azure OpenAI credentials not configured. Cannot generate image.")
        return None
    
    # Prepare the API request
    api_version = "2024-02-01"  # The API version for DALL-E 3
    url = f"{settings.AZURE_DALLE_ENDPOINT}/openai/deployments/dall-e-3/images/generations?api-version={api_version}"
    logger.debug(f"Request URL: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_DALLE_API_KEY
    }
    logger.debug(f"Request headers: {json.dumps({k: v for k, v in headers.items() if k != 'api-key'})}")
    
    # Prepare the request payload
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": "1024x1024",  # Default size
        "style": "vivid",     # Can be 'vivid' or 'natural'
        "quality": "standard",  # Can be 'standard' or 'hd'
        "n": 1                # Number of images to generate
    }
    logger.debug(f"Request payload: {json.dumps(payload)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.debug("Sending POST request to Azure DALL-E API...")
            async with session.post(url, headers=headers, json=payload) as response:
                logger.debug(f"Response status: {response.status}")
                
                # Log headers for debugging
                resp_headers = dict(response.headers)
                logger.debug(f"Response headers: {json.dumps(resp_headers)}")
                
                if response.status == 200:
                    result = await response.json()
                    logger.debug(f"Response JSON structure: {json.dumps({k: '...' for k in result.keys()})}")
                    
                    # Extract the image URL from the response
                    if result.get('data') and len(result['data']) > 0:
                        data_item = result['data'][0]
                        logger.debug(f"Data item properties: {json.dumps({k: '...' for k in data_item.keys()})}")
                        
                        image_url = data_item.get('url')
                        if image_url:
                            logger.debug(f"Successfully generated image with URL: {image_url}")
                            
                            # Download the image and save it locally
                            logger.debug("Attempting to download and save the image...")
                            image_filename = await download_and_save_image(image_url, prompt)
                            if image_filename:
                                # Return the local URL
                                relative_url = f"/static/images/{image_filename}"
                                full_url = urljoin(settings.BASE_URL, relative_url)
                                logger.debug(f"Final image URL to return: {full_url}")
                                return full_url
                            
                            logger.debug("Fallback to using the original URL")
                            return image_url  # Fallback to the original URL
                        else:
                            # Handle case where image data is base64 encoded
                            logger.debug("No URL found, checking for base64 encoded image data...")
                            image_b64 = data_item.get('b64_json')
                            if image_b64:
                                logger.debug(f"Found base64 encoded image data (length: {len(image_b64)})")
                                # Save the image to a file
                                image_path = save_base64_image(image_b64, prompt)
                                if image_path:
                                    logger.debug(f"Saved base64 encoded image to: {image_path}")
                                    
                                    # Convert to a URL relative to the API server
                                    relative_url = f"/static/images/{os.path.basename(image_path)}"
                                    full_url = urljoin(settings.BASE_URL, relative_url)
                                    logger.debug(f"Final image URL to return: {full_url}")
                                    return full_url
                    
                    # If we got here, we couldn't find the image data
                    logger.error(f"No image URL or base64 data found in the response")
                    logger.debug(f"Full response content: {json.dumps(result)}")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"Error generating image. Status: {response.status}")
                    logger.debug(f"Error response body: {error_text}")
                    return None
    except Exception as e:
        logger.error(f"Exception during image generation: {str(e)}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return None

async def download_and_save_image(image_url: str, prompt: str) -> str | None:
    """
    Downloads an image from a URL and saves it locally.
    
    Args:
        image_url: The URL of the image to download
        prompt: The prompt used to generate the image (used for filename)
        
    Returns:
        The filename of the saved image, or None if download failed
    """
    logger.debug(f"=== DOWNLOADING IMAGE ===")
    logger.debug(f"Image URL: {image_url}")
    
    try:
        # Ensure directory exists
        os.makedirs("static/images", exist_ok=True)
        
        # Create a unique filename based on a hash of the prompt
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png"
        file_path = os.path.join("static/images", filename)
        logger.debug(f"Target file path: {file_path}")
        
        # Download the image
        logger.debug(f"Starting download...")
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                logger.debug(f"Download response status: {response.status}")
                
                if response.status == 200:
                    image_data = await response.read()
                    logger.debug(f"Downloaded image data (size: {len(image_data)} bytes)")
                    
                    # Save the image to file
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    logger.debug(f"Image saved successfully to: {file_path}")
                    
                    # Verify file exists and has content
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        logger.debug(f"Verified file exists with size: {os.path.getsize(file_path)} bytes")
                        return filename
                    else:
                        logger.error(f"File verification failed: exists={os.path.exists(file_path)}, size={os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")
                        return None
                else:
                    logger.error(f"Failed to download image. Status: {response.status}")
                    resp_text = await response.text()
                    logger.debug(f"Error response body: {resp_text}")
                    return None
    except Exception as e:
        logger.error(f"Error downloading and saving image: {str(e)}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
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
    logger.debug(f"=== SAVING BASE64 IMAGE ===")
    logger.debug(f"Base64 data length: {len(b64_data)}")
    
    # Create directory if it doesn't exist
    os.makedirs("static/images", exist_ok=True)
    
    # Create a unique filename based on a hash of the prompt
    import hashlib
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
    filename = f"dalle3_{prompt_hash}.png"
    file_path = os.path.join("static/images", filename)
    logger.debug(f"Target file path: {file_path}")
    
    # Decode and save the image
    try:
        logger.debug("Decoding base64 data...")
        image_data = base64.b64decode(b64_data)
        logger.debug(f"Decoded image data size: {len(image_data)} bytes")
        
        logger.debug("Writing image data to file...")
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Verify file exists and has content
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            logger.debug(f"Verified file exists with size: {os.path.getsize(file_path)} bytes")
            return file_path
        else:
            logger.error(f"File verification failed: exists={os.path.exists(file_path)}, size={os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")
            return None
    except Exception as e:
        logger.error(f"Error saving base64 image: {str(e)}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return None
"""
Azure DALL-E 3 Integration

This module provides functionality to generate images using Azure's DALL-E 3 service.
"""

from app.core.config import settings
import aiohttp
import os
import base64
import json
from urllib.parse import urljoin
import hashlib  # Keep hashlib as it's used for filenames

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
    # Check if required settings are available
    if not settings.AZURE_DALLE_ENDPOINT or not settings.AZURE_DALLE_API_KEY:
        # Consider raising an exception or returning a more specific error if needed
        print("Warning: Azure OpenAI credentials not configured. Cannot generate image.")
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
                    
                    # Extract the image URL or base64 data from the response
                    if result.get('data') and len(result['data']) > 0:
                        data_item = result['data'][0]
                        
                        image_url = data_item.get('url')
                        if image_url:
                            # Attempt to download and save the image locally
                            image_filename = await download_and_save_image(image_url, prompt)
                            if image_filename:
                                # Return the local URL
                                relative_url = f"/static/images/{image_filename}"
                                full_url = urljoin(settings.BASE_URL, relative_url)
                                return full_url
                            
                            # Fallback to using the original URL if download fails
                            return image_url
                        else:
                            # Handle case where image data is base64 encoded
                            image_b64 = data_item.get('b64_json')
                            if image_b64:
                                # Save the image to a file
                                image_path = save_base64_image(image_b64, prompt)
                                if image_path:
                                    # Convert to a URL relative to the API server
                                    relative_url = f"/static/images/{os.path.basename(image_path)}"
                                    full_url = urljoin(settings.BASE_URL, relative_url)
                                    return full_url
                    
                    # If we got here, we couldn't find the image data
                    print(f"Error: No image URL or base64 data found in the response. Full response: {json.dumps(result)}")
                    return None
                else:
                    error_text = await response.text()
                    print(f"Error generating image. Status: {response.status}. Response: {error_text}")
                    return None
    except Exception as e:
        print(f"Exception during image generation: {str(e)}")
        # Optionally re-raise or handle the exception more specifically
        # import traceback
        # print(f"Exception traceback: {traceback.format_exc()}")
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
    try:
        # Ensure directory exists
        image_dir = "static/images"
        os.makedirs(image_dir, exist_ok=True)
        
        # Create a unique filename based on a hash of the prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png"
        file_path = os.path.join(image_dir, filename)
        
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Save the image to file
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Verify file exists and has content
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        return filename
                    else:
                        print(f"Error: File verification failed after download: {file_path}")
                        return None
                else:
                    resp_text = await response.text()
                    print(f"Failed to download image. Status: {response.status}. URL: {image_url}. Response: {resp_text}")
                    return None
    except Exception as e:
        print(f"Error downloading and saving image from {image_url}: {str(e)}")
        # import traceback
        # print(f"Exception traceback: {traceback.format_exc()}")
        return None

def save_base64_image(b64_data: str, prompt: str) -> str | None:
    """
    Saves a base64 encoded image to a file.
    
    Args:
        b64_data: Base64 encoded image data
        prompt: The prompt used to generate the image (used for filename)
        
    Returns:
        The path to the saved image file, or None if saving failed
    """
    try:
        # Create directory if it doesn't exist
        image_dir = "static/images"
        os.makedirs(image_dir, exist_ok=True)
        
        # Create a unique filename based on a hash of the prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:10]
        filename = f"dalle3_{prompt_hash}.png"
        file_path = os.path.join(image_dir, filename)
        
        # Decode and save the image
        image_data = base64.b64decode(b64_data)
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Verify file exists and has content
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        else:
            print(f"Error: File verification failed after saving base64: {file_path}")
            return None
            
    except Exception as e:
        print(f"Error saving base64 image: {str(e)}")
        # import traceback
        # print(f"Exception traceback: {traceback.format_exc()}")
        return None
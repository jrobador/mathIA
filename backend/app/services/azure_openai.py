"""
Azure OpenAI Service Integration

This module provides production-ready integration with Azure OpenAI services
for the math tutoring agent using prompty templates.
"""

import os
import yaml
from app.core.config import settings

# Initialize the client once
llm_client = None

async def initialize_client():
    """
    Initialize the Azure OpenAI client if not already done.
    Uses either API key or Azure AD authentication based on available credentials.
    """
    global llm_client
    if llm_client is not None:
        return llm_client
        
    if settings.API_HOST == "azure" and settings.AZURE_OPENAI_ENDPOINT:
        # Import here to avoid loading these modules unless needed
        from openai import AsyncAzureOpenAI
        from azure.identity import DefaultAzureCredential
        
        try:
            # Configure auth based on available credentials
            if settings.AZURE_OPENAI_API_KEY:
                # API Key authentication
                llm_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                )
                print(f"Initialized Azure OpenAI client with API key")
            elif settings.AZURE_TENANT_ID:
                # Azure AD authentication
                credential = DefaultAzureCredential()
                token = credential.get_token("https://cognitiveservices.azure.com/.default")
                
                llm_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_ad_token=token.token,
                )
                print(f"Initialized Azure OpenAI client with Azure AD authentication")
            else:
                print("Warning: Neither Azure OpenAI API key nor Azure AD credentials are configured.")
        except Exception as e:
            print(f"Error initializing Azure OpenAI client: {e}")
            llm_client = None
    
    return llm_client

class PromptyTemplate:
    def __init__(self, template_path: str):
        """
        Initialize a prompty template from a file.
        
        Args:
            template_path: Path to the prompty template file
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
        Load and parse the prompty template file.
        """
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Split into frontmatter and messages
            parts = template_content.split('---')
            if len(parts) < 3:
                raise ValueError(f"Invalid prompty template format in {self.template_path}")
            
            # Parse YAML frontmatter
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
                    # Save previous section if exists
                    if current_role is not None:
                        self.messages.append({
                            'role': current_role,
                            'content': '\n'.join(current_content).strip()
                        })
                        current_content = []
                    
                    # Start new section
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
            print(f"Error loading prompty template {self.template_path}: {e}")
            raise
    
    def fill_template(self, **kwargs):
        """
        Fill the template with the provided variables.
        
        Args:
            **kwargs: Values for the template variables
            
        Returns:
            List of filled message dictionaries
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
    Invokes the Azure OpenAI LLM using a prompty template.
    
    Args:
        template_path: Path to the prompty template file
        **kwargs: Values for the template variables
        
    Returns:
        Response text from the model
    """
    # Ensure client is initialized
    client = await initialize_client()
    
    if not client:
        raise Exception("LLM client not available. Check Azure OpenAI configuration.")
    
    try:
        # Load and fill the template
        template = PromptyTemplate(template_path)
        messages = template.fill_template(**kwargs)
        
        # Make the API call
        response = await client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error using prompty template {template_path}: {e}")
        raise

async def stream_with_prompty(template_path: str, **kwargs):
    """
    Streams responses from Azure OpenAI using a prompty template.
    
    Args:
        template_path: Path to the prompty template file
        **kwargs: Values for the template variables
        
    Yields:
        Response text chunks as they become available
    """
    # Ensure client is initialized
    client = await initialize_client()
    
    if not client:
        raise Exception("LLM client not available. Check Azure OpenAI configuration.")
    
    try:
        # Load and fill the template
        template = PromptyTemplate(template_path)
        messages = template.fill_template(**kwargs)
        
        # Stream the response
        stream = await client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
            stream=True,
        )
        
        # Yield chunks as they arrive
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        print(f"Error streaming from prompty template {template_path}: {e}")
        raise

# Function to get a list of available prompty templates
def get_available_templates(templates_dir="prompts"):
    """
    Gets a list of available prompty templates.
    
    Args:
        templates_dir: Directory containing prompty templates
        
    Returns:
        Dictionary mapping template names to file paths
    """
    templates = {}
    
    try:
        for filename in os.listdir(templates_dir):
            if filename.endswith(".prompty"):
                filepath = os.path.join(templates_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    parts = content.split('---')
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])
                        name = frontmatter.get('name')
                        if name:
                            templates[name] = filepath
                except Exception as e:
                    print(f"Error parsing template {filepath}: {e}")
    except Exception as e:
        print(f"Error loading templates from {templates_dir}: {e}")
    
    return templates
from app.core.config import settings
from langchain_core.messages import SystemMessage
import asyncio

# Initialize the client once
llm_client = None

async def initialize_client():
    """
    Initialize the Azure OpenAI client if not already done.
    """
    global llm_client
    if llm_client is not None:
        return llm_client
        
    if settings.API_HOST == "azure" and settings.AZURE_OPENAI_ENDPOINT:
        # Import here to avoid loading these modules unless needed
        from langchain_openai import AzureChatOpenAI
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        
        # Configure auth: Choose Key or AAD
        if settings.AZURE_OPENAI_API_KEY:
             llm_client = AzureChatOpenAI(
                 azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                 openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                 azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                 openai_api_key=settings.AZURE_OPENAI_API_KEY,
                 temperature=0.2, # Adjust as needed
             )
             print(f"Initialized Azure OpenAI client with API key")
        elif settings.AZURE_TENANT_ID:
             token_provider = get_bearer_token_provider(
                 DefaultAzureCredential(), 
                 "https://cognitiveservices.azure.com/.default"
             )
             llm_client = AzureChatOpenAI(
                 azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                 openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                 azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                 azure_ad_token_provider=token_provider,
                 temperature=0.2, # Adjust as needed
            )
             print(f"Initialized Azure OpenAI client with AAD auth")
        else:
             print("Warning: Azure OpenAI client not fully configured.")
    
    return llm_client

async def invoke_llm(messages: list, system_prompt: str | None = None) -> str:
    """
    Invokes the Azure OpenAI LLM with the given messages and system prompt.
    """
    # Ensure client is initialized
    client = await initialize_client()
    
    if not client:
        print("LLM client not available, using simulated response")
        return simulate_response(messages, system_prompt)
    
    try:
        # Prepare messages with system prompt if provided
        api_messages = []
        if system_prompt:
            api_messages.append(SystemMessage(content=system_prompt))
        
        # Add the provided messages
        api_messages.extend(messages)
        
        # Call the LLM
        response = await client.ainvoke(api_messages)
        return response.content
        
    except Exception as e:
        print(f"Error invoking LLM: {e}")
        # Return a fallback response
        return simulate_response(messages, system_prompt)

def simulate_response(messages: list, system_prompt: str | None = None) -> str:
    """
    Provides a simulated response for testing when the LLM is not available.
    """
    print(f"--- Simulating LLM Call ---")
    if system_prompt:
        print(f"System: {system_prompt}")
    for msg in messages:
        print(f"{msg.type.capitalize()}: {msg.content}")
    print(f"---------------------------")

    # Get the last message content
    last_message_content = messages[-1].content if messages else ""

    # Generate appropriate simulated responses based on the content
    if "Explícame sobre" in last_message_content:
        topic = messages[0].content.split('sobre ')[-1] if 'sobre ' in messages[0].content else "este tema"
        return f"""
        Claro, vamos a aprender sobre {topic}.
        
        Este concepto es muy importante en matemáticas. Primero, debemos entender que las matemáticas son una forma de entender el mundo a través de patrones y relaciones numéricas.
        
        Cuando trabajamos con {topic}, estamos desarrollando habilidades de razonamiento lógico y resolución de problemas que son útiles en muchas situaciones de la vida real.
        """
    elif "Crea un ejercicio guiado" in last_message_content:
        topic = messages[0].content.split('sobre ')[-1] if 'sobre ' in messages[0].content else "este tema"
        return f"""
        Aquí tienes un ejercicio guiado sobre {topic}:
        
        Imagina que tenemos 5 estrellas y necesitamos dividirlas en grupos iguales.
        ¿Cuántas estrellas tendríamos en cada grupo si formamos 5 grupos?
        
        ===SOLUCIÓN PARA EVALUACIÓN===
        
        Para resolver este problema:
        1. Tenemos 5 estrellas en total
        2. Queremos dividirlas en 5 grupos iguales
        3. Por lo tanto, cada grupo tendrá 5 ÷ 5 = 1 estrella
        
        La respuesta es 1 estrella por grupo.
        """
    elif "Crea un ejercicio independiente" in last_message_content:
        topic = messages[0].content.split('sobre ')[-1] if 'sobre ' in messages[0].content else "este tema"
        return f"""
        Resuelve el siguiente problema sobre {topic}:
        
        Si tienes 12 planetas y los quieres organizar en 3 sistemas solares iguales, ¿cuántos planetas habrá en cada sistema solar?
        
        ===SOLUCIÓN PARA EVALUACIÓN===
        
        Para resolver este problema de división:
        1. Tenemos 12 planetas en total
        2. Queremos dividirlos en 3 sistemas solares iguales
        3. Por lo tanto, cada sistema solar tendrá 12 ÷ 3 = 4 planetas
        
        La respuesta es 4 planetas por sistema solar.
        """
    elif "Evalúa la respuesta" in last_message_content:
        # Extract the student's answer from the message
        student_answer_line = next((line for line in last_message_content.split('\n') if line.startswith("Respuesta del estudiante:")), "")
        student_answer = student_answer_line.split(":")[-1].strip() if student_answer_line else ""
        
        # For simulation, assume common answers are correct
        if student_answer in ["4", "1", "3", "5", "10"]:
            return "[RESULTADO: Correct]\n¡Muy bien! Has entendido correctamente el concepto y has aplicado la operación matemática de forma adecuada."
        elif student_answer.isdigit():
            return "[RESULTADO: Incorrect_Calculation]\nTu enfoque es correcto, pero parece que hubo un pequeño error en el cálculo. Revisa los números una vez más."
        else:
            return "[RESULTADO: Incorrect_Conceptual]\nParece que hay una confusión con el concepto. Recuerda que cuando dividimos, estamos repartiendo cantidades en grupos iguales."
    else:
        return "Lo siento, no estoy seguro de cómo responder a esa pregunta específica. ¿Podrías reformularla o darme más detalles sobre lo que necesitas?"
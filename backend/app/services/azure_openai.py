from app.core.config import settings
import random

# In a real scenario, you'd initialize the AzureChatOpenAI client here
# from langchain_openai import AzureChatOpenAI
# from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# llm_client = None
# if settings.API_HOST == "azure" and settings.AZURE_OPENAI_ENDPOINT:
#     # Configure auth: Choose Key or AAD
#     if settings.AZURE_OPENAI_API_KEY:
#          llm_client = AzureChatOpenAI(
#              azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
#              openai_api_version=settings.AZURE_OPENAI_API_VERSION,
#              azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
#              openai_api_key=settings.AZURE_OPENAI_API_KEY,
#              temperature=0.2, # Adjust as needed
#          )
#     elif settings.AZURE_TENANT_ID:
#          token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
#          llm_client = AzureChatOpenAI(
#              azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
#              openai_api_version=settings.AZURE_OPENAI_API_VERSION,
#              azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
#              azure_ad_token_provider=token_provider,
#              temperature=0.2, # Adjust as needed
#         )
#     else:
#          print("Warning: Azure OpenAI client not fully configured.")


async def invoke_llm(messages: list, system_prompt: str | None = None) -> str:
    """
    Simulates invoking the LLM. Replace with actual client.ainvoke.
    """
    print(f"--- Simulating LLM Call ---")
    if system_prompt:
        print(f"System: {system_prompt}")
    for msg in messages:
        print(f"{msg.type.capitalize()}: {msg.content}")
    print(f"---------------------------")

    # --- SIMULATED RESPONSE ---
    last_message_content = messages[-1].content if messages else ""

    if "Explícame sobre" in last_message_content:
        return f"Claro, hablemos de {messages[0].content.split('sobre ')[-1]} usando el tema '{messages[0].content.split(': ')[-1]}'. [Explicación detallada simulada...]"
    elif "Crea un ejercicio guiado" in last_message_content:
        return f"Aquí tienes un ejercicio guiado sobre {messages[0].content.split('sobre ')[-1]}: [Problema y pasos simulados...] \n===SOLUCIÓN PARA EVALUACIÓN===\n [Solución simulada]"
    elif "Crea un ejercicio independiente" in last_message_content:
        return f"Intenta resolver este problema sobre {messages[0].content.split('sobre ')[-1]}: [Problema simulado...] \n===SOLUCIÓN PARA EVALUACIÓN===\n [Solución simulada]"
    elif "Evalúa la respuesta" in last_message_content:
        # Simulate evaluation based on student answer
        student_answer_line = next((line for line in last_message_content.split('\n') if line.startswith("Respuesta del estudiante:")), "")
        student_answer = student_answer_line.split(":")[-1].strip()
        if "simulada" in student_answer.lower() or random.random() < 0.6: # ~60% chance correct
             return "[RESULTADO: Correct]\n¡Muy bien hecho! [Explicación simulada]"
        elif random.random() < 0.7:
             return "[RESULTADO: Incorrect_Calculation]\nParece que hubo un pequeño error de cálculo. [Explicación simulada]"
        else:
             return "[RESULTADO: Incorrect_Conceptual]\nRevisemos el concepto. [Explicación simulada]"
    else:
        return "Hmm, no estoy seguro de cómo responder a eso en esta simulación."
    # --------------------------

    # --- REAL LLM CALL (Example) ---
    # if not llm_client:
    #     return "Error: LLM client not configured."
    # try:
    #     # Construct messages properly for the API
    #     api_messages = []
    #     if system_prompt:
    #         api_messages.append(SystemMessage(content=system_prompt))
    #     api_messages.extend(messages) # Assumes messages are already in Langchain format

    #     response = await llm_client.ainvoke(api_messages)
    #     return response.content
    # except Exception as e:
    #     print(f"Error invoking LLM: {e}")
    #     return "Error: Could not get response from LLM."
    # -----------------------------
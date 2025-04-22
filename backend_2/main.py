from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import os
from api import http_routes, ws_routes # Make sure ws_routes is imported
from config import API_HOST, API_PORT, DEBUG, ALLOWED_ORIGINS
from agents.learning_agent import AdaptiveLearningAgent

# Asegurar que los directorios de archivos estáticos existen
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/audio", exist_ok=True)

app = FastAPI(
    title="Agente Educativo Adaptativo",
    description="API para un agente educativo adaptativo", # Simplified description
    version="1.0.0"
)

# Configurar CORS para permitir peticiones desde el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar directorio de archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Crear una instancia global del agente
learning_agent = AdaptiveLearningAgent()

# Configurar la aplicación para usar la instancia del agente
app.state.learning_agent = learning_agent

# Incluir routers
app.include_router(http_routes.router)
app.include_router(ws_routes.router) # Include the refactored WebSocket router

@app.get("/")
async def root():
    """
    Endpoint raíz para verificar que el servidor está en funcionamiento
    """
    return {
        "name": "Agente Educativo Adaptativo API",
        "version": "1.0.0",
        "status": "online"
    }

# ----- REMOVED -----
# Define an active WebSocket connections list
# active_connections = {} # REMOVE THIS - Handled in ws_routes.py

# Helper function to broadcast to all connections for a session
# async def broadcast_to_session(session_id: str, message: dict): # REMOVE THIS - Handled in ws_routes.py
#     """
#     Broadcast a message to all WebSocket connections for a session
#     """
#     # ... implementation removed ...
# ----- END REMOVED -----


# Tarea en segundo plano para limpiar sesiones inactivas
@app.on_event("startup")
async def startup_event():
    """
    Inicia tareas en segundo plano al iniciar la aplicación
    """
    # Verify critical directories (Keep this part)
    prompts_dir = os.path.join(os.getcwd(), "prompts")
    print(f"Checking for prompts directory: {prompts_dir}")
    # ... (rest of the prompt directory check logic) ...
    if os.path.exists(prompts_dir):
        prompts_files = [f for f in os.listdir(prompts_dir) if f.endswith('.prompty')]
        print(f"Found {len(prompts_files)} prompty files: {prompts_files}")

    # Imprimir información sobre la configuración (Keep this part)
    from config import OPENAI_AVAILABLE, DALLE_AVAILABLE, SPEECH_AVAILABLE
    print(f"Iniciando API con servicios - OpenAI: {OPENAI_AVAILABLE}, DALL-E: {DALLE_AVAILABLE}, Speech: {SPEECH_AVAILABLE}")

    # Iniciar tarea de limpieza de sesiones (Keep this part)
    # Ensure the agent instance is accessible via app.state here
    asyncio.create_task(cleanup_sessions_task(app)) # Pass app instance if needed

async def cleanup_sessions_task(app_instance: FastAPI): # Accept app instance
    """
    Tarea periódica para limpiar sesiones inactivas
    """
    while True:
        # Limpiar sesiones cada 15 minutos
        await asyncio.sleep(15 * 60) # Use a variable from config?

        try:
            # Access agent via the passed app instance's state
            agent: AdaptiveLearningAgent = app_instance.state.learning_agent
            cleaned = agent.cleanup_inactive_sessions()
            if cleaned > 0:
                print(f"Limpieza programada: {cleaned} sesiones inactivas eliminadas")
            else:
                print("Limpieza programada: No sesiones inactivas encontradas.")
        except AttributeError:
             print("Error en limpieza de sesiones: No se pudo acceder al agente en app.state.")
        except Exception as e:
            print(f"Error en limpieza de sesiones: {e}")

if __name__ == "__main__":
    """
    Punto de entrada para ejecutar la aplicación directamente
    """
    uvicorn.run(
        "main:app", # Reference the FastAPI app object
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        # Consider adding log_level="info" for more Uvicorn details
    )
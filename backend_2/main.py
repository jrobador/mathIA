from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import uuid
import os
from api import http_routes, ws_routes
from config import API_HOST, API_PORT, DEBUG, ALLOWED_ORIGINS
from agents.learning_agent import AdaptiveLearningAgent

# Asegurar que los directorios de archivos estáticos existen
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/audio", exist_ok=True)

app = FastAPI(
    title="Agente Educativo Adaptativo",
    description="API para un agente educativo adaptativo con human-in-the-loop",
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
app.include_router(ws_routes.router)

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

# Tarea en segundo plano para limpiar sesiones inactivas
@app.on_event("startup")
async def startup_event():
    """
    Inicia tareas en segundo plano al iniciar la aplicación
    """
    # Imprimir información sobre la configuración
    from config import OPENAI_AVAILABLE, DALLE_AVAILABLE, SPEECH_AVAILABLE
    print(f"Iniciando API con servicios - OpenAI: {OPENAI_AVAILABLE}, DALL-E: {DALLE_AVAILABLE}, Speech: {SPEECH_AVAILABLE}")
    
    # Iniciar tarea de limpieza de sesiones
    asyncio.create_task(cleanup_sessions_task())

async def cleanup_sessions_task():
    """
    Tarea periódica para limpiar sesiones inactivas
    """
    while True:
        # Limpiar sesiones cada 15 minutos
        await asyncio.sleep(15 * 60)
        
        try:
            # Limpiar sesiones inactivas
            cleaned = app.state.learning_agent.cleanup_inactive_sessions()
            print(f"Limpieza programada: {cleaned} sesiones inactivas eliminadas")
        except Exception as e:
            print(f"Error en limpieza de sesiones: {e}")

if __name__ == "__main__":
    """
    Punto de entrada para ejecutar la aplicación directamente
    """
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG
    )
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import json
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

# Define an active WebSocket connections list
active_connections = {}

@app.websocket("/ws/new_session")
async def websocket_new_session(websocket: WebSocket):
    """
    WebSocket endpoint for creating a new session
    """
    await websocket.accept()
    print("New WebSocket connection accepted for new_session")
    
    try:
        # Wait for client request
        data = await websocket.receive_text()
        print(f"Received data on new_session WebSocket: {data}")
        
        # Parse the request data
        request_data = json.loads(data)
        
        if request_data.get("action") == "create_session":
            session_data = request_data.get("data", {})
            
            # Extract session params
            topic_id = session_data.get("topic_id", "fractions_introduction")
            personalized_theme = session_data.get("personalized_theme", "space")
            user_id = session_data.get("user_id")
            initial_mastery = float(session_data.get("initial_mastery", 0.0))
            
            try:
                # Create session
                session_id, result = await app.state.learning_agent.create_session(
                    topic_id=topic_id,
                    personalized_theme=personalized_theme,
                    initial_mastery=initial_mastery,
                    user_id=user_id
                )
                
                # Send response back to client
                await websocket.send_json({
                    "type": "session_created",
                    "data": {
                        "session_id": session_id,
                        "result": result
                    }
                })
                
                print(f"WebSocket session created: {session_id}")
            except Exception as e:
                print(f"Error creating session via WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
        elif request_data.get("action") == "get_roadmaps":
            # Get available roadmaps
            roadmaps = app.state.learning_agent.get_available_roadmaps()
            await websocket.send_json({
                "type": "roadmaps_list",
                "data": roadmaps
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid action"
            })
    except WebSocketDisconnect:
        print("WebSocket disconnected during new_session")
    except Exception as e:
        print(f"Error in new_session WebSocket: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Clean up
        if websocket.client_state.CONNECTED:
            await websocket.close()
        print("WebSocket connection for new_session closed")

@app.websocket("/ws/session/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for an existing session
    """
    await websocket.accept()
    print(f"WebSocket connection accepted for session {session_id}")
    
    # Create a unique connection ID
    connection_id = f"{session_id}_{len(active_connections.get(session_id, []))}"
    
    # Add connection to active connections
    if session_id not in active_connections:
        active_connections[session_id] = {}
    active_connections[session_id][connection_id] = websocket
    
    try:
        # Check if session exists
        session_state = app.state.learning_agent.get_session_state(session_id)
        if not session_state:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            return
        
        # Send initial state
        await websocket.send_json({
            "type": "state_update",
            "data": session_state
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            print(f"Received data on session WebSocket: {data}")
            
            # Parse the request data
            request_data = json.loads(data)
            action = request_data.get("action")
            request_id = request_data.get("requestId")
            
            if action == "submit_answer":
                answer = request_data.get("data", {}).get("answer", "")
                try:
                    # Process answer
                    result = await app.state.learning_agent.process_user_input(
                        session_id=session_id,
                        user_input=answer
                    )
                    
                    # Send response
                    await websocket.send_json({
                        "type": "agent_response",
                        "requestId": request_id,
                        "data": result
                    })
                    
                    # Process next step if not waiting for input
                    next_result = result.get("next_action")
                    if next_result and not result.get("waiting_for_input", False):
                        next_step = await app.state.learning_agent.process_step(session_id)
                        await websocket.send_json({
                            "type": "agent_response",
                            "data": next_step
                        })
                except Exception as e:
                    print(f"Error processing answer: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "requestId": request_id,
                        "message": str(e)
                    })
            elif action == "get_state":
                try:
                    # Get session state
                    state = app.state.learning_agent.get_session_state(session_id)
                    await websocket.send_json({
                        "type": "state_update",
                        "requestId": request_id,
                        "data": state
                    })
                except Exception as e:
                    print(f"Error getting state: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "requestId": request_id,
                        "message": str(e)
                    })
            elif action == "continue":
                try:
                    # Process next step
                    result = await app.state.learning_agent.process_step(session_id)
                    await websocket.send_json({
                        "type": "agent_response",
                        "requestId": request_id,
                        "data": result
                    })
                except Exception as e:
                    print(f"Error continuing session: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "requestId": request_id,
                        "message": str(e)
                    })
            elif action == "ping":
                # Simple ping-pong
                await websocket.send_json({
                    "type": "pong",
                    "requestId": request_id,
                    "timestamp": request_data.get("timestamp", 0)
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "requestId": request_id,
                    "message": f"Unknown action: {action}"
                })
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"Error in session WebSocket: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Remove connection from active connections
        if session_id in active_connections and connection_id in active_connections[session_id]:
            del active_connections[session_id][connection_id]
            if not active_connections[session_id]:
                del active_connections[session_id]
        
        # Close the WebSocket if still connected
        if websocket.client_state.CONNECTED:
            await websocket.close()
        
        print(f"WebSocket connection for session {session_id} closed")

# Helper function to broadcast to all connections for a session
async def broadcast_to_session(session_id: str, message: dict):
    """
    Broadcast a message to all WebSocket connections for a session
    """
    if session_id in active_connections:
        for websocket in active_connections[session_id].values():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to session {session_id}: {e}")

# Tarea en segundo plano para limpiar sesiones inactivas
@app.on_event("startup")
async def startup_event():
    """
    Inicia tareas en segundo plano al iniciar la aplicación
    """
    # Verify critical directories
    prompts_dir = os.path.join(os.getcwd(), "prompts")
    print(f"Checking for prompts directory: {prompts_dir}")
    if not os.path.exists(prompts_dir):
        print(f"WARNING: Prompts directory not found at: {prompts_dir}")
        # Try looking in parent directory (in case running from subdirectory)
        parent_prompts_dir = os.path.join(os.getcwd(), "..", "prompts")
        if os.path.exists(parent_prompts_dir):
            print(f"Found prompts directory in parent directory: {parent_prompts_dir}")
            # Create a symlink for convenience
            try:
                os.symlink(parent_prompts_dir, prompts_dir)
                print(f"Created symlink from {parent_prompts_dir} to {prompts_dir}")
            except Exception as e:
                print(f"Could not create symlink: {e}")
        else:
            print(f"WARNING: Could not find prompts directory in parent directory either")
            print(f"Current working directory: {os.getcwd()}")
            # List all files in current directory to help debugging
            print(f"Files in current directory: {os.listdir(os.getcwd())}")
            # Try to create the directory
            try:
                os.makedirs(prompts_dir, exist_ok=True)
                print(f"Created prompts directory: {prompts_dir}")
                print(f"NOTE: You will need to copy prompt files to this directory")
            except Exception as e:
                print(f"Failed to create prompts directory: {e}")
    
    # List all prompts files found (to verify they're accessible)
    if os.path.exists(prompts_dir):
        prompts_files = [f for f in os.listdir(prompts_dir) if f.endswith('.prompty')]
        print(f"Found {len(prompts_files)} prompty files: {prompts_files}")
    
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
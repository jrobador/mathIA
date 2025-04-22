from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from typing import Dict, Any
import json
import uuid

router = APIRouter()

# Almacenamiento de conexiones activas
active_connections: Dict[str, Dict[str, WebSocket]] = {}

@router.websocket("/ws/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str, request: Request):
    """
    Endpoint WebSocket para una sesión específica
    """
    await websocket.accept()
    
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    # Generar ID de conexión único
    connection_id = str(uuid.uuid4())
    
    # Verificar si la sesión existe
    session_state = learning_agent.get_session_state(session_id)
    if not session_state:
        await websocket.send_json({
            "type": "error",
            "message": f"Sesión {session_id} no encontrada"
        })
        await websocket.close()
        return
    
    # Registrar la conexión
    if session_id not in active_connections:
        active_connections[session_id] = {}
    
    active_connections[session_id][connection_id] = websocket
    
    try:
        # Enviar estado inicial
        await websocket.send_json({
            "type": "state_update",
            "data": session_state
        })
        
        # Procesar un paso si la sesión no está esperando input
        if not session_state.get("waiting_for_input", False):
            result = await learning_agent.process_step(session_id)
            
            # Enviar resultado al cliente
            await websocket.send_json({
                "type": "agent_response",
                "data": result
            })
        
        # Bucle principal para recibir mensajes
        while True:
            # Esperar mensaje del cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action", "")
                
                if action == "submit_answer":
                    # Procesar respuesta del usuario
                    result = await learning_agent.process_user_input(
                        session_id=session_id,
                        user_input=message.get("data", {}).get("answer", "")
                    )
                    
                    # Enviar resultado al cliente
                    await websocket.send_json({
                        "type": "agent_response",
                        "data": result
                    })
                    
                    # Si hay un error, no continuar procesando
                    if "error" in result:
                        continue
                    
                    # Procesar siguiente paso automáticamente si no está esperando input
                    if not result.get("waiting_for_input", False):
                        next_result = await learning_agent.process_step(session_id)
                        
                        # Enviar resultado del siguiente paso
                        await websocket.send_json({
                            "type": "agent_response",
                            "data": next_result
                        })
                
                elif action == "continue":
                    # Continuar la sesión procesando el siguiente paso
                    result = await learning_agent.process_step(session_id)
                    
                    # Enviar resultado al cliente
                    await websocket.send_json({
                        "type": "agent_response",
                        "data": result
                    })
                
                elif action == "get_state":
                    # Obtener el estado actual de la sesión
                    session_state = learning_agent.get_session_state(session_id)
                    
                    # Enviar estado al cliente
                    await websocket.send_json({
                        "type": "state_update",
                        "data": session_state
                    })
                
                elif action == "ping":
                    # Simple ping-pong para mantener la conexión viva
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp", 0)
                    })
                
                else:
                    # Acción desconocida
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Acción desconocida: {action}"
                    })
            
            except json.JSONDecodeError:
                # Error al decodificar el mensaje
                await websocket.send_json({
                    "type": "error",
                    "message": "Formato de mensaje inválido"
                })
            
            except Exception as e:
                # Error general
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                })
    
    except WebSocketDisconnect:
        # Cliente desconectado
        if session_id in active_connections and connection_id in active_connections[session_id]:
            del active_connections[session_id][connection_id]
            
            # Si no hay más conexiones para esta sesión, eliminar la entrada
            if not active_connections[session_id]:
                del active_connections[session_id]

@router.websocket("/ws/new_session")
async def websocket_new_session_endpoint(websocket: WebSocket, request: Request):
    """
    Endpoint WebSocket para crear una nueva sesión
    """
    await websocket.accept()
    
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    try:
        # Esperar mensaje con datos de la nueva sesión
        data = await websocket.receive_text()
        
        try:
            message = json.loads(data)
            
            if message.get("action") == "create_session":
                # Obtener datos de la solicitud
                session_data = message.get("data", {})
                topic_id = session_data.get("topic_id", "fractions_introduction")
                user_id = session_data.get("user_id")
                initial_mastery = float(session_data.get("initial_mastery", 0.0))
                personalized_theme = session_data.get("personalized_theme", "space")
                
                # Crear nueva sesión
                try:
                    session_id, result = await learning_agent.create_session(
                        topic_id=topic_id,
                        personalized_theme=personalized_theme,
                        initial_mastery=initial_mastery,
                        user_id=user_id
                    )
                    
                    # Enviar datos de la nueva sesión
                    await websocket.send_json({
                        "type": "session_created",
                        "data": {
                            "session_id": session_id,
                            "topic_id": topic_id,
                            "result": result
                        }
                    })
                    
                    # Redirigir a la conexión de sesión
                    await websocket.send_json({
                        "type": "redirect",
                        "url": f"/ws/session/{session_id}"
                    })
                    
                except ValueError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
            elif message.get("action") == "get_roadmaps":
                # Obtener lista de roadmaps disponibles
                roadmaps = learning_agent.get_available_roadmaps()
                
                await websocket.send_json({
                    "type": "roadmaps_list",
                    "data": roadmaps
                })
                
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "Acción no válida para este endpoint"
                })
        
        except json.JSONDecodeError:
            # Error al decodificar el mensaje
            await websocket.send_json({
                "type": "error",
                "message": "Formato de mensaje inválido"
            })
        
        except Exception as e:
            # Error general
            import traceback
            traceback.print_exc()
            await websocket.send_json({
                "type": "error",
                "message": f"Error: {str(e)}"
            })
    
    except WebSocketDisconnect:
        # Cliente desconectado
        pass

# Función para enviar notificaciones a todos los clientes conectados a una sesión
async def broadcast_to_session(session_id: str, message: Dict[str, Any]):
    """
    Envía un mensaje a todos los clientes conectados a una sesión
    
    Args:
        session_id: ID de la sesión
        message: Mensaje a enviar
    """
    if session_id in active_connections:
        for connection in active_connections[session_id].values():
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Ignorar errores al enviar
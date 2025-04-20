"""
Endpoints de la API para gestionar sesiones del tutor de matemáticas.
Define las rutas y handlers para interacción con el agente.
"""
from fastapi import APIRouter, HTTPException, Body, Query, Response, status
from app.schemas.session import (
    StartSessionRequest, StartSessionResponse, 
    ProcessInputRequest, ProcessInputResponse, 
    AgentOutput, DifficultySetting, 
    LearningPath, SessionStatusResponse
)
from app.agent.state import initialize_state
from app.agent.graph import get_compiled_app
from app.agent.diagnostic import create_diagnostic_result_from_json, apply_diagnostic_to_state
from langchain_core.messages import HumanMessage
import time
import uuid
from typing import Dict, Any, Optional

# Crear router
router = APIRouter()

# En producción, usaríamos una base de datos o caché distribuida
# Para este hackathon, usamos memoria en proceso
active_sessions: Dict[str, Dict[str, Any]] = {}

# Para rendimiento, compilamos el grafo una vez
compiled_app = get_compiled_app()

def map_learning_path_to_topic(learning_path: Optional[LearningPath]) -> str:
    """Mapea el camino de aprendizaje seleccionado a un tema inicial."""
    if not learning_path:
        return "fractions_introduction"
        
    path_to_topic = {
        LearningPath.FRACTIONS: "fractions_introduction",
        LearningPath.ADDITION: "addition_introduction",
        LearningPath.SUBTRACTION: "subtraction_introduction",
        LearningPath.MULTIPLICATION: "multiplication_introduction",
        LearningPath.DIVISION: "division_introduction"
    }
    
    return path_to_topic.get(learning_path, "fractions_introduction")

def map_difficulty_to_mastery(difficulty: Optional[DifficultySetting]) -> float:
    """Mapea el nivel de dificultad a un nivel inicial de dominio."""
    if not difficulty:
        return 0.1
        
    difficulty_to_mastery = {
        DifficultySetting.INITIAL: 0.1,
        DifficultySetting.BEGINNER: 0.3,
        DifficultySetting.INTERMEDIATE: 0.5,
        DifficultySetting.ADVANCED: 0.7
    }
    
    return difficulty_to_mastery.get(difficulty, 0.1)

@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest = Body(...)):
    """
    Inicia una nueva sesión de aprendizaje con el agente tutor.
    
    - Genera un ID de sesión único
    - Inicializa el estado con la configuración proporcionada
    - Ejecuta el grafo para obtener el primer mensaje
    
    Returns:
        StartSessionResponse: ID de la sesión y salida inicial del agente
    """
    try:
        # Generar ID único para la sesión
        session_id = str(uuid.uuid4())
        
        # Determinar tema inicial basado en el camino de aprendizaje
        initial_topic = None
        if request.learning_path:
            initial_topic = map_learning_path_to_topic(request.learning_path)
        elif request.config and request.config.initial_topic:
            initial_topic = request.config.initial_topic
        
        # Determinar nivel de dificultad inicial
        initial_difficulty = None
        if request.diagnostic_results:
            initial_difficulty = request.diagnostic_results.recommended_level
        elif request.config and request.config.initial_difficulty:
            initial_difficulty = request.config.initial_difficulty
        
        # Mapear nivel de dificultad a nivel de dominio inicial
        initial_mastery = map_difficulty_to_mastery(initial_difficulty)
        
        # Crear el estado inicial con tema personalizado
        initial_state = initialize_state(personalized_theme=request.personalized_theme)
        
        # Si hay un tema inicial definido, establecerlo
        if initial_topic:
            initial_state["current_topic"] = initial_topic
            # Inicializar mastery para el tema
            initial_state["topic_mastery"] = {initial_topic: initial_mastery}
        
        # Si hay un mensaje inicial del usuario, añadirlo
        if request.initial_message:
            initial_state["messages"] = [HumanMessage(content=request.initial_message)]
        
        # Aplicar configuraciones adicionales si se proporcionan
        if request.config:
            if request.config.initial_cpa_phase:
                initial_state["current_cpa_phase"] = request.config.initial_cpa_phase
        
        # Si hay diagnóstico, aplicarlo al estado
        if request.diagnostic_results:
            diagnostic_dict = request.diagnostic_results.dict()
            diagnostic_obj = create_diagnostic_result_from_json(diagnostic_dict)
            if diagnostic_obj:
                apply_diagnostic_to_state(initial_state, diagnostic_obj)
        
        # Ejecutar el grafo con el estado inicial
        print(f"Starting new session {session_id} with topic: {initial_state['current_topic']}")
        result_state = await compiled_app.ainvoke(initial_state)
        
        # Guardar el estado actualizado
        active_sessions[session_id] = {
            "state": result_state, 
            "created_at": time.time(),
            "last_updated": time.time()
        }
        
        # Si había resultados de diagnóstico, guardarlos también
        if request.diagnostic_results:
            active_sessions[session_id]["diagnostic_results"] = request.diagnostic_results.dict()
        
        # Preparar respuesta
        agent_output = AgentOutput(**result_state.get("current_step_output", {}))
        
        return StartSessionResponse(
            session_id=session_id, 
            initial_output=agent_output,
            status="active"
        )
        
    except Exception as e:
        print(f"Error starting session: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to start session: {str(e)}"
        )

@router.post("/{session_id}/process", response_model=ProcessInputResponse)
async def process_input(
    session_id: str, 
    request: ProcessInputRequest = Body(...),
    response: Response = None
):
    """
    Procesa la entrada del usuario para una sesión activa.
    
    - Verifica que la sesión exista
    - Añade el mensaje del usuario al historial
    - Ejecuta el grafo para obtener la siguiente acción
    
    Args:
        session_id: ID de la sesión
        request: Contiene el mensaje del usuario
        
    Returns:
        ProcessInputResponse: Salida del agente tras procesar la entrada
    """
    # Verificar que la sesión existe
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found. Please start a new session."
        )

    try:
        # Obtener datos de la sesión
        session_data = active_sessions[session_id]
        current_state = session_data["state"]
        
        # Añadir mensaje del usuario al historial
        if "messages" not in current_state:
            current_state["messages"] = []
        
        current_state["messages"].append(HumanMessage(content=request.message))
        
        # Determinar cómo reanudar el grafo
        last_output = current_state.get("current_step_output", {})
        
        # Si el último output requería una respuesta, preparar el estado para evaluación
        if last_output.get("prompt_for_answer", False):
            print(f"User provided answer for session {session_id}. Evaluating...")
            # Asegurar que el siguiente paso sea evaluar la respuesta
            current_state["next"] = "evaluate_answer"
        
        # Ejecutar el grafo con el estado actualizado
        start_time = time.time()
        print(f"Processing input for session {session_id}. Current topic: {current_state.get('current_topic')}")
        
        result_state = await compiled_app.ainvoke(current_state)
        
        # Actualizar datos de la sesión
        session_data["state"] = result_state
        session_data["last_updated"] = time.time()
        
        # Preparar respuesta
        agent_output = AgentOutput(**result_state.get("current_step_output", {}))
        
        # Obtener nivel de dominio actual
        current_topic = result_state.get("current_topic", "")
        mastery_level = result_state.get("topic_mastery", {}).get(current_topic, 0.0)
        
        # Logging para rendimiento
        processing_time = time.time() - start_time
        print(f"Processed input in {processing_time:.2f} seconds")
        
        # Establecer header de tiempo de procesamiento para monitoreo
        if response:
            response.headers["X-Processing-Time"] = f"{processing_time:.2f}"
        
        return ProcessInputResponse(
            session_id=session_id, 
            agent_output=agent_output,
            mastery_level=mastery_level
        )
        
    except Exception as e:
        print(f"Error processing input for session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to process input: {str(e)}"
        )

@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Obtiene el estado actual de una sesión, incluyendo información de progreso.
    
    Args:
        session_id: ID de la sesión
        
    Returns:
        SessionStatusResponse: Información sobre el estado actual de la sesión
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    
    session_data = active_sessions[session_id]
    current_state = session_data["state"]
    
    # Extraer información relevante del estado
    current_topic = current_state.get("current_topic", "")
    topic_mastery = current_state.get("topic_mastery", {})
    current_cpa_phase = current_state.get("current_cpa_phase", "Concrete")
    
    return SessionStatusResponse(
        session_id=session_id,
        current_topic=current_topic,
        mastery_levels=topic_mastery,
        current_cpa_phase=current_cpa_phase,
        is_active=True,
        created_at=session_data.get("created_at"),
        last_updated=session_data.get("last_updated")
    )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: str):
    """
    Finaliza una sesión activa y libera recursos.
    
    Args:
        session_id: ID de la sesión a finalizar
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    
    # En un sistema real, podríamos guardar datos de la sesión para análisis
    print(f"Ending session {session_id}")
    
    # Eliminar la sesión de la memoria
    del active_sessions[session_id]
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{session_id}/feedback", status_code=status.HTTP_202_ACCEPTED)
async def submit_session_feedback(
    session_id: str,
    rating: int = Query(..., ge=1, le=5),
    comments: Optional[str] = Query(None)
):
    """
    Permite al usuario enviar feedback sobre la sesión de aprendizaje.
    
    Args:
        session_id: ID de la sesión
        rating: Valoración numérica (1-5)
        comments: Comentarios opcionales
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    
    # En un sistema real, guardaríamos este feedback en una base de datos
    print(f"Received feedback for session {session_id}: Rating {rating}, Comments: {comments}")
    
    # Añadir el feedback al estado de la sesión para referencia
    session_data = active_sessions[session_id]
    if "feedback" not in session_data:
        session_data["feedback"] = []
    
    session_data["feedback"].append({
        "rating": rating,
        "comments": comments,
        "timestamp": time.time()
    })
    
    return {"message": "Feedback received. Thank you!"}

# Endpoint de limpieza periódica (para mantenimiento)
@router.post("/maintenance/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_inactive_sessions(
    max_age_hours: float = Query(24.0, description="Edad máxima de sesiones en horas")
):
    """
    Endpoint administrativo para limpiar sesiones inactivas.
    
    Args:
        max_age_hours: Edad máxima de sesiones en horas
    
    Returns:
        Dict: Resultado de la limpieza
    """
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    inactive_sessions = []
    for session_id, data in list(active_sessions.items()):
        last_updated = data.get("last_updated", data.get("created_at", 0))
        if now - last_updated > max_age_seconds:
            inactive_sessions.append(session_id)
            del active_sessions[session_id]
    
    return {
        "cleaned_sessions": len(inactive_sessions),
        "remaining_sessions": len(active_sessions)
    }
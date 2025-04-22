from fastapi import APIRouter, HTTPException, Body, Request, Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

router = APIRouter()

class StartSessionRequest(BaseModel):
    """Modelo de petición para iniciar una nueva sesión"""
    topic_id: str = Field("fractions_introduction", description="ID del tema a estudiar")
    user_id: Optional[str] = Field(None, description="ID del usuario (opcional)")
    initial_mastery: float = Field(0.0, ge=0.0, le=1.0, description="Nivel inicial de dominio")
    personalized_theme: str = Field("space", description="Tema de personalización (espacio, océano, etc.)")

class SessionResponse(BaseModel):
    """Modelo de respuesta con información de la sesión"""
    session_id: str
    topic_id: str
    result: Dict[str, Any]
    requires_input: bool

class SubmitAnswerRequest(BaseModel):
    """Modelo de petición para enviar una respuesta del usuario"""
    answer: str = Field(..., description="Respuesta del usuario")

@router.post("/api/sessions", response_model=SessionResponse)
async def create_session(request: Request, body: StartSessionRequest = Body(...)):
    """
    Crea una nueva sesión de aprendizaje
    """
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    try:
        # Crear sesión
        session_id, result = await learning_agent.create_session(
            topic_id=body.topic_id,
            personalized_theme=body.personalized_theme,
            initial_mastery=body.initial_mastery,
            user_id=body.user_id
        )
        
        # Determinar si requiere input
        requires_input = result.get("waiting_for_input", False)
        
        return SessionResponse(
            session_id=session_id,
            topic_id=body.topic_id,
            result=result,
            requires_input=requires_input
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la sesión: {str(e)}")

@router.post("/api/sessions/{session_id}/answer", response_model=Dict[str, Any])
async def submit_answer(
    request: Request,
    session_id: str = Path(..., description="ID de la sesión"),
    body: SubmitAnswerRequest = Body(...)
):
    """
    Envía la respuesta del usuario para evaluación
    """
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    # Verificar que la sesión existe
    if not learning_agent.get_session_state(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    try:
        # Procesar la respuesta
        result = await learning_agent.process_user_input(
            session_id=session_id,
            user_input=body.answer
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Procesar el siguiente paso automáticamente si no está esperando input
        if not result.get("waiting_for_input", False):
            next_result = await learning_agent.process_step(session_id)
            
            # Combinar resultados para la respuesta
            result["next_step"] = next_result
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la respuesta: {str(e)}")

@router.get("/api/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session_state(
    request: Request,
    session_id: str = Path(..., description="ID de la sesión")
):
    """
    Obtiene el estado actual de una sesión
    """
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    # Obtener estado de la sesión
    state = learning_agent.get_session_state(session_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    return state

@router.get("/api/sessions/{session_id}/continue", response_model=Dict[str, Any])
async def continue_session(
    request: Request,
    session_id: str = Path(..., description="ID de la sesión")
):
    """
    Continúa la ejecución de una sesión procesando el siguiente paso
    """
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    # Verificar que la sesión existe
    if not learning_agent.get_session_state(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    try:
        # Procesar el siguiente paso
        result = await learning_agent.process_step(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al continuar la sesión: {str(e)}")

@router.get("/api/roadmaps", response_model=List[Dict[str, Any]])
async def get_roadmaps(request: Request):
    """
    Obtiene la lista de roadmaps de aprendizaje disponibles
    """
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    # Obtener roadmaps
    roadmaps = learning_agent.get_available_roadmaps()
    
    return roadmaps

@router.get("/api/sessions", response_model=List[Dict[str, Any]])
async def get_active_sessions(request: Request):
    """
    Obtiene la lista de sesiones activas
    """
    # Obtener el agente de aprendizaje
    learning_agent = request.app.state.learning_agent
    
    # Obtener sesiones activas
    sessions = learning_agent.get_active_sessions()
    
    return sessions

@router.get("/api/health")
async def health_check():
    """
    Endpoint de verificación de salud del servicio
    """
    return {"status": "ok", "service": "adaptive-learning-agent"}
# app/schemas/session.py - Añadir esquemas para diagnóstico

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from enum import Enum
import time

# --- Enumeraciones adicionales ---

class DifficultySetting(str, Enum):
    INITIAL = "initial"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class LearningPath(str, Enum):
    FRACTIONS = "fractions"
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"

# --- Esquemas de diagnóstico ---

class DiagnosticResult(BaseModel):
    id: int
    correct: bool
    question_type: Optional[str] = None
    concept_tested: Optional[str] = None

class DiagnosticData(BaseModel):
    score: float
    correct_answers: int
    total_questions: int
    recommended_level: DifficultySetting
    question_results: Optional[List[DiagnosticResult]] = None

# --- Actualización de TutorConfig ---

class TutorConfig(BaseModel):
    """Configuración para personalizar el comportamiento del tutor."""
    initial_topic: Optional[str] = None
    initial_cpa_phase: Optional[str] = None
    initial_difficulty: Optional[DifficultySetting] = None
    difficulty_adjustment_rate: Optional[float] = 0.1
    enable_audio: Optional[bool] = True
    enable_images: Optional[bool] = True
    language: Optional[str] = "es"  # Idioma por defecto es español
    diagnostic_score: Optional[float] = None
    diagnostic_details: Optional[List[DiagnosticResult]] = None

# --- Actualización de StartSessionRequest ---

class StartSessionRequest(BaseModel):
    """Solicitud para iniciar una nueva sesión de tutoría."""
    personalized_theme: Optional[str] = "espacio"
    initial_message: Optional[str] = None
    config: Optional[TutorConfig] = None
    diagnostic_results: Optional[DiagnosticData] = None
    learning_path: Optional[LearningPath] = None
    
    class Config:
        schema_extra = {
            "example": {
                "personalized_theme": "espacio",
                "initial_message": "Hola, quiero aprender sobre fracciones",
                "config": {
                    "initial_topic": "fractions_introduction",
                    "initial_cpa_phase": "Concrete",
                    "enable_audio": True
                },
                "learning_path": "addition"
            }
        }

# --- Fin de la actualización de esquemas ---

# app/api/endpoints/session.py - Actualización del endpoint start_session

from fastapi import APIRouter, HTTPException, Body, Depends, Query, Response, status
from app.schemas.session import (
    StartSessionRequest, StartSessionResponse, ProcessInputResponse, 
    AgentOutput, DiagnosticData, DifficultySetting, LearningPath
)
from app.agent.state import initialize_state
from app.agent.graph import get_compiled_app
import time
import uuid

# Función auxiliar para mapear el camino de aprendizaje a un tema inicial
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

# Función auxiliar para mapear el nivel de dificultad a un nivel inicial de dominio
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

# Actualización del endpoint start_session
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
            active_sessions[session_id]["diagnostic_results"] = request.diagnostic_results
        
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
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

# ----- Enums para el modelo -----
class CPAPhase(str, Enum):
    """Enum que representa las fases de enseñanza Concreto-Pictórico-Abstracto."""
    CONCRETE = "Concrete"
    PICTORIAL = "Pictorial"
    ABSTRACT = "Abstract"

class EvaluationOutcome(str, Enum):
    """Enum que representa los posibles resultados de evaluar la respuesta de un estudiante."""
    CORRECT = "Correct"
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual"  # Incorrecto debido a malentendido del concepto
    INCORRECT_CALCULATION = "Incorrect_Calculation"  # Incorrecto debido a un error de cálculo
    UNCLEAR = "Unclear"  # La respuesta o razonamiento no es lo suficientemente claro para evaluar

class Message(BaseModel):
    """Modelo para representar mensajes en la conversación."""
    role: str  # 'human' o 'ai'
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class StudentState(BaseModel):
    """
    Modelo para el estado de una sesión de aprendizaje del estudiante.
    """
    # Información de la sesión
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Estado educativo
    current_topic: str  # ID del tema actual (ej. "fractions_introduction")
    current_cpa_phase: CPAPhase = CPAPhase.CONCRETE
    topic_mastery: Dict[str, float] = {}  # Nivel de dominio (0.0 a 1.0) por ID de tema
    
    # Mensajes
    messages: List[Message] = []
    
    # Seguimiento de progreso
    consecutive_correct: int = 0  # Contador de respuestas correctas consecutivas
    consecutive_incorrect: int = 0  # Contador de respuestas incorrectas consecutivas
    error_feedback_given_count: int = 0  # Cuántas veces se ha proporcionado retroalimentación para el tipo de error actual
    
    # Estado de la última acción/interacción
    last_action_type: Optional[str] = None  # Tipo de la última acción realizada por el agente
    last_evaluation: Optional[EvaluationOutcome] = None  # Resultado de la última evaluación
    last_problem_details: Optional[Dict[str, Any]] = None  # Detalles del último problema presentado
    
    # Para el control de flujo del agente
    waiting_for_input: bool = False  # Indica si el agente está esperando respuesta del usuario
    theory_presented_for_topics: List[str] = []  # Lista de temas para los que ya se ha presentado la teoría
    
    # Personalización
    personalized_theme: str = "space"  # Tema para personalización (ej. "space", "animals")
    
    class Config:
        use_enum_values = True

class AgentOutput(BaseModel):
    """Estructura para la salida del agente hacia el frontend."""
    text: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    prompt_for_answer: bool = False
    evaluation: Optional[EvaluationOutcome] = None
    is_final_step: bool = False

# Funciones auxiliares para trabajar con el estado
def initialize_state(session_id: str, topic_id: str = "fractions_introduction", 
                    personalized_theme: str = "space", user_id: Optional[str] = None) -> StudentState:
    """Inicializa un nuevo estado de sesión con valores predeterminados."""
    return StudentState(
        session_id=session_id,
        user_id=user_id,
        current_topic=topic_id,
        current_cpa_phase=CPAPhase.CONCRETE,
        topic_mastery={topic_id: 0.1},  # Dominio bajo inicial para el tema de inicio
        personalized_theme=personalized_theme,
    )

def get_current_mastery(state: StudentState) -> float:
    """Obtiene el nivel de dominio actual para el tema."""
    return state.topic_mastery.get(state.current_topic, 0.0)

def update_mastery(state: StudentState, delta: float) -> None:
    """
    Actualiza el nivel de dominio del tema actual por un delta dado.
    Asegura que el dominio se mantenga entre 0.0 y 1.0.
    
    Args:
        state: El estado de sesión actual.
        delta: La cantidad para cambiar el dominio (puede ser positiva o negativa).
    """
    current_mastery = state.topic_mastery.get(state.current_topic, 0.0)
    
    # Calcular nuevo dominio, limitando entre 0.0 y 1.0
    new_mastery = max(0.0, min(1.0, current_mastery + delta))
    
    # Actualizar el estado
    state.topic_mastery[state.current_topic] = new_mastery
    state.updated_at = datetime.now()

def add_message(state: StudentState, role: str, content: str) -> None:
    """
    Añade un mensaje al historial de conversación.
    
    Args:
        state: El estado de sesión actual.
        role: El rol del mensaje ('human' o 'ai').
        content: El contenido del mensaje.
    """
    message = Message(role=role, content=content)
    state.messages.append(message)
    state.updated_at = datetime.now()

def get_last_user_message(state: StudentState) -> Optional[Message]:
    """
    Obtiene el último mensaje del usuario.
    
    Args:
        state: El estado de sesión actual.
        
    Returns:
        El último mensaje del usuario o None si no hay ninguno.
    """
    for message in reversed(state.messages):
        if message.role == "human":
            return message
    return None
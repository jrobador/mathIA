from typing import Dict, List, Any, Optional, TypedDict, Union
from enum import Enum
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# ----- Enums para el modelo -----
class CPAPhase(str, Enum):
    CONCRETE = "Concrete"
    PICTORIAL = "Pictorial"
    ABSTRACT = "Abstract"

class EvaluationOutcome(str, Enum):
    CORRECT = "Correct"
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual"
    INCORRECT_CALCULATION = "Incorrect_Calculation"
    UNCLEAR = "Unclear"

# ----- Estado del Agente -----
class StudentSessionState(TypedDict, total=False):
    # Historial de mensajes (Langchain format)
    messages: List[Union[HumanMessage, AIMessage, SystemMessage]]

    # Estado educativo
    current_topic: str
    current_cpa_phase: str  # Usando string en lugar de enum para ser compatible con JSON
    topic_mastery: Dict[str, float]  # Dominio por tema

    # Tracking de progreso
    consecutive_correct: int
    consecutive_incorrect: int
    error_feedback_given_count: int

    # Estado de la última acción
    last_action_type: Optional[str]
    last_evaluation: Optional[str]  # Usando string en lugar de enum
    last_problem_details: Optional[Dict[str, Any]]

    # Salida del paso actual (será enviada al frontend via API response)
    current_step_output: Dict[str, Any]

    # Personalización del estudiante
    personalized_theme: str
    
    # Para el flujo condicional del grafo
    next: Optional[str]

# Funciones auxiliares para trabajar con el estado
def initialize_state(personalized_theme: str = "espacio") -> StudentSessionState:
    """Inicializa un nuevo estado de sesión con valores por defecto."""
    return {
        "messages": [],
        "current_topic": "fractions_introduction",
        "current_cpa_phase": "Concrete",
        "topic_mastery": {"fractions_introduction": 0.1},
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "error_feedback_given_count": 0,
        "last_action_type": None,
        "last_evaluation": None,
        "last_problem_details": None,
        "current_step_output": {},
        "personalized_theme": personalized_theme,
        "next": None
    }

def get_current_mastery(state: StudentSessionState) -> float:
    """Obtiene el nivel de dominio actual del tema."""
    current_topic = state.get("current_topic", "fractions_introduction")
    return state.get("topic_mastery", {}).get(current_topic, 0.0)

def update_mastery(state: StudentSessionState, delta: float) -> None:
    """Actualiza el nivel de dominio del tema actual."""
    current_topic = state.get("current_topic", "fractions_introduction")
    
    if "topic_mastery" not in state:
        state["topic_mastery"] = {}
    
    current_mastery = state["topic_mastery"].get(current_topic, 0.0)
    new_mastery = max(0.0, min(1.0, current_mastery + delta))
    state["topic_mastery"][current_topic] = new_mastery
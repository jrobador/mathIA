from typing import Dict, List, Any, Optional, TypedDict
from enum import Enum
from langchain_core.messages import  BaseMessage

# ----- Enums y tipos para el modelo -----
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
# Use TypedDict for LangGraph state compatibility if needed, or stick to BaseModel
class StudentSessionState(TypedDict):
    # Historial de mensajes (Langchain format)
    messages: List[BaseMessage]

    # Estado educativo
    current_topic: str
    current_cpa_phase: CPAPhase
    topic_mastery: Dict[str, float] # Dominio por tema

    # Tracking de progreso
    consecutive_correct: int
    consecutive_incorrect: int
    error_feedback_given_count: int

    # Estado de la última acción
    last_action_type: Optional[str]
    last_evaluation: Optional[EvaluationOutcome]
    last_problem_details: Optional[Dict[str, Any]] # Needs optional

    # Salida del paso actual (será enviada al frontend via API response)
    current_step_output: Dict[str, Any] # Matches AgentOutput schema structure

    # Personalización del estudiante
    personalized_theme: str

    # Helper method (not directly part of TypedDict state, but useful logic)
    # Moved logic to where state is accessed/updated in nodes
"""
Esquemas Pydantic para las sesiones del tutor de matemáticas.
Define los modelos de datos utilizados en la API.
"""
from pydantic import BaseModel
from typing import Optional, Dict, List
from enum import Enum

# --- Enumeraciones ---

class CPAPhase(str, Enum):
    CONCRETE = "Concrete"
    PICTORIAL = "Pictorial"
    ABSTRACT = "Abstract"

class EvaluationOutcome(str, Enum):
    CORRECT = "Correct"
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual"
    INCORRECT_CALCULATION = "Incorrect_Calculation"
    UNCLEAR = "Unclear"

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

# --- Configuración del tutor ---

class TutorConfig(BaseModel):
    """Configuración para personalizar el comportamiento del tutor."""
    initial_topic: Optional[str] = None
    initial_cpa_phase: Optional[CPAPhase] = None
    initial_difficulty: Optional[DifficultySetting] = None
    difficulty_adjustment_rate: Optional[float] = 0.1
    enable_audio: Optional[bool] = True
    enable_images: Optional[bool] = True
    language: Optional[str] = "es"  # Idioma por defecto es español
    diagnostic_score: Optional[float] = None
    diagnostic_details: Optional[List[DiagnosticResult]] = None
    
    class Config:
        use_enum_values = True  # Para serializar enums como sus valores string

# --- Esquemas de Solicitud ---

class StartSessionRequest(BaseModel):
    """Solicitud para iniciar una nueva sesión de tutoría."""
    personalized_theme: Optional[str] = "espacio"
    initial_message: Optional[str] = None
    config: Optional[TutorConfig] = None
    diagnostic_results: Optional[DiagnosticData] = None
    learning_path: Optional[LearningPath] = None
    
    class Config:
        use_enum_values = True
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

class ProcessInputRequest(BaseModel):
    """Solicitud para procesar la entrada del usuario en una sesión activa."""
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Creo que la respuesta es 3/4"
            }
        }

# --- Esquemas de Respuesta ---

class FeedbackDetails(BaseModel):
    """Detalles de retroalimentación específica."""
    type: Optional[str] = None  # Tipo de feedback (correcto, incorrecto, etc.)
    message: Optional[str] = None  # Mensaje detallado
    
    class Config:
        schema_extra = {
            "example": {
                "type": "error_conceptual",
                "message": "Parece que hay una confusión con el concepto de denominador."
            }
        }

class AgentOutput(BaseModel):
    """Estructura de salida del agente para el frontend."""
    text: Optional[str] = None  # Texto principal de la respuesta
    image_url: Optional[str] = None  # URL de imagen generada (si hay)
    audio_url: Optional[str] = None  # URL de audio generado (si hay)
    feedback: Optional[FeedbackDetails] = None  # Detalles de feedback específicos
    prompt_for_answer: Optional[bool] = False  # Indica si espera respuesta
    evaluation: Optional[EvaluationOutcome] = None  # Resultado de evaluación (si aplica)
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "text": "Vamos a aprender sobre fracciones. Una fracción representa una parte de un todo...",
                "image_url": "https://example.com/images/fractions.png",
                "audio_url": "https://example.com/audio/explanation.mp3",
                "prompt_for_answer": True
            }
        }

class StartSessionResponse(BaseModel):
    """Respuesta a la solicitud de inicio de sesión."""
    session_id: str  # ID único de la sesión
    initial_output: AgentOutput  # Primera salida del agente
    status: str = "active"  # Estado de la sesión
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "initial_output": {
                    "text": "¡Hola! Vamos a aprender sobre fracciones...",
                    "image_url": "https://example.com/images/welcome.png"
                },
                "status": "active"
            }
        }

class ProcessInputResponse(BaseModel):
    """Respuesta a la solicitud de procesamiento de entrada."""
    session_id: str  # ID de la sesión
    agent_output: AgentOutput  # Salida del agente tras procesar la entrada
    mastery_level: Optional[float] = None  # Nivel de dominio actual (0-1)
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_output": {
                    "text": "¡Muy bien! Tu respuesta es correcta...",
                    "prompt_for_answer": False
                },
                "mastery_level": 0.6
            }
        }

class SessionStatusResponse(BaseModel):
    """Respuesta con el estado actual de la sesión."""
    session_id: str
    current_topic: str
    mastery_levels: Dict[str, float]
    current_cpa_phase: CPAPhase
    is_active: bool
    created_at: Optional[float] = None
    last_updated: Optional[float] = None
    
    class Config:
        use_enum_values = True
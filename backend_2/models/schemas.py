from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from enum import Enum

class SessionStartRequest(BaseModel):
    topic_id: str = Field(..., description="ID del tema a estudiar")
    user_id: Optional[str] = Field(None, description="ID del usuario (opcional)")
    initial_mastery: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Nivel inicial de dominio")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")

class SubmitAnswerRequest(BaseModel):
    answer: str = Field(..., description="Respuesta del usuario")
    problem_id: Optional[str] = Field(None, description="ID del problema (si aplica)")
    time_taken: Optional[int] = Field(None, description="Tiempo en segundos que tomó responder")

class MessageType(str, Enum):
    THEORY = "THEORY"
    GUIDED_PRACTICE = "GUIDED_PRACTICE"
    INDEPENDENT_PRACTICE = "INDEPENDENT_PRACTICE"
    FEEDBACK = "FEEDBACK"
    EVALUATION = "EVALUATION"
    SYSTEM = "SYSTEM"
    ERROR = "ERROR"

class AgentMessage(BaseModel):
    type: MessageType
    content: Dict[str, Any]
    requires_input: bool = Field(False, description="Indica si requiere respuesta del usuario")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Datos para visualización")

class ClientMessage(BaseModel):
    action: str = Field(..., description="Acción solicitada (submit_answer, request_hint, etc.)")
    data: Dict[str, Any] = Field(..., description="Datos asociados a la acción")

class SessionState(BaseModel):
    session_id: str
    topic_id: str
    mastery: float
    waiting_for_input: bool
    current_phase: str
    timestamp: str
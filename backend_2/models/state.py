from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class EvaluationResult(str, Enum):
    CORRECT = "CORRECT"
    INCORRECT_CONCEPTUAL = "INCORRECT_CONCEPTUAL"
    INCORRECT_CALCULATION = "INCORRECT_CALCULATION"

class AgentState(BaseModel):
    """Modelo del estado del agente educativo adaptativo"""
    
    # Identificadores
    session_id: str
    topic_id: str = Field(..., description="ID del tema actual")
    
    # Métricas de progreso
    mastery: float = Field(0.0, ge=0.0, le=1.0, description="Nivel de dominio del tema actual (0-1)")
    consecutive_correct: int = Field(0, ge=0, description="Respuestas correctas consecutivas")
    consecutive_incorrect: int = Field(0, ge=0, description="Respuestas incorrectas consecutivas")
    error_feedback_count: int = Field(0, ge=0, description="Contador de retroalimentaciones dadas")
    
    # Estado de la instrucción
    theory_presented: bool = Field(False, description="Indica si ya se presentó la teoría")
    last_eval: Optional[EvaluationResult] = Field(None, description="Resultado de la última evaluación")
    
    # Control de flujo
    waiting_for_input: bool = Field(False, description="Indica si el agente está esperando respuesta")
    next_action: Optional[str] = Field(None, description="Próxima acción a ejecutar")
    
    # Detalles del problema actual
    last_problem_details: Optional[Dict] = Field(None, description="Detalles del último problema presentado")
    last_answer: Optional[str] = Field(None, description="Última respuesta del usuario")
    
    # Historial
    interaction_history: List[Dict] = Field(default_factory=list, description="Historial de interacciones")
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def update(self, **kwargs):
        """Actualiza el estado y marca la hora de actualización"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.now()
        return self
        
    def log_interaction(self, action: str, content: Dict):
        """Registra una interacción en el historial"""
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "content": content
        })
        self.updated_at = datetime.now()
"""
Utilidades para procesar resultados de diagnóstico y adaptar el estado del agente.

Este módulo contiene funciones para interpretar los resultados del diagnóstico
inicial y configurar el estado de aprendizaje del estudiante en consecuencia.
"""

from typing import Dict, List, Any, Optional
from enum import Enum

class DifficultySetting(str, Enum):
    INITIAL = "initial"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class DiagnosticResult:
    """Representa el resultado de un diagnóstico completo."""
    def __init__(
        self,
        score: float,
        correct_answers: int,
        total_questions: int,
        recommended_level: DifficultySetting,
        question_results: Optional[List[Dict[str, Any]]] = None
    ):
        self.score = score
        self.correct_answers = correct_answers
        self.total_questions = total_questions
        self.recommended_level = recommended_level
        self.question_results = question_results or []
    
    @property
    def percent_correct(self) -> float:
        """Retorna el porcentaje de respuestas correctas."""
        if not self.total_questions:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100
    
    def get_strengths(self) -> List[str]:
        """Identifica los puntos fuertes basados en las respuestas correctas."""
        if not self.question_results:
            return []
        
        strengths = {}
        for question in self.question_results:
            if question.get("correct", False) and "concept_tested" in question:
                concept = question["concept_tested"]
                strengths[concept] = strengths.get(concept, 0) + 1
        
        # Retornar conceptos con más de una respuesta correcta
        return [concept for concept, count in strengths.items() if count > 0]
    
    def get_weaknesses(self) -> List[str]:
        """Identifica los puntos débiles basados en las respuestas incorrectas."""
        if not self.question_results:
            return []
        
        weaknesses = {}
        for question in self.question_results:
            if not question.get("correct", True) and "concept_tested" in question:
                concept = question["concept_tested"]
                weaknesses[concept] = weaknesses.get(concept, 0) + 1
        
        # Retornar todos los conceptos con respuestas incorrectas
        return [concept for concept, count in weaknesses.items() if count > 0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a un diccionario."""
        return {
            "score": self.score,
            "correct_answers": self.correct_answers,
            "total_questions": self.total_questions,
            "recommended_level": self.recommended_level,
            "percent_correct": self.percent_correct,
            "strengths": self.get_strengths(),
            "weaknesses": self.get_weaknesses(),
            "question_results": self.question_results
        }

def difficulty_to_mastery_level(difficulty: DifficultySetting) -> float:
    """
    Convierte un nivel de dificultad a un nivel de dominio inicial.
    
    Args:
        difficulty: Nivel de dificultad recomendado
    
    Returns:
        Nivel de dominio inicial (0-1)
    """
    mapping = {
        DifficultySetting.INITIAL: 0.1,
        DifficultySetting.BEGINNER: 0.3,
        DifficultySetting.INTERMEDIATE: 0.5,
        DifficultySetting.ADVANCED: 0.7
    }
    return mapping.get(difficulty, 0.1)

def apply_diagnostic_to_state(state: Dict[str, Any], diagnostic: DiagnosticResult) -> Dict[str, Any]:
    """
    Aplica los resultados del diagnóstico al estado del estudiante.
    
    Args:
        state: Estado actual del estudiante
        diagnostic: Resultados del diagnóstico
    
    Returns:
        Estado actualizado
    """
    # Obtener nivel de dominio basado en la dificultad recomendada
    mastery_level = difficulty_to_mastery_level(diagnostic.recommended_level)
    
    # Actualizar topic_mastery para el tema actual
    current_topic = state.get("current_topic", "fractions_introduction")
    if "topic_mastery" not in state:
        state["topic_mastery"] = {}
    
    state["topic_mastery"][current_topic] = mastery_level
    
    # Ajustar fase CPA según nivel
    if mastery_level < 0.3:
        state["current_cpa_phase"] = "Concrete"
    elif mastery_level < 0.6:
        state["current_cpa_phase"] = "Pictorial"
    else:
        state["current_cpa_phase"] = "Abstract"
    
    # Guardar información de diagnóstico en el estado
    state["diagnostic_results"] = diagnostic.to_dict()
    
    return state

def create_diagnostic_result_from_json(data: Dict[str, Any]) -> Optional[DiagnosticResult]:
    """
    Crea un objeto DiagnosticResult a partir de datos JSON.
    
    Args:
        data: Diccionario con datos del diagnóstico
    
    Returns:
        DiagnosticResult o None si los datos son inválidos
    """
    if not isinstance(data, dict):
        return None
    
    try:
        score = float(data.get("score", 0.0))
        correct_answers = int(data.get("correct_answers", 0))
        total_questions = int(data.get("total_questions", 0))
        
        # Convertir nivel recomendado a enum
        level_str = data.get("recommended_level", "initial")
        try:
            recommended_level = DifficultySetting(level_str)
        except ValueError:
            recommended_level = DifficultySetting.INITIAL
        
        question_results = data.get("question_results", [])
        
        return DiagnosticResult(
            score=score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            recommended_level=recommended_level,
            question_results=question_results
        )
    except (ValueError, TypeError):
        return None
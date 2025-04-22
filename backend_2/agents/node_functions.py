from typing import Dict, Any, Optional
from models.state import AgentState, EvaluationResult
import random
import json
from utils.visualization import generate_visual

# Funciones de nodos para el diagrama de flujo del agente

def determine_next_step(state: AgentState) -> Dict[str, Any]:
    """
    Determina el próximo paso basado en el estado actual
    """
    # Si está esperando input, debe pausar
    if state.waiting_for_input:
        return {"action": "pause", "message": "Esperando respuesta del usuario"}
    
    # Lógica de decisión basada en el diagrama de flujo
    if state.mastery < 0.3 and not state.theory_presented:
        state.update(next_action="present_theory")
        return {"action": "continue", "next": "present_theory"}
    
    elif state.mastery < 0.3 and state.theory_presented:
        state.update(next_action="present_guided_practice")
        return {"action": "continue", "next": "present_guided_practice"}
    
    elif 0.3 <= state.mastery <= 0.7:
        state.update(next_action="present_independent_practice")
        return {"action": "continue", "next": "present_independent_practice"}
    
    elif state.last_eval in [EvaluationResult.INCORRECT_CONCEPTUAL, EvaluationResult.INCORRECT_CALCULATION]:
        state.update(next_action="provide_targeted_feedback")
        return {"action": "continue", "next": "provide_targeted_feedback"}
    
    elif state.consecutive_incorrect >= 3:
        state.update(next_action="simplify_instruction")
        return {"action": "continue", "next": "simplify_instruction"}
    
    elif state.mastery > 0.8 and state.consecutive_correct >= 2:
        state.update(next_action="check_advance_topic")
        return {"action": "continue", "next": "check_advance_topic"}
    
    # Por defecto, presentar práctica independiente
    state.update(next_action="present_independent_practice")
    return {"action": "continue", "next": "present_independent_practice"}

def present_theory(state: AgentState, topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Presenta la teoría del tema actual
    """
    theory_content = topic_data.get("theory", {})
    
    # Verificar si se necesita una visualización
    visual_data = None
    if theory_content.get("needs_visual", False):
        visual_data = generate_visual(
            visual_type=theory_content.get("visual_type", "concept"),
            topic_id=state.topic_id,
            content=theory_content
        )
    
    # Actualizar estado
    state.update(
        theory_presented=True,
        next_action=None,
        waiting_for_input=False
    )
    
    state.log_interaction("present_theory", {
        "theory_id": theory_content.get("id"),
        "has_visual": visual_data is not None
    })
    
    return {
        "action": "present_content",
        "content_type": "theory",
        "content": theory_content,
        "visual_data": visual_data
    }

def present_guided_practice(state: AgentState, topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Presenta un ejercicio guiado con más apoyo
    """
    practice_problems = topic_data.get("guided_practice", [])
    
    # Seleccionar un problema apropiado
    problem_idx = min(state.consecutive_incorrect, len(practice_problems) - 1)
    problem = practice_problems[problem_idx]
    
    # Verificar si se necesita una visualización
    visual_data = None
    if problem.get("needs_visual", False):
        visual_data = generate_visual(
            visual_type=problem.get("visual_type", "problem"),
            topic_id=state.topic_id,
            content=problem
        )
    
    # Actualizar estado con detalles del problema actual
    state.update(
        last_problem_details=problem,
        waiting_for_input=True,  # Esperará respuesta
        next_action="evaluate_answer"
    )
    
    state.log_interaction("present_guided_practice", {
        "problem_id": problem.get("id"),
        "difficulty_level": problem.get("difficulty", 1)
    })
    
    return {
        "action": "present_content",
        "content_type": "guided_practice",
        "content": problem,
        "visual_data": visual_data,
        "requires_input": True
    }

def present_independent_practice(state: AgentState, topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Presenta un ejercicio para práctica independiente
    """
    practice_problems = topic_data.get("independent_practice", [])
    
    # Seleccionar un problema basado en el nivel de dominio
    suitable_problems = [p for p in practice_problems 
                        if p.get("difficulty", 0.5) <= state.mastery + 0.2]
    
    if not suitable_problems:
        suitable_problems = practice_problems
    
    problem = random.choice(suitable_problems)
    
    # Verificar si se necesita una visualización
    visual_data = None
    if problem.get("needs_visual", False):
        visual_data = generate_visual(
            visual_type=problem.get("visual_type", "problem"),
            topic_id=state.topic_id,
            content=problem
        )
    
    # Actualizar estado con detalles del problema actual
    state.update(
        last_problem_details=problem,
        waiting_for_input=True,  # Esperará respuesta
        next_action="evaluate_answer"
    )
    
    state.log_interaction("present_independent_practice", {
        "problem_id": problem.get("id"),
        "difficulty_level": problem.get("difficulty", 1)
    })
    
    return {
        "action": "present_content",
        "content_type": "independent_practice",
        "content": problem,
        "visual_data": visual_data,
        "requires_input": True
    }

def evaluate_answer(state: AgentState, answer: str, topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa la respuesta del usuario
    """
    problem = state.last_problem_details
    if not problem:
        return {"action": "error", "message": "No hay un problema activo para evaluar"}
    
    # Obtener la respuesta correcta
    correct_answer = problem.get("answer", "")
    
    # Evaluar si la respuesta es correcta
    # Aquí deberías implementar lógica más sofisticada para evaluar respuestas
    is_correct = answer.strip().lower() == correct_answer.strip().lower()
    
    # Determinar el tipo de error si es incorrecto
    eval_result = EvaluationResult.CORRECT
    
    if not is_correct:
        # Lógica simplificada, en la implementación real esto sería más sofisticado
        # para distinguir entre errores conceptuales y de cálculo
        if "conceptual_errors" in problem and any(err in answer.lower() for err in problem["conceptual_errors"]):
            eval_result = EvaluationResult.INCORRECT_CONCEPTUAL
        else:
            eval_result = EvaluationResult.INCORRECT_CALCULATION
    
    # Actualizar métricas de mastery
    old_mastery = state.mastery
    
    if is_correct:
        # Incrementar el dominio y los contadores
        mastery_increase = problem.get("mastery_value", 0.1)
        new_mastery = min(1.0, state.mastery + mastery_increase)
        
        state.update(
            mastery=new_mastery,
            consecutive_correct=state.consecutive_correct + 1,
            consecutive_incorrect=0,
            last_eval=eval_result,
            waiting_for_input=False,
            last_answer=answer
        )
    else:
        # Reducir el dominio y los contadores
        mastery_decrease = problem.get("mastery_penalty", 0.05)
        new_mastery = max(0.0, state.mastery - mastery_decrease)
        
        state.update(
            mastery=new_mastery,
            consecutive_correct=0,
            consecutive_incorrect=state.consecutive_incorrect + 1,
            last_eval=eval_result,
            waiting_for_input=False,
            last_answer=answer
        )
    
    state.log_interaction("evaluate_answer", {
        "problem_id": problem.get("id"),
        "is_correct": is_correct,
        "evaluation_result": eval_result,
        "old_mastery": old_mastery,
        "new_mastery": state.mastery
    })
    
    return {
        "action": "evaluation_result",
        "is_correct": is_correct,
        "evaluation_type": eval_result,
        "old_mastery": old_mastery,
        "new_mastery": state.mastery
    }

def provide_targeted_feedback(state: AgentState, topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Proporciona retroalimentación específica basada en el tipo de error
    """
    problem = state.last_problem_details
    if not problem:
        return {"action": "error", "message": "No hay un problema para proporcionar retroalimentación"}
    
    # Obtener el tipo de error
    error_type = state.last_eval
    user_answer = state.last_answer
    
    # Generar retroalimentación específica
    feedback = {}
    visual_data = None
    
    if error_type == EvaluationResult.INCORRECT_CONCEPTUAL:
        # Retroalimentación para errores conceptuales
        feedback = {
            "type": "conceptual",
            "explanation": problem.get("conceptual_feedback", "Hay un error en tu comprensión del concepto."),
            "correct_approach": problem.get("correct_approach", "")
        }
        
        # Generar visual si es necesario para error conceptual
        if problem.get("needs_conceptual_visual", False):
            visual_data = generate_visual(
                visual_type="feedback_conceptual",
                topic_id=state.topic_id,
                content=problem,
                user_answer=user_answer
            )
    
    elif error_type == EvaluationResult.INCORRECT_CALCULATION:
        # Retroalimentación para errores de cálculo
        feedback = {
            "type": "calculation",
            "explanation": problem.get("calculation_feedback", "Hay un error en tus cálculos."),
            "calculation_tip": problem.get("calculation_tip", "")
        }
    
    # Incrementar contador de retroalimentación
    state.update(
        error_feedback_count=state.error_feedback_count + 1,
        next_action=None,
        waiting_for_input=False
    )
    
    state.log_interaction("provide_targeted_feedback", {
        "feedback_type": feedback.get("type"),
        "error_type": error_type
    })
    
    return {
        "action": "present_content",
        "content_type": "feedback",
        "content": feedback,
        "visual_data": visual_data
    }

def simplify_instruction(state: AgentState, topic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplifica la instrucción o regresa a la teoría
    """
    # Si hay muchos errores consecutivos, volver a la teoría
    if state.consecutive_incorrect >= 5:
        state.update(
            theory_presented=False,  # Forzar a mostrar teoría nuevamente
            next_action=None,
            waiting_for_input=False
        )
        
        state.log_interaction("simplify_instruction", {
            "action": "return_to_theory",
            "consecutive_errors": state.consecutive_incorrect
        })
        
        return {
            "action": "present_content",
            "content_type": "system_message",
            "content": {
                "message": "Vamos a revisar nuevamente la teoría para reforzar los conceptos."
            }
        }
    
    # Simplificar la instrucción presentando un problema más sencillo
    else:
        # Reducir el nivel de maestría para obtener problemas más fáciles
        reduced_mastery = max(0.1, state.mastery - 0.2)
        
        state.update(
            mastery=reduced_mastery,
            next_action=None,
            waiting_for_input=False
        )
        
        state.log_interaction("simplify_instruction", {
            "action": "reduce_difficulty",
            "old_mastery": state.mastery + 0.2,
            "new_mastery": reduced_mastery
        })
        
        return {
            "action": "present_content",
            "content_type": "system_message",
            "content": {
                "message": "Vamos a intentar con algunos ejercicios más sencillos para fortalecer las bases."
            }
        }

def check_advance_topic(state: AgentState, topic_data: Dict[str, Any], curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifica si se debe avanzar al siguiente tema
    """
    current_topic = state.topic_id
    curriculum = curriculum_data.get("topics", [])
    
    # Encontrar el índice del tema actual
    current_index = next((i for i, topic in enumerate(curriculum) if topic.get("id") == current_topic), -1)
    
    # Verificar si hay un tema siguiente
    if current_index >= 0 and current_index < len(curriculum) - 1:
        next_topic = curriculum[current_index + 1]
        
        # Actualizar al siguiente tema
        state.update(
            topic_id=next_topic.get("id"),
            mastery=0.1,  # Reiniciar maestría para el nuevo tema
            consecutive_correct=0,
            consecutive_incorrect=0,
            theory_presented=False,
            last_eval=None,
            last_problem_details=None,
            next_action=None,
            waiting_for_input=False
        )
        
        state.log_interaction("check_advance_topic", {
            "action": "advance_to_next_topic",
            "old_topic": current_topic,
            "new_topic": next_topic.get("id")
        })
        
        return {
            "action": "topic_change",
            "old_topic": current_topic,
            "new_topic": next_topic.get("id"),
            "topic_name": next_topic.get("name", ""),
            "message": f"¡Felicitaciones! Has dominado el tema actual. Avanzaremos al siguiente tema: {next_topic.get('name', '')}"
        }
    
    # No hay más temas, el curso ha terminado
    else:
        state.log_interaction("check_advance_topic", {
            "action": "course_completed",
            "final_topic": current_topic
        })
        
        return {
            "action": "course_completed",
            "message": "¡Felicitaciones! Has completado todos los temas del curso."
        }
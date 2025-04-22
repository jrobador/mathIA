"""
Implementa las funciones principales del agente educativo.
Estas funciones corresponden a los nodos en el diagrama de flujo original.
Integra correctamente los servicios de Azure.
"""

from typing import Dict, Any, Optional, List
import random
import re
import os
import json
from datetime import datetime

from models.student_state import (
    StudentState, EvaluationOutcome, CPAPhase, 
    update_mastery, add_message, get_last_user_message
)
from models.curriculum import get_roadmap, get_next_topic_id
from services.azure_service import (
    invoke_llm, invoke_with_prompty, generate_image, generate_speech
)

# Directorio de prompts para las plantillas Prompty
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

# Funciones principales del agente (basadas en los nodos del diagrama)

async def determine_next_step(state: StudentState) -> Dict[str, Any]:
    """
    Determina el próximo paso basado en el estado actual
    """
    print(f"Ejecutando determine_next_step para session_id={state.session_id}")
    
    # Si está esperando input, debe pausar
    if state.waiting_for_input:
        return {"action": "pause", "message": "Esperando respuesta del usuario"}
    
    # Lógica de decisión basada en el diagrama de flujo
    mastery = state.topic_mastery.get(state.current_topic, 0.1)
    theory_presented = state.current_topic in state.theory_presented_for_topics
    
    next_action = None
    
    if mastery < 0.3 and not theory_presented:
        next_action = "present_theory"
    
    elif mastery < 0.3 and theory_presented:
        next_action = "present_guided_practice"
    
    elif 0.3 <= mastery <= 0.7:
        next_action = "present_independent_practice"
    
    elif state.last_evaluation in [EvaluationOutcome.INCORRECT_CONCEPTUAL, EvaluationOutcome.INCORRECT_CALCULATION]:
        next_action = "provide_targeted_feedback"
    
    elif state.consecutive_incorrect >= 3:
        next_action = "simplify_instruction"
    
    elif mastery > 0.8 and state.consecutive_correct >= 2:
        next_action = "check_advance_topic"
    
    # Por defecto, presentar práctica independiente
    else:
        next_action = "present_independent_practice"
    
    print(f"determine_next_step decidió: {next_action}")
    return {"action": next_action}

async def present_theory(state: StudentState) -> Dict[str, Any]:
    """
    Presenta la teoría del tema actual
    """
    print(f"Ejecutando present_theory para tema={state.current_topic}")
    
    # Marcar la teoría como presentada
    if state.current_topic not in state.theory_presented_for_topics:
        state.theory_presented_for_topics.append(state.current_topic)
    
    # Generar contenido de teoría utilizando LLM
    topic_id = state.current_topic
    roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id
    
    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return {"error": f"No se encontró el roadmap para {roadmap_id}"}
    
    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return {"error": f"No se encontró el tema {topic_id} en el roadmap"}
    
    try:
        # Construir ruta a la plantilla de teoría
        theory_template_path = os.path.join(PROMPTS_DIR, "theory.prompty")
        
        # Verificar si la plantilla existe
        if os.path.exists(theory_template_path):
            # Usar plantilla Prompty para generar teoría
            theory_content = await invoke_with_prompty(
                theory_template_path,
                topic_title=topic.title,
                topic_description=topic.description,
                cpa_phase=state.current_cpa_phase.value,
                theme=state.personalized_theme,
                subtopics=", ".join(topic.subtopics)
            )
        else:
            # Fallback a prompt directo si no hay plantilla
            prompt = f"""Genera una explicación teórica sobre {topic.title} para un estudiante.
            Fase: {state.current_cpa_phase.value}, Tema: {state.personalized_theme}.
            Descripción del tema: {topic.description}
            Subtemas: {', '.join(topic.subtopics)}
            
            Usa un lenguaje claro y adecuado para estudiantes, con ejemplos concretos."""
            
            system_message = "Eres un tutor educativo experto que explica conceptos matemáticos de manera clara y concisa."
            theory_content = await invoke_llm(prompt, system_message)
        
        # Generar imagen y audio si es necesario
        visual_needed = state.current_cpa_phase != CPAPhase.ABSTRACT
        image_url = None
        if visual_needed:
            img_prompt = f"Visualización educativa para el concepto matemático: {topic.title}, con tema {state.personalized_theme}, estilo claro y educativo para niños"
            image_url = await generate_image(img_prompt)
        
        # Generar audio
        audio_url = await generate_speech(theory_content)
        
        # Registrar la acción en el estado
        state.last_action_type = "present_theory"
        state.waiting_for_input = False
        
        # Agregar mensaje al historial
        add_message(state, "ai", theory_content)
        
        # Resultado con contenido enriquecido
        return {
            "action": "present_content",
            "content_type": "theory",
            "text": theory_content,
            "title": topic.title,
            "image_url": image_url,
            "audio_url": audio_url,
            "requires_input": False
        }
        
    except Exception as e:
        print(f"Error en present_theory: {e}")
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": f"No pude generar explicación teórica para {topic.title}. Probemos con práctica."
        }

async def present_guided_practice(state: StudentState) -> Dict[str, Any]:
    """
    Presenta un ejercicio guiado con más apoyo
    """
    print(f"Ejecutando present_guided_practice para tema={state.current_topic}")
    
    # Generar un problema de práctica guiada utilizando LLM
    topic_id = state.current_topic
    roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id
    
    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return {"error": f"No se encontró el roadmap para {roadmap_id}"}
    
    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return {"error": f"No se encontró el tema {topic_id} en el roadmap"}
    
    mastery = state.topic_mastery.get(topic_id, 0.1)
    
    try:
        # Construir ruta a la plantilla de práctica guiada
        practice_template_path = os.path.join(PROMPTS_DIR, "guided_practice.prompty")
        
        # Verificar si la plantilla existe
        if os.path.exists(practice_template_path):
            # Usar plantilla Prompty para generar problema
            practice_content = await invoke_with_prompty(
                practice_template_path,
                topic_title=topic.title,
                topic_description=topic.description,
                cpa_phase=state.current_cpa_phase.value,
                theme=state.personalized_theme,
                mastery_level=mastery,
                subtopics=", ".join(topic.subtopics)
            )
        else:
            # Fallback a prompt directo si no hay plantilla
            prompt = f"""Genera un problema de práctica GUIADA sobre {topic.title} para un estudiante.
            Nivel de dominio actual: {mastery:.2f}, Fase: {state.current_cpa_phase.value}
            Tema de personalización: {state.personalized_theme}
            
            El problema debe incluir instrucciones paso a paso y pistas para ayudar al estudiante.
            Incluye al final la solución esperada en formato:
            SOLUCIÓN: [respuesta correcta]"""
            
            system_message = "Eres un tutor educativo experto que crea problemas matemáticos adaptados al nivel del estudiante."
            practice_content = await invoke_llm(prompt, system_message)
        
        # Extraer la solución
        solution_match = re.search(r"SOLUCIÓN:(.+?)$", practice_content, re.DOTALL | re.IGNORECASE)
        if not solution_match:
            solution_match = re.search(r"Solución:(.+?)$", practice_content, re.DOTALL | re.IGNORECASE)
            
        solution_text = solution_match.group(1).strip() if solution_match else "5" # Valor predeterminado
        
        # Eliminar la solución del texto del problema para mostrar al estudiante
        problem_text = practice_content
        if solution_match:
            problem_text = practice_content.replace(solution_match.group(0), "").strip()
        
        # Generar imagen y audio
        image_url = await generate_image(f"Problema matemático de {topic.title} con tema {state.personalized_theme}")
        audio_url = await generate_speech(problem_text)
        
        # Guardar detalles del problema
        state.last_problem_details = {
            "problem": problem_text,
            "solution": solution_text,
            "type": "guided_practice",
            "difficulty": 0.3, # Dificultad baja para práctica guiada
            "mastery_value": 0.1, # Incremento de dominio si es correcto
            "mastery_penalty": 0.05 # Decremento de dominio si es incorrecto
        }
        
        # Actualizar estado
        state.last_action_type = "present_guided_practice"
        state.waiting_for_input = True # Esperará respuesta
        
        # Agregar mensaje al historial
        add_message(state, "ai", problem_text)
        
        return {
            "action": "present_content",
            "content_type": "guided_practice",
            "text": problem_text,
            "image_url": image_url,
            "audio_url": audio_url,
            "requires_input": True
        }
        
    except Exception as e:
        print(f"Error en present_guided_practice: {e}")
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "No pude generar un problema de práctica guiada. Intentemos otro enfoque."
        }

async def present_independent_practice(state: StudentState) -> Dict[str, Any]:
    """
    Presenta un ejercicio para práctica independiente
    """
    print(f"Ejecutando present_independent_practice para tema={state.current_topic}")
    
    # Generar un problema de práctica independiente utilizando LLM
    topic_id = state.current_topic
    roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id
    
    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return {"error": f"No se encontró el roadmap para {roadmap_id}"}
    
    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return {"error": f"No se encontró el tema {topic_id} en el roadmap"}
    
    mastery = state.topic_mastery.get(topic_id, 0.1)
    
    try:
        # Construir ruta a la plantilla de práctica independiente
        practice_template_path = os.path.join(PROMPTS_DIR, "independent_practice.prompty")
        
        # Verificar si la plantilla existe
        if os.path.exists(practice_template_path):
            # Usar plantilla Prompty para generar problema
            practice_content = await invoke_with_prompty(
                practice_template_path,
                topic_title=topic.title,
                topic_description=topic.description,
                cpa_phase=state.current_cpa_phase.value,
                theme=state.personalized_theme,
                mastery_level=mastery,
                subtopics=", ".join(topic.subtopics)
            )
        else:
            # Fallback a prompt directo si no hay plantilla
            prompt = f"""Genera un problema de práctica INDEPENDIENTE sobre {topic.title} para un estudiante.
            Nivel de dominio actual: {mastery:.2f}, Fase: {state.current_cpa_phase.value}
            Tema de personalización: {state.personalized_theme}
            
            El problema debe ser levemente más difícil que su nivel actual.
            Incluye al final la solución esperada en formato:
            SOLUCIÓN: [respuesta correcta]"""
            
            system_message = "Eres un tutor educativo experto que crea problemas matemáticos adaptados al nivel del estudiante."
            practice_content = await invoke_llm(prompt, system_message)
        
        # Extraer la solución
        solution_match = re.search(r"SOLUCIÓN:(.+?)$", practice_content, re.DOTALL | re.IGNORECASE)
        if not solution_match:
            solution_match = re.search(r"Solución:(.+?)$", practice_content, re.DOTALL | re.IGNORECASE)
            
        solution_text = solution_match.group(1).strip() if solution_match else "5" # Valor predeterminado
        
        # Eliminar la solución del texto del problema para mostrar al estudiante
        problem_text = practice_content
        if solution_match:
            problem_text = practice_content.replace(solution_match.group(0), "").strip()
        
        # Generar imagen y audio
        image_url = await generate_image(f"Problema matemático de {topic.title} con tema {state.personalized_theme}")
        audio_url = await generate_speech(problem_text)
        
        # Guardar detalles del problema
        state.last_problem_details = {
            "problem": problem_text,
            "solution": solution_text,
            "type": "independent_practice",
            "difficulty": min(0.8, mastery + 0.2), # Ajustar dificultad según dominio
            "mastery_value": 0.15, # Mayor incremento por ser independiente
            "mastery_penalty": 0.08 # Mayor penalización por ser independiente
        }
        
        # Actualizar estado
        state.last_action_type = "present_independent_practice"
        state.waiting_for_input = True # Esperará respuesta
        
        # Agregar mensaje al historial
        add_message(state, "ai", problem_text)
        
        return {
            "action": "present_content",
            "content_type": "independent_practice",
            "text": problem_text,
            "image_url": image_url,
            "audio_url": audio_url,
            "requires_input": True
        }
        
    except Exception as e:
        print(f"Error en present_independent_practice: {e}")
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "No pude generar un problema de práctica independiente. Intentemos otro enfoque."
        }

async def evaluate_answer(state: StudentState, user_answer: str) -> Dict[str, Any]:
    """
    Evalúa la respuesta del usuario
    """
    print(f"Ejecutando evaluate_answer para respuesta='{user_answer}'")
    
    # Verificar que existan detalles del problema
    if not state.last_problem_details:
        return {
            "action": "error",
            "error": "No hay problema activo para evaluar",
            "fallback_text": "No recuerdo cuál era el problema. Intentemos uno nuevo."
        }
    
    # Obtener detalles del problema
    problem = state.last_problem_details
    problem_text = problem.get("problem", "")
    expected_solution = problem.get("solution", "")
    problem_type = problem.get("type", "unknown")
    
    try:
        # Construir ruta a la plantilla de evaluación
        eval_template_path = os.path.join(PROMPTS_DIR, "evaluation.prompty")
        
        # Verificar si la plantilla existe
        if os.path.exists(eval_template_path):
            # Usar plantilla Prompty para evaluar
            evaluation_result_str = await invoke_with_prompty(
                eval_template_path,
                problem=problem_text,
                solution=expected_solution,
                student_answer=user_answer
            )
        else:
            # Fallback a prompt directo si no hay plantilla
            prompt = f"""Evalúa esta respuesta de un estudiante:
            Problema: {problem_text}
            Solución esperada: {expected_solution}
            Respuesta del estudiante: {user_answer}
            
            Evalúa si la respuesta es CORRECT, INCORRECT_CONCEPTUAL o INCORRECT_CALCULATION.
            Responde solo con uno de estos valores."""
            
            system_message = "Eres un tutor educativo experto que evalúa respuestas matemáticas con precisión."
            evaluation_result_str = await invoke_llm(prompt, system_message)
        
        # Procesar el resultado
        evaluation_result_str = evaluation_result_str.strip().upper()
        
        # Mapear a enum
        if "CORRECT" in evaluation_result_str:
            evaluation_result = EvaluationOutcome.CORRECT
        elif "CONCEPTUAL" in evaluation_result_str:
            evaluation_result = EvaluationOutcome.INCORRECT_CONCEPTUAL
        elif "CALCULATION" in evaluation_result_str:
            evaluation_result = EvaluationOutcome.INCORRECT_CALCULATION
        else:
            evaluation_result = EvaluationOutcome.UNCLEAR
        
        # Actualizar métricas de dominio
        old_mastery = state.topic_mastery.get(state.current_topic, 0.0)
        
        if evaluation_result == EvaluationOutcome.CORRECT:
            # Incrementar dominio y contadores
            mastery_increase = problem.get("mastery_value", 0.1)
            state.consecutive_correct += 1
            state.consecutive_incorrect = 0
            update_mastery(state, mastery_increase)
        else:
            # Reducir dominio y contadores
            mastery_decrease = problem.get("mastery_penalty", 0.05)
            state.consecutive_correct = 0
            state.consecutive_incorrect += 1
            update_mastery(state, -mastery_decrease)
        
        # Actualizar estado
        state.last_evaluation = evaluation_result
        state.last_action_type = "evaluate_answer"
        state.waiting_for_input = False
        
        # Generar mensaje de retroalimentación básica
        if evaluation_result == EvaluationOutcome.CORRECT:
            feedback_text = "¡Correcto! Buen trabajo."
        else:
            feedback_text = "Esa no es la respuesta correcta. Veamos por qué."
        
        # Agregar mensaje de respuesta al historial
        add_message(state, "human", user_answer)
        add_message(state, "ai", feedback_text)
        
        # Generar audio para retroalimentación
        audio_url = await generate_speech(feedback_text)
        
        new_mastery = state.topic_mastery.get(state.current_topic, 0.0)
        
        return {
            "action": "evaluation_result",
            "evaluation_type": evaluation_result.value,
            "text": feedback_text,
            "audio_url": audio_url,
            "is_correct": evaluation_result == EvaluationOutcome.CORRECT,
            "old_mastery": old_mastery,
            "new_mastery": new_mastery
        }
        
    except Exception as e:
        print(f"Error en evaluate_answer: {e}")
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "Hubo un problema al evaluar tu respuesta. Intentemos otro problema."
        }

async def provide_targeted_feedback(state: StudentState) -> Dict[str, Any]:
    """
    Proporciona retroalimentación específica basada en el tipo de error
    """
    print(f"Ejecutando provide_targeted_feedback para error_type={state.last_evaluation}")
    
    # Verificar que existan detalles del problema y una evaluación
    if not state.last_problem_details or not state.last_evaluation:
        return {
            "action": "error",
            "error": "No hay problema o evaluación para proporcionar retroalimentación",
            "fallback_text": "Intentemos un nuevo problema."
        }
    
    # Obtener detalles relevantes
    problem = state.last_problem_details
    problem_text = problem.get("problem", "")
    expected_solution = problem.get("solution", "")
    error_type = state.last_evaluation
    
    # Obtener la última respuesta del usuario
    last_message = get_last_user_message(state)
    user_answer = last_message.content if last_message else "No disponible"
    
    try:
        # Construir ruta a la plantilla de retroalimentación
        feedback_template_path = os.path.join(PROMPTS_DIR, "feedback.prompty")
        
        # Verificar si la plantilla existe
        if os.path.exists(feedback_template_path):
            # Usar plantilla Prompty para generar retroalimentación
            feedback_text = await invoke_with_prompty(
                feedback_template_path,
                problem=problem_text,
                solution=expected_solution,
                student_answer=user_answer,
                error_type=error_type.value,
                theme=state.personalized_theme
            )
        else:
            # Fallback a prompt directo si no hay plantilla
            prompt = f"""Proporciona retroalimentación detallada para un estudiante que cometió un error de tipo {error_type.value}:
            Problema: {problem_text}
            Solución esperada: {expected_solution}
            Respuesta del estudiante: {user_answer}
            
            Explica el error y proporciona orientación para corregirlo.
            Sé amable y constructivo. Personaliza para tema {state.personalized_theme}."""
            
            system_message = "Eres un tutor educativo experto que proporciona retroalimentación constructiva y útil."
            feedback_text = await invoke_llm(prompt, system_message)
        
        # Generar imagen y audio si es necesario
        image_url = None
        if error_type == EvaluationOutcome.INCORRECT_CONCEPTUAL:
            img_prompt = f"Explicación visual clara del concepto matemático {state.current_topic.replace('_', ' ')} con tema {state.personalized_theme}"
            image_url = await generate_image(img_prompt)
        
        audio_url = await generate_speech(feedback_text)
        
        # Actualizar estado
        state.error_feedback_given_count += 1
        state.last_action_type = "provide_feedback"
        state.waiting_for_input = False
        
        # Agregar mensaje al historial
        add_message(state, "ai", feedback_text)
        
        return {
            "action": "present_content",
            "content_type": "feedback",
            "text": feedback_text,
            "image_url": image_url,
            "audio_url": audio_url,
            "requires_input": False,
            "feedback_type": error_type.value
        }
        
    except Exception as e:
        print(f"Error en provide_targeted_feedback: {e}")
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "No pude generar retroalimentación específica. Intentemos otro problema."
        }

async def simplify_instruction(state: StudentState) -> Dict[str, Any]:
    """
    Simplifica la instrucción o regresa a la teoría
    """
    print(f"Ejecutando simplify_instruction para consecutive_incorrect={state.consecutive_incorrect}")
    
    # Si hay muchos errores consecutivos, volver a la teoría
    if state.consecutive_incorrect >= 5:
        # Forzar a mostrar teoría nuevamente
        if state.current_topic in state.theory_presented_for_topics:
            state.theory_presented_for_topics.remove(state.current_topic)
        
        # Retroceder fase CPA si es posible
        if state.current_cpa_phase == CPAPhase.ABSTRACT:
            state.current_cpa_phase = CPAPhase.PICTORIAL
        elif state.current_cpa_phase == CPAPhase.PICTORIAL:
            state.current_cpa_phase = CPAPhase.CONCRETE
        
        state.last_action_type = "simplify_instruction"
        state.waiting_for_input = False
        
        message = "Vamos a revisar nuevamente la teoría para reforzar los conceptos."
        add_message(state, "ai", message)
        
        audio_url = await generate_speech(message)
        
        return {
            "action": "present_content",
            "content_type": "system_message",
            "text": message,
            "audio_url": audio_url,
            "requires_input": False
        }
    
    # Simplificar la instrucción presentando un problema más sencillo
    else:
        # Reducir el nivel de maestría para obtener problemas más fáciles
        old_mastery = state.topic_mastery.get(state.current_topic, 0.1)
        reduced_mastery = max(0.1, old_mastery - 0.2)
        state.topic_mastery[state.current_topic] = reduced_mastery
        
        state.last_action_type = "simplify_instruction"
        state.waiting_for_input = False
        
        message = "Vamos a intentar con algunos ejercicios más sencillos para fortalecer las bases."
        add_message(state, "ai", message)
        
        audio_url = await generate_speech(message)
        
        return {
            "action": "present_content",
            "content_type": "system_message",
            "text": message,
            "audio_url": audio_url,
            "requires_input": False
        }

async def check_advance_topic(state: StudentState) -> Dict[str, Any]:
    """
    Verifica si se debe avanzar al siguiente tema
    """
    print(f"Ejecutando check_advance_topic para current_topic={state.current_topic}")
    
    current_topic = state.current_topic
    roadmap_id = current_topic.split('_')[0] if '_' in current_topic else current_topic
    
    # Verificar si hay un tema siguiente
    next_topic_id = get_next_topic_id(roadmap_id, current_topic)
    
    if next_topic_id:
        # Obtener información del siguiente tema
        roadmap = get_roadmap(roadmap_id)
        next_topic = roadmap.get_topic_by_id(next_topic_id) if roadmap else None
        
        if next_topic:
            # Actualizar al siguiente tema
            state.current_topic = next_topic_id
            state.current_cpa_phase = CPAPhase.CONCRETE  # Reiniciar fase CPA
            state.consecutive_correct = 0
            state.consecutive_incorrect = 0
            state.last_evaluation = None
            state.last_problem_details = None
            state.error_feedback_given_count = 0
            state.waiting_for_input = False
            
            # Inicializar dominio para el nuevo tema si no existe
            if next_topic_id not in state.topic_mastery:
                state.topic_mastery[next_topic_id] = 0.1
            
            state.last_action_type = "advance_topic"
            
            message = f"¡Felicitaciones! Has dominado el tema actual. Avanzaremos al siguiente tema: {next_topic.title}"
            add_message(state, "ai", message)
            
            audio_url = await generate_speech(message)
            
            return {
                "action": "topic_change",
                "text": message,
                "audio_url": audio_url,
                "old_topic": current_topic,
                "new_topic": next_topic_id,
                "new_topic_title": next_topic.title,
                "requires_input": False
            }
        
    # No hay más temas, el curso ha terminado
    message = f"¡Felicitaciones! Has completado todos los temas del curso de {roadmap_id}."
    add_message(state, "ai", message)
    
    audio_url = await generate_speech(message)
    
    return {
        "action": "course_completed",
        "text": message,
        "audio_url": audio_url,
        "requires_input": False,
        "is_final_step": True
    }
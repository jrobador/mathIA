from typing import Dict, Any, List
from enum import Enum
from app.agent.state import StudentSessionState, EvaluationOutcome, CPAPhase
from app.services.azure_openai import invoke_llm
from app.services.azure_speech import generate_speech
from app.services.stability_ai import generate_image
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.agent.roadmap import get_roadmap, get_next_topic_id
import re

async def determine_next_step(state: StudentSessionState) -> Dict[str, Any]:
    """
    Nodo central de decisión que determina la siguiente acción pedagógica
    basándose en el estado actual del estudiante.
    """
    print("Executing determine_next_step...")
    
    # Obtain current mastery level for the topic
    current_topic = state.get("current_topic", "fractions_introduction")
    mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
    
    # Get tracking variables
    consecutive_correct = state.get("consecutive_correct", 0)
    consecutive_incorrect = state.get("consecutive_incorrect", 0)
    last_action_type = state.get("last_action_type")
    last_evaluation = state.get("last_evaluation")
    error_feedback_given_count = state.get("error_feedback_given_count", 0)
    
    # Decision logic tree
    next_node = "present_theory"  # Default action
    
    # If mastery is low and we haven't just shown theory
    if mastery < 0.3 and last_action_type != "present_theory":
        next_node = "present_theory"
    
    # If mastery is low but we just showed theory
    elif mastery < 0.3 and last_action_type == "present_theory":
        next_node = "present_guided_practice"
    
    # If mastery is medium or there are some consecutive correct answers
    elif (0.3 <= mastery <= 0.7) or consecutive_correct > 0:
        next_node = "present_independent_practice"
    
    # If the last attempt was conceptually incorrect
    elif last_evaluation == "Incorrect_Conceptual" and error_feedback_given_count < 2:
        next_node = "provide_targeted_feedback"
    
    # If the last attempt had calculation errors
    elif last_evaluation == "Incorrect_Calculation":
        next_node = "provide_targeted_feedback"
    
    # If there are multiple consecutive errors
    elif consecutive_incorrect >= 3:
        # Go back to theory or simplify
        next_node = "present_theory"
        # We could also go back in the CPA phase if in ABSTRACT
        if state.get("current_cpa_phase") == "Abstract":
            state["current_cpa_phase"] = "Pictorial"
    
    # If mastery is high with several consecutive correct answers
    elif mastery > 0.8 and consecutive_correct >= 3:
        next_node = "check_advance_topic"
    
    print(f"Decision: Next node = {next_node}")
    return {"next": next_node}

async def present_theory(state: StudentSessionState) -> Dict[str, Any]:
    """
    Genera y presenta una explicación teórica adaptada al tema actual
    y la fase CPA en la que se encuentra el estudiante.
    """
    print("Executing present_theory...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", "Concrete")
    personalized_theme = state.get("personalized_theme", "espacio")
    
    # Create a system prompt for the LLM
    system_prompt = f"""
    Eres un tutor de matemáticas experto en el método Singapur.
    Genera una explicación clara sobre {current_topic} para un estudiante,
    usando el enfoque Singapur en la fase {current_cpa_phase}.
    Contextualiza ejemplos con el tema de interés: {personalized_theme}.
    Usa lenguaje accesible y explicaciones paso a paso.
    La explicación debe tener 2-3 párrafos, ser concisa pero efectiva.
    """
    
    # Create messages for the LLM call
    messages = [
        HumanMessage(content=f"Explícame sobre {current_topic} en fase {current_cpa_phase}")
    ]
    
    # Call the LLM for theory generation
    theory_explanation = await invoke_llm(messages, system_prompt)
    
    # Decide if we need visualization based on CPA phase
    needs_visual = current_cpa_phase in ["Concrete", "Pictorial"]
    
    # Generate image if needed
    image_url = None
    if needs_visual:
        image_prompt = f"Educational math visualization for {current_topic} in {current_cpa_phase} phase, related to {personalized_theme}, child-friendly, clear visual learning aid"
        image_url = await generate_image(image_prompt)
    
    # Generate audio for accessibility
    audio_url = await generate_speech(theory_explanation)
    
    # Update state
    state["last_action_type"] = "present_theory"
    
    # Prepare output for frontend
    current_step_output = {
        "text": theory_explanation,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": False
    }
    
    # Update state with output
    state["current_step_output"] = current_step_output
    
    return {"next": "determine_next_step"}

async def present_guided_practice(state: StudentSessionState) -> Dict[str, Any]:
    """
    Genera un problema guiado con el modelado de la solución,
    adaptado al nivel del estudiante.
    """
    print("Executing present_guided_practice...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", "Concrete")
    personalized_theme = state.get("personalized_theme", "espacio")
    mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
    
    # System prompt for guided practice
    system_prompt = f"""
    Eres un tutor de matemáticas experto en el método Singapur.
    Genera un problema de práctica guiada sobre {current_topic},
    en fase {current_cpa_phase}, con un tema relacionado a {personalized_theme}.
    
    El problema debe ser adecuado para un nivel de dominio: {mastery:.1f} (en escala 0-1).
    
    Incluye el problema claramente marcado y luego muestra el modelado de solución paso a paso.
    
    Divide tu respuesta en dos partes claras:
    1. El problema que se le mostrará al estudiante
    2. La solución paso a paso con explicaciones
    
    IMPORTANTE: Separa la solución del problema con la etiqueta "===SOLUCIÓN PARA EVALUACIÓN===" 
    para que pueda ser procesada adecuadamente.
    """
    
    # Messages for the LLM call
    messages = [
        HumanMessage(content=f"Crea un ejercicio guiado sobre {current_topic}")
    ]
    
    # Call the LLM for guided practice generation
    practice_content = await invoke_llm(messages, system_prompt)
    
    # Process the response to separate problem and solution
    parts = practice_content.split("===SOLUCIÓN PARA EVALUACIÓN===")
    problem_text = parts[0].strip()
    solution_text = parts[1].strip() if len(parts) > 1 else ""
    
    # Decide if we need visualization
    needs_visual = current_cpa_phase in ["Concrete", "Pictorial"]
    
    # Generate image if needed
    image_url = None
    if needs_visual:
        image_prompt = f"Math problem visualization for {current_topic} in {current_cpa_phase} phase, about {personalized_theme}, educational, child-friendly"
        image_url = await generate_image(image_prompt)
    
    # Generate audio
    audio_url = await generate_speech(problem_text)
    
    # Save problem details for later evaluation
    state["last_problem_details"] = {
        "problem": problem_text,
        "solution": solution_text,
        "type": "guided_practice"
    }
    
    # Update state
    state["last_action_type"] = "present_guided_practice"
    
    # Prepare output for frontend
    current_step_output = {
        "text": problem_text,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": True
    }
    
    # Update state with output
    state["current_step_output"] = current_step_output
    
    return {"next": "evaluate_answer"}

async def present_independent_practice(state: StudentSessionState) -> Dict[str, Any]:
    """
    Genera un problema de práctica independiente adaptado 
    al nivel de dominio actual del estudiante.
    """
    print("Executing present_independent_practice...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", "Concrete")
    personalized_theme = state.get("personalized_theme", "espacio")
    mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
    
    # System prompt for independent practice
    system_prompt = f"""
    Eres un tutor de matemáticas experto en el método Singapur.
    Genera un problema de práctica independiente sobre {current_topic},
    en fase {current_cpa_phase}, con un tema relacionado a {personalized_theme}.
    
    El problema debe ser adecuado para un nivel de dominio: {mastery:.1f} (en escala 0-1).
    
    Proporciona SOLO el problema para el estudiante, SIN incluir la solución en la parte visible.
    
    Sin embargo, debes proporcionar la solución detallada después de una etiqueta especial,
    para que se pueda usar en la evaluación posterior.
    
    IMPORTANTE: Separa la solución del problema con la etiqueta "===SOLUCIÓN PARA EVALUACIÓN===" 
    para que pueda ser procesada adecuadamente.
    """
    
    # Messages for the LLM call
    messages = [
        HumanMessage(content=f"Crea un ejercicio independiente sobre {current_topic}")
    ]
    
    # Call the LLM for independent practice generation
    practice_content = await invoke_llm(messages, system_prompt)
    
    # Process the response to separate problem and solution
    parts = practice_content.split("===SOLUCIÓN PARA EVALUACIÓN===")
    problem_text = parts[0].strip()
    solution_text = parts[1].strip() if len(parts) > 1 else ""
    
    # Decide if we need visualization
    needs_visual = current_cpa_phase in ["Concrete", "Pictorial"]
    
    # Generate image if needed
    image_url = None
    if needs_visual:
        image_prompt = f"Math problem visualization for {current_topic} in {current_cpa_phase} phase, about {personalized_theme}, educational, child-friendly"
        image_url = await generate_image(image_prompt)
    
    # Generate audio
    audio_url = await generate_speech(problem_text)
    
    # Save problem details for later evaluation
    state["last_problem_details"] = {
        "problem": problem_text,
        "solution": solution_text,
        "type": "independent_practice"
    }
    
    # Update state
    state["last_action_type"] = "present_independent_practice"
    
    # Prepare output for frontend
    current_step_output = {
        "text": problem_text,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": True
    }
    
    # Update state with output
    state["current_step_output"] = current_step_output
    
    return {"next": "evaluate_answer"}

async def evaluate_answer(state: StudentSessionState) -> Dict[str, Any]:
    """
    Evalúa la respuesta del estudiante comparándola con la solución esperada
    y determina el tipo de error si lo hay.
    """
    print("Executing evaluate_answer...")
    # Get the student's answer (last message)
    messages = state.get("messages", [])
    
    if not messages or not isinstance(messages[-1], HumanMessage):
        print("Warning: No student answer found in state")
        return {"next": "determine_next_step"}
    
    student_answer = messages[-1].content
    
    # Get problem details
    last_problem = state.get("last_problem_details", {})
    problem = last_problem.get("problem", "")
    solution = last_problem.get("solution", "")
    
    # System prompt for evaluation
    system_prompt = """
    Eres un evaluador experto de respuestas matemáticas.
    Evalúa la respuesta del estudiante al problema matemático proporcionado.
    Determina si la respuesta es:
    1. Correcta (Correct) - La respuesta es correcta matemáticamente.
    2. Incorrecta debido a error conceptual (Incorrect_Conceptual) - El estudiante no ha entendido el concepto.
    3. Incorrecta debido a error de cálculo (Incorrect_Calculation) - El concepto está bien pero hay errores de cálculo.
    4. Poco clara o ambigua (Unclear) - No se puede determinar si es correcta o no.
    
    Proporciona una evaluación detallada explicando el razonamiento, identificando errores específicos si los hay.
    
    IMPORTANTE: Empieza tu respuesta con "[RESULTADO: X]" donde X es uno de: Correct, Incorrect_Conceptual, Incorrect_Calculation, Unclear.
    Luego proporciona tu explicación detallada.
    """
    
    # Messages for the LLM call
    messages = [
        HumanMessage(content=f"""
        Problema: {problem}
        
        Solución esperada: {solution}
        
        Respuesta del estudiante: {student_answer}
        
        Evalúa la respuesta e indica el resultado como: [RESULTADO: (Correct/Incorrect_Conceptual/Incorrect_Calculation/Unclear)]
        Luego proporciona una explicación detallada del razonamiento.
        """)
    ]
    
    # Call the LLM for evaluation
    evaluation_response = await invoke_llm(messages, system_prompt)
    
    # Extract the evaluation result
    result_match = re.search(r'\[RESULTADO:\s*(Correct|Incorrect_Conceptual|Incorrect_Calculation|Unclear)\]', 
                           evaluation_response)
    
    result = "Unclear"
    if result_match:
        result = result_match.group(1)
    
    # Extract feedback text (remove the [RESULTADO: X] part)
    feedback_text = re.sub(r'\[RESULTADO:\s*(Correct|Incorrect_Conceptual|Incorrect_Calculation|Unclear)\]', 
                          '', evaluation_response).strip()
    
    # Update state based on result
    if result == "Correct":
        state["consecutive_correct"] = state.get("consecutive_correct", 0) + 1
        state["consecutive_incorrect"] = 0
        # Increase mastery
        current_topic = state.get("current_topic", "fractions_introduction")
        current_mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
        # Make sure topic_mastery exists
        if "topic_mastery" not in state:
            state["topic_mastery"] = {}
        state["topic_mastery"][current_topic] = min(1.0, current_mastery + 0.1)
    elif result in ["Incorrect_Conceptual", "Incorrect_Calculation"]:
        state["consecutive_incorrect"] = state.get("consecutive_incorrect", 0) + 1
        state["consecutive_correct"] = 0
        # Decrease mastery differently based on error type
        current_topic = state.get("current_topic", "fractions_introduction")
        current_mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
        # Make sure topic_mastery exists
        if "topic_mastery" not in state:
            state["topic_mastery"] = {}
        if result == "Incorrect_Conceptual":
            state["topic_mastery"][current_topic] = max(0.0, current_mastery - 0.05)
        else:
            state["topic_mastery"][current_topic] = max(0.0, current_mastery - 0.02)
    
    # Update state
    state["last_evaluation"] = result
    state["error_feedback_given_count"] = 0  # Reset feedback counter
    state["last_action_type"] = "evaluate_answer"
    
    # Prepare output for frontend
    current_step_output = {
        "evaluation": result,
        "feedback_text": feedback_text
    }
    
    # Update state with output
    state["current_step_output"] = current_step_output
    
    return {"next": "determine_next_step"}

async def provide_targeted_feedback(state: StudentSessionState) -> Dict[str, Any]:
    """
    Proporciona feedback específico basado en el tipo de error detectado
    en la evaluación previa.
    """
    print("Executing provide_targeted_feedback...")
    feedback_text = state.get("current_step_output", {}).get("feedback_text", "")
    last_evaluation = state.get("last_evaluation", "Unclear")
    current_cpa_phase = state.get("current_cpa_phase", "Concrete")
    current_topic = state.get("current_topic", "fractions_introduction")
    personalized_theme = state.get("personalized_theme", "espacio")
    
    # If feedback text is not provided, generate it
    if not feedback_text:
        # Create prompt to generate feedback
        system_prompt = f"""
        Eres un tutor de matemáticas experto en proporcionar feedback constructivo.
        Genera un feedback específico para un error de tipo {last_evaluation} 
        en el tema {current_topic}.
        El feedback debe ser empático, motivador y educativamente útil.
        """
        
        messages = [
            HumanMessage(content=f"Proporciona feedback para un error de tipo {last_evaluation} en el tema {current_topic}")
        ]
        
        # Call LLM for feedback generation
        feedback_text = await invoke_llm(messages, system_prompt)
    
    # If the error is conceptual and we're in abstract phase, consider going back
    if last_evaluation == "Incorrect_Conceptual" and current_cpa_phase == "Abstract":
        state["current_cpa_phase"] = "Pictorial"
        feedback_text += "\n\nVamos a usar un modelo visual para entender mejor este concepto."
    
    # Decide if we need a visual to enhance feedback
    needs_visual = last_evaluation == "Incorrect_Conceptual"
    
    # Generate image if needed
    image_url = None
    if needs_visual:
        image_prompt = f"Educational visual explanation of {current_topic} misconception, related to {personalized_theme}, clear instructional diagram"
        image_url = await generate_image(image_prompt)
    
    # Generate audio
    audio_url = await generate_speech(feedback_text)
    
    # Update state
    state["error_feedback_given_count"] = state.get("error_feedback_given_count", 0) + 1
    state["last_action_type"] = "provide_feedback"
    
    # Prepare output for frontend
    current_step_output = {
        "text": feedback_text,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": False
    }
    
    # Update state with output
    state["current_step_output"] = current_step_output
    
    return {"next": "determine_next_step"}

async def check_advance_topic(state: StudentSessionState) -> Dict[str, Any]:
    """
    Verifica si hay un siguiente tema en el roadmap para avanzar,
    o si se ha completado todo el proceso.
    """
    print("Executing check_advance_topic...")
    current_topic = state.get("current_topic", "fractions_introduction")
    
    # Determinar el roadmap basado en el tema actual
    roadmap_id = None
    
    # Extraer el prefijo del tema (por ejemplo, 'fractions' de 'fractions_introduction')
    topic_prefix_match = re.match(r'^([a-z]+)_', current_topic)
    if topic_prefix_match:
        roadmap_id = topic_prefix_match.group(1)
    else:
        # Si no se puede determinar, usar fracciones por defecto
        roadmap_id = "fractions"
    
    # Obtener el siguiente tema usando la función de roadmap
    next_topic_id = get_next_topic_id(roadmap_id, current_topic)
    
    # Verificar si hay un tema siguiente
    if next_topic_id:
        # Obtener roadmap para obtener más información del tema
        roadmap = get_roadmap(roadmap_id)
        next_topic = roadmap.get_topic_by_id(next_topic_id) if roadmap else None
        
        # Reset state for new topic
        state["current_topic"] = next_topic_id
        state["consecutive_correct"] = 0
        state["consecutive_incorrect"] = 0
        state["current_cpa_phase"] = "Concrete"
        
        # Initialize mastery for new topic if it doesn't exist
        if "topic_mastery" not in state:
            state["topic_mastery"] = {}
        if next_topic_id not in state["topic_mastery"]:
            state["topic_mastery"][next_topic_id] = 0.1
        
        # Create transition message
        if next_topic:
            transition_text = f"¡Excelente progreso! Has dominado el tema actual. Avancemos ahora a: {next_topic.title}"
            transition_description = next_topic.description
        else:
            transition_text = f"¡Excelente progreso! Avancemos al siguiente tema: {next_topic_id.replace('_', ' ').title()}"
            transition_description = "Un nuevo tema para seguir aprendiendo matemáticas."
        
        # Generate audio
        audio_url = await generate_speech(transition_text)
        
        # Prepare output for frontend
        current_step_output = {
            "text": f"{transition_text}\n\n{transition_description}",
            "audio_url": audio_url,
            "prompt_for_answer": False
        }
        
        # Update state with output
        state["current_step_output"] = current_step_output
        
        return {"next": "determine_next_step"}
    else:
        # No more topics, end the session
        roadmap = get_roadmap(roadmap_id)
        roadmap_title = roadmap.title if roadmap else roadmap_id.capitalize()
        
        completion_text = f"¡Felicidades! Has completado todos los temas de {roadmap_title}. Has demostrado un excelente dominio de los conceptos."
        
        # Generate audio
        audio_url = await generate_speech(completion_text)
        
        # Prepare output for frontend
        current_step_output = {
            "text": completion_text,
            "audio_url": audio_url,
            "prompt_for_answer": False
        }
        
        # Update state with output
        state["current_step_output"] = current_step_output
        
        return {"next": "__end__"}
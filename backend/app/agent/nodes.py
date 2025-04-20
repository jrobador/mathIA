# -*- coding: utf-8 -*-
from typing import Dict, Any
from app.agent.state import StudentSessionState, EvaluationOutcome, CPAPhase 
from app.services.azure_openai import invoke_with_prompty 
from app.services.azure_speech import generate_speech
from app.services.azure_image import generate_image
from langchain_core.messages import HumanMessage
from app.agent.roadmap import get_roadmap, get_next_topic_id
import re
import os

# Define the prompts directory path
PROMPTS_DIR = os.path.join("prompts")

async def determine_next_step(state: StudentSessionState) -> Dict[str, Any]:
    """
    Central decision node that determines the next pedagogical action
    based on the student's current state.
    """
    print("Executing determine_next_step...")
    
    # Obtain current mastery level for the topic
    current_topic = state.get("current_topic", "fractions_introduction")
    mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
    
    # Get tracking variables from state
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
    elif last_evaluation == EvaluationOutcome.INCORRECT_CONCEPTUAL.value and error_feedback_given_count < 2:
        next_node = "provide_targeted_feedback"
    
    # If the last attempt had calculation errors
    elif last_evaluation == EvaluationOutcome.INCORRECT_CALCULATION.value:
        next_node = "provide_targeted_feedback"
    
    # If there are multiple consecutive errors
    elif consecutive_incorrect >= 3:
        # Go back to theory or simplify
        next_node = "present_theory"
        # We could also go back in the CPA phase if in ABSTRACT
        if state.get("current_cpa_phase") == CPAPhase.ABSTRACT.value:
            state["current_cpa_phase"] = CPAPhase.PICTORIAL.value
    
    # If mastery is high with several consecutive correct answers
    elif mastery > 0.8 and consecutive_correct >= 3:
        next_node = "check_advance_topic"
    
    # If mastery is reasonable
    elif mastery >= 0.3:
         next_node = "present_independent_practice"

    print(f"Decision: Next node = {next_node}")
    return {"next": next_node}

async def present_theory(state: StudentSessionState) -> Dict[str, Any]:
    """
    Generates and presents a theoretical explanation adapted to the current topic
    and the student's current CPA phase.
    """
    print("Executing present_theory...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", CPAPhase.CONCRETE.value)
    personalized_theme = state.get("personalized_theme", "space")
    
    # Use the theory prompty template
    theory_template_path = os.path.join(PROMPTS_DIR, "theory.prompty")
    theory_explanation = await invoke_with_prompty(
        theory_template_path,
        topic=current_topic,
        cpa_phase=current_cpa_phase,
        theme=personalized_theme
    )
    
    # Decide if visualization is needed based on the CPA phase
    needs_visual = current_cpa_phase in [CPAPhase.CONCRETE.value, CPAPhase.PICTORIAL.value]
    
    # Generate an image if needed
    image_url = None
    if needs_visual:
        # Use the image generation prompty template
        image_template_path = os.path.join(PROMPTS_DIR, "image_generation.prompty")
        image_prompt = await invoke_with_prompty(
            image_template_path,
            image_type="theory",
            topic=current_topic,
            cpa_phase=current_cpa_phase,
            theme=personalized_theme
        )
        image_url = await generate_image(image_prompt)
    
    # Generate audio for accessibility
    audio_url = await generate_speech(theory_explanation)
    
    # Update the state to reflect the last action performed
    state["last_action_type"] = "present_theory"
    state["consecutive_incorrect"] = 0 # Reset consecutive incorrect count
    state["error_feedback_given_count"] = 0 # Reset feedback count

    # Prepare the output data to be sent to the frontend
    current_step_output = {
        "text": theory_explanation,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": False
    }
    
    # Update the state with the output for the current step
    state["current_step_output"] = current_step_output
    
    # Indicate the next node in the graph flow
    return {"next": "determine_next_step"}

async def present_guided_practice(state: StudentSessionState) -> Dict[str, Any]:
    """
    Generates a guided practice problem with solution modeling,
    adapted to the student's level.
    """
    print("Executing present_guided_practice...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", CPAPhase.CONCRETE.value)
    personalized_theme = state.get("personalized_theme", "space")
    mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
    
    # Use the guided practice prompty template
    guided_practice_template_path = os.path.join(PROMPTS_DIR, "guided_practice.prompty")
    practice_content = await invoke_with_prompty(
        guided_practice_template_path,
        topic=current_topic,
        cpa_phase=current_cpa_phase,
        theme=personalized_theme,
        mastery=mastery
    )
    
    # Process the LLM response to separate the problem and the hidden solution
    parts = practice_content.split("===SOLUTION FOR EVALUATION===")
    problem_text = parts[0].strip()
    # Ensure there is a solution part, otherwise use an empty string
    solution_text = parts[1].strip() if len(parts) > 1 else "Solution not provided by LLM." 
    
    # Decide if visualization is needed based on the CPA phase
    needs_visual = current_cpa_phase in [CPAPhase.CONCRETE.value, CPAPhase.PICTORIAL.value]
    
    # Generate an image if needed
    image_url = None
    if needs_visual:
        # Use the image generation prompty template
        image_template_path = os.path.join(PROMPTS_DIR, "image_generation.prompty")
        image_prompt = await invoke_with_prompty(
            image_template_path,
            image_type="practice",
            topic=current_topic,
            cpa_phase=current_cpa_phase,
            theme=personalized_theme
        )
        image_url = await generate_image(image_prompt)
    
    # Generate audio for the problem text
    audio_url = await generate_speech(problem_text)
    
    # Save the problem details (including the hidden solution) in the state for later evaluation
    state["last_problem_details"] = {
        "problem": problem_text,
        "solution": solution_text,
        "type": "guided_practice"
    }
    
    # Update the state to reflect the last action
    state["last_action_type"] = "present_guided_practice"
    
    # Prepare the output for the frontend
    current_step_output = {
        "text": problem_text,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": True
    }
    
    # Update the state with the output
    state["current_step_output"] = current_step_output
    
    # Indicate the next node
    return {"next": "evaluate_answer"}

async def present_independent_practice(state: StudentSessionState) -> Dict[str, Any]:
    """
    Generates an independent practice problem adapted 
    to the student's current mastery level.
    """
    print("Executing present_independent_practice...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", CPAPhase.CONCRETE.value)
    personalized_theme = state.get("personalized_theme", "space")
    mastery = state.get("topic_mastery", {}).get(current_topic, 0.1)
    
    # Use the independent practice prompty template
    independent_practice_template_path = os.path.join(PROMPTS_DIR, "independent_practice.prompty")
    practice_content = await invoke_with_prompty(
        independent_practice_template_path,
        topic=current_topic,
        cpa_phase=current_cpa_phase,
        theme=personalized_theme,
        mastery=mastery
    )
    
    # Process the response to separate the problem and the hidden solution
    parts = practice_content.split("===SOLUTION FOR EVALUATION===")
    problem_text = parts[0].strip()
    solution_text = parts[1].strip() if len(parts) > 1 else "Solution not provided by LLM."
    
    # Decide if visualization is needed based on the CPA phase
    needs_visual = current_cpa_phase in [CPAPhase.CONCRETE.value, CPAPhase.PICTORIAL.value]
    
    # Generate an image if needed
    image_url = None
    if needs_visual:
        # Use the image generation prompty template
        image_template_path = os.path.join(PROMPTS_DIR, "image_generation.prompty")
        image_prompt = await invoke_with_prompty(
            image_template_path,
            image_type="practice",
            topic=current_topic,
            cpa_phase=current_cpa_phase,
            theme=personalized_theme
        )
        image_url = await generate_image(image_prompt)
    
    # Generate audio for the problem text
    audio_url = await generate_speech(problem_text)
    
    # Save the problem details (including the hidden solution) for later evaluation
    state["last_problem_details"] = {
        "problem": problem_text,
        "solution": solution_text,
        "type": "independent_practice"
    }
    
    # Update the state
    state["last_action_type"] = "present_independent_practice"
    
    # Prepare the output for the frontend
    current_step_output = {
        "text": problem_text,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": True
    }
    
    # Update the state with the output
    state["current_step_output"] = current_step_output
    
    # Indicate the next node
    return {"next": "evaluate_answer"}

async def evaluate_answer(state: StudentSessionState) -> Dict[str, Any]:
    """
    Evaluates the student's answer by comparing it with the expected solution
    and determines the type of error, if any. Updates mastery and tracking stats.
    """
    print("Executing evaluate_answer...")
    # Get the student's answer (assumed to be the last message in the history)
    messages = state.get("messages", [])
    
    # Check if the last message is from the human (student)
    if not messages or not isinstance(messages[-1], HumanMessage):
        print("Warning: No student answer found in state messages to evaluate.")
        state["last_action_type"] = "evaluate_answer_failed"
        state["current_step_output"] = { 
             "text": "I didn't receive your answer. Could you please try again?",
             "audio_url": await generate_speech("I didn't receive your answer. Could you please try again?"),
             "prompt_for_answer": True 
        }
        return {"next": "determine_next_step"}

    student_answer = messages[-1].content
    
    # Get the details of the problem that was last presented
    last_problem = state.get("last_problem_details", {})
    problem = last_problem.get("problem", "No problem context available.")
    solution = last_problem.get("solution", "No solution context available.")
    
    # Use the evaluation prompty template
    evaluation_template_path = os.path.join(PROMPTS_DIR, "evaluation.prompty")
    evaluation_response = await invoke_with_prompty(
        evaluation_template_path,
        problem=problem,
        solution=solution,
        student_answer=student_answer
    )
    
    # Extract the evaluation result using regex
    result_match = re.search(r'\[EVALUATION:\s*(Correct|Incorrect_Conceptual|Incorrect_Calculation|Unclear)\]', 
                           evaluation_response, re.IGNORECASE)
    
    result = EvaluationOutcome.UNCLEAR.value # Default to Unclear if pattern not found
    if result_match:
        # Map the extracted string to the Enum value for consistency
        result_str = result_match.group(1).capitalize()
        if result_str == EvaluationOutcome.CORRECT.value:
             result = EvaluationOutcome.CORRECT.value
        elif result_str == EvaluationOutcome.INCORRECT_CONCEPTUAL.value.capitalize():
             result = EvaluationOutcome.INCORRECT_CONCEPTUAL.value
        elif result_str == EvaluationOutcome.INCORRECT_CALCULATION.value.capitalize():
             result = EvaluationOutcome.INCORRECT_CALCULATION.value

    # Extract the feedback text
    feedback_text = re.sub(r'\[EVALUATION:\s*(Correct|Incorrect_Conceptual|Incorrect_Calculation|Unclear)\]', 
                          '', evaluation_response, flags=re.IGNORECASE).strip()
    if not feedback_text:
        feedback_text = "Evaluation complete."

    # --- Update state based on evaluation result ---
    current_topic = state.get("current_topic", "fractions_introduction")
    # Ensure topic_mastery dictionary exists before updating
    if "topic_mastery" not in state:
        state["topic_mastery"] = {}
    current_mastery = state["topic_mastery"].get(current_topic, 0.1)

    if result == EvaluationOutcome.CORRECT.value:
        state["consecutive_correct"] = state.get("consecutive_correct", 0) + 1
        state["consecutive_incorrect"] = 0
        # Increase mastery, more significantly for independent practice
        mastery_increase = 0.15 if last_problem.get("type") == "independent_practice" else 0.1
        new_mastery = min(1.0, current_mastery + mastery_increase)
        state["topic_mastery"][current_topic] = new_mastery
        feedback_text = f"Correct! Well done. {feedback_text}"

    elif result in [EvaluationOutcome.INCORRECT_CONCEPTUAL.value, EvaluationOutcome.INCORRECT_CALCULATION.value]:
        state["consecutive_incorrect"] = state.get("consecutive_incorrect", 0) + 1
        state["consecutive_correct"] = 0
        # Decrease mastery, more for conceptual errors
        mastery_decrease = 0.1 if result == EvaluationOutcome.INCORRECT_CONCEPTUAL.value else 0.05
        new_mastery = max(0.0, current_mastery - mastery_decrease)
        state["topic_mastery"][current_topic] = new_mastery
        feedback_text = f"Not quite right. {feedback_text}"

    else: # Unclear or other cases
        state["consecutive_correct"] = 0
        state["consecutive_incorrect"] = 0
        feedback_text = f"I couldn't quite understand your answer. Let's look at this: {feedback_text}"

    # Update general state variables after evaluation
    state["last_evaluation"] = result
    state["error_feedback_given_count"] = 0
    state["last_action_type"] = "evaluate_answer"
    
    # Prepare output for frontend
    current_step_output = {
        "evaluation": result,
        "feedback_text": feedback_text,
        "audio_url": await generate_speech(feedback_text),
        "prompt_for_answer": False
    }
    
    # Update state with the output of this evaluation step
    state["current_step_output"] = current_step_output
    
    # Move to the decision node to determine what happens next based on the evaluation
    return {"next": "determine_next_step"}

async def provide_targeted_feedback(state: StudentSessionState) -> Dict[str, Any]:
    """
    Provides specific feedback based on the type of error detected
    in the previous evaluation.
    """
    print("Executing provide_targeted_feedback...")
    # Get feedback text from the previous evaluation step if available
    feedback_text = state.get("current_step_output", {}).get("feedback_text", "")
    last_evaluation = state.get("last_evaluation", EvaluationOutcome.UNCLEAR.value)
    current_cpa_phase = state.get("current_cpa_phase", CPAPhase.CONCRETE.value)
    current_topic = state.get("current_topic", "fractions_introduction")
    personalized_theme = state.get("personalized_theme", "space")
    
    # If feedback text wasn't generated during evaluation or is default, generate it now
    if not feedback_text or feedback_text == "Evaluation complete.":
        # Use the feedback prompty template
        feedback_template_path = os.path.join(PROMPTS_DIR, "feedback.prompty")
        feedback_text = await invoke_with_prompty(
            feedback_template_path,
            topic=current_topic,
            error_type=last_evaluation,
            cpa_phase=current_cpa_phase
        )
    
    # --- Enhance feedback based on context ---
    # If the error is conceptual and we're in the abstract phase, suggest reverting to pictorial
    if last_evaluation == EvaluationOutcome.INCORRECT_CONCEPTUAL.value and current_cpa_phase == CPAPhase.ABSTRACT.value:
        state["current_cpa_phase"] = CPAPhase.PICTORIAL.value
        feedback_text += "\n\nLet's try using a visual model to understand this concept better."
        print(f"Reverted CPA phase to {state['current_cpa_phase']} due to conceptual error.")

    # Decide if a visual aid would enhance this specific feedback
    needs_visual = last_evaluation == EvaluationOutcome.INCORRECT_CONCEPTUAL.value
    
    # Generate an image if deemed helpful
    image_url = None
    if needs_visual:
        # Use the image generation prompty template
        image_template_path = os.path.join(PROMPTS_DIR, "image_generation.prompty")
        image_prompt = await invoke_with_prompty(
            image_template_path,
            image_type="feedback_conceptual",
            topic=current_topic,
            cpa_phase=current_cpa_phase,
            theme=personalized_theme
        )
        image_url = await generate_image(image_prompt)
    
    # Generate audio for the feedback message
    audio_url = await generate_speech(feedback_text)
    
    # Update state
    state["error_feedback_given_count"] = state.get("error_feedback_given_count", 0) + 1
    state["last_action_type"] = "provide_feedback"
    
    # Prepare output for the frontend
    current_step_output = {
        "text": feedback_text,
        "image_url": image_url,
        "audio_url": audio_url,
        "prompt_for_answer": False
    }
    
    # Update state with the output
    state["current_step_output"] = current_step_output
    
    # Proceed to the decision node
    return {"next": "determine_next_step"}

async def check_advance_topic(state: StudentSessionState) -> Dict[str, Any]:
    """
    Checks if the student has mastered the current topic and if there is 
    a next topic in the roadmap to advance to.
    """
    print("Executing check_advance_topic...")
    current_topic = state.get("current_topic", "fractions_introduction")
    current_cpa_phase = state.get("current_cpa_phase", CPAPhase.CONCRETE.value)  # Get current CPA phase
    
    # Determine the current roadmap ID based on the topic prefix
    roadmap_id = None
    topic_prefix_match = re.match(r'^([a-z_]+)_', current_topic)
    if topic_prefix_match:
        roadmap_id = topic_prefix_match.group(1)
    else:
        print(f"Warning: Could not determine roadmap ID from topic '{current_topic}'. Defaulting to 'fractions'.")
        roadmap_id = "fractions"

    # Get the ID of the next topic using the roadmap helper function
    next_topic_id = get_next_topic_id(roadmap_id, current_topic)
    
    # Check if a next topic exists in the roadmap
    if next_topic_id:
        # Get the roadmap details to fetch the next topic's title/description
        roadmap = get_roadmap(roadmap_id)
        next_topic = roadmap.get_topic_by_id(next_topic_id) if roadmap else None
        
        # --- Reset state for the new topic ---
        previous_topic = current_topic
        state["current_topic"] = next_topic_id
        state["consecutive_correct"] = 0
        state["consecutive_incorrect"] = 0
        state["current_cpa_phase"] = CPAPhase.CONCRETE.value
        state["error_feedback_given_count"] = 0
        state["last_action_type"] = "advance_topic"
        state["last_evaluation"] = None
        state["last_problem_details"] = None

        # Initialize mastery for the new topic if it doesn't exist
        if "topic_mastery" not in state:
            state["topic_mastery"] = {}
        if next_topic_id not in state["topic_mastery"]:
            state["topic_mastery"][next_topic_id] = 0.1
        
        # Create a transition message for the student
        if next_topic:
            transition_text = f"Excellent progress! You've mastered {previous_topic.replace('_', ' ').title()}. Let's move on to: {next_topic.title}"
            transition_description = next_topic.description
        else:
            transition_text = f"Excellent progress! Let's move on to the next topic: {next_topic_id.replace('_', ' ').title()}"
            transition_description = "A new challenge awaits as we continue learning math!"
        
        # Generate audio for the transition message
        audio_url = await generate_speech(transition_text)
        
        # Prepare the output for the frontend
        current_step_output = {
            "text": f"{transition_text}\n\n{transition_description}",
            "image_url": None,
            "audio_url": audio_url,
            "prompt_for_answer": False
        }
        
        # Update state with the transition output
        state["current_step_output"] = current_step_output
        
        print(f"Advanced topic from {previous_topic} to {next_topic_id}")
        return {"next": "determine_next_step"}
    
    else:
        # No more topics in this roadmap, end the session
        roadmap = get_roadmap(roadmap_id)
        roadmap_title = roadmap.title if roadmap else roadmap_id.replace('_', ' ').capitalize()
        
        completion_text = f"Congratulations! You have completed all the topics in the {roadmap_title} roadmap. You've shown excellent understanding of the concepts!"
        
        # Generate audio for the completion message
        audio_url = await generate_speech(completion_text)
        
        # Generate a celebratory image
        theme = state.get("personalized_theme", "achievement")
        # Make sure we have the current_cpa_phase for the image generation prompt
        current_cpa_phase = state.get("current_cpa_phase", CPAPhase.CONCRETE.value)  # Get current CPA phase
        
        image_template_path = os.path.join(PROMPTS_DIR, "image_generation.prompty")
        image_prompt = await invoke_with_prompty(
            image_template_path,
            image_type="celebration",
            topic=current_topic,
            cpa_phase=current_cpa_phase,
            theme=theme
        )
        image_url = await generate_image(image_prompt)

        # Prepare the final output for the frontend
        current_step_output = {
            "text": completion_text,
            "image_url": image_url,
            "audio_url": audio_url,
            "prompt_for_answer": False,
            "is_final_step": True
        }
        
        # Update state with the final output
        state["current_step_output"] = current_step_output
        state["last_action_type"] = "complete_roadmap"
        
        print(f"Completed roadmap {roadmap_id}")
        return {"next": "__end__"}
"""
Implements the core functions of the learning agent.
These functions correspond to the nodes in the original flowchart.
Successfully integrates Azure services.
"""
from datetime import datetime
from typing import Dict, Any
import re
import os

from models.student_state import (
    StudentState, EvaluationOutcome, CPAPhase, 
    update_mastery, add_message, get_last_user_message
)
from models.curriculum import get_roadmap, get_next_topic_id
from services.azure_service import (
    invoke_llm, invoke_with_prompty, generate_image, generate_speech
)

def get_prompts_dir():
    """
    Determines the correct prompts directory path using multiple resolution strategies.
    This handles different execution contexts (running from project root or subdirectory).
    """
    file_relative_path = os.path.join(os.path.dirname(__file__), "..", "prompts")
    if os.path.exists(file_relative_path):
        print(f"Using prompts directory relative to file: {file_relative_path}")
        return os.path.abspath(file_relative_path)
    
    cwd_relative_path = os.path.join(os.getcwd(), "prompts")
    if os.path.exists(cwd_relative_path):
        print(f"Using prompts directory relative to working directory: {cwd_relative_path}")
        return os.path.abspath(cwd_relative_path)
    
    parent_dir_path = os.path.join(os.getcwd(), "..", "prompts")
    if os.path.exists(parent_dir_path):
        print(f"Using prompts directory relative to parent directory: {parent_dir_path}")
        return os.path.abspath(parent_dir_path)
    
    print(f"WARNING: Could not find prompts directory. Using best guess: {file_relative_path}")
    return os.path.abspath(file_relative_path)

PROMPTS_DIR = get_prompts_dir()
print(f"Prompts directory set to: {PROMPTS_DIR}")

async def determine_next_step(state: StudentState) -> Dict[str, Any]:
    """
    Determine the next step based on the current state with detailed logging
    """
    print(f"Ejecutando determine_next_step para session_id={state.session_id}")
    
    mastery = state.topic_mastery.get(state.current_topic, 0.1)
    theory_presented = state.current_topic in state.theory_presented_for_topics
    
    print(f"DEBUG determine_next_step - Estado actual:")
    print(f"  - topic: {state.current_topic}")
    print(f"  - mastery: {mastery:.2f}")
    print(f"  - theory_presented: {theory_presented}")
    print(f"  - consecutive_correct: {state.consecutive_correct}")
    print(f"  - consecutive_incorrect: {state.consecutive_incorrect}")
    print(f"  - last_evaluation: {state.last_evaluation}")
    print(f"  - waiting_for_input: {state.waiting_for_input}")
    print(f"  - last_action_type: {state.last_action_type}")
    
    if state.waiting_for_input:
        print("  → Pausing execution: waiting_for_input = True")
        return {"action": "pause", "message": "Esperando respuesta del usuario"}
    
    next_action = None
    decision_reason = "Default" 
    
    if mastery < 0.3 and not theory_presented:
        next_action = "present_theory"
        decision_reason = f"mastery ({mastery:.2f}) < 0.3 and theory not presented"
    
    elif mastery < 0.3 and theory_presented:
        next_action = "present_guided_practice"
        decision_reason = f"mastery ({mastery:.2f}) < 0.3 and theory already presented"
    
    elif state.last_evaluation in [EvaluationOutcome.INCORRECT_CONCEPTUAL, EvaluationOutcome.INCORRECT_CALCULATION]:
        next_action = "provide_targeted_feedback"
        decision_reason = f"last_evaluation is {state.last_evaluation}"
    
    elif state.consecutive_incorrect >= 3:
        next_action = "simplify_instruction"
        decision_reason = f"consecutive_incorrect ({state.consecutive_incorrect}) >= 3"
    
    elif (mastery > 0.6 and state.consecutive_correct >= 2) or (mastery > 0.8 and state.consecutive_correct >= 1):
        next_action = "check_advance_topic"
        decision_reason = f"Advancement condition met: mastery = {mastery:.2f}, consecutive_correct = {state.consecutive_correct}"
        print(f"DEBUG: Topic advancement triggered! mastery = {mastery:.2f}, consecutive_correct = {state.consecutive_correct}")
    
    elif 0.3 <= mastery <= 0.7:
        next_action = "present_independent_practice"
        decision_reason = f"mastery ({mastery:.2f}) between 0.3 and 0.7"
    
    else:
        next_action = "present_independent_practice"
        decision_reason = f"Default case - mastery = {mastery:.2f}, not matching any other condition"
    
    print(f"determine_next_step decidió: {next_action}")
    print(f"  → Reason: {decision_reason}")
    
    print(f"DEBUG determine_next_step - Condiciones evaluadas:")
    print(f"  - mastery < 0.3: {mastery < 0.3}")
    print(f"  - theory_presented: {theory_presented}")
    print(f"  - 0.3 <= mastery <= 0.7: {0.3 <= mastery <= 0.7}")
    print(f"  - mastery > 0.6 & consecutive_correct >= 2: {mastery > 0.6 and state.consecutive_correct >= 2}")
    print(f"  - mastery > 0.8 & consecutive_correct >= 1: {mastery > 0.8 and state.consecutive_correct >= 1}")
    print(f"  - last_evaluation requires feedback: {state.last_evaluation in [EvaluationOutcome.INCORRECT_CONCEPTUAL, EvaluationOutcome.INCORRECT_CALCULATION]}")
    print(f"  - consecutive_incorrect >= 3: {state.consecutive_incorrect >= 3}")
    
    return {"action": next_action}

def get_cpa_phase_value(cpa_phase) -> str:
    """Safely extract the value from a CPA phase object or string"""
    if isinstance(cpa_phase, CPAPhase):
        return cpa_phase.value
    elif isinstance(cpa_phase, str):
        return cpa_phase
    else:
        print(f"Warning: Unexpected type for CPA phase: {type(cpa_phase)}. Defaulting to Concrete.")
        return CPAPhase.CONCRETE.value

async def present_theory(state: StudentState) -> Dict[str, Any]:
    """
    Presents the theory for the current topic.
    """
    print(f"Executing present_theory for topic={state.current_topic}") 

    if state.current_topic not in state.theory_presented_for_topics:
        state.theory_presented_for_topics.append(state.current_topic)

    topic_id = state.current_topic
    roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id

    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return {"error": f"Roadmap not found for {roadmap_id}"}

    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return {"error": f"Topic {topic_id} not found in the roadmap"}

    try:
        theory_template_path = os.path.join(PROMPTS_DIR, "theory.prompty")

        current_cpa_phase_value = get_cpa_phase_value(state.current_cpa_phase)

        theme = state.personalized_theme

        print(f"Generating theory for topic: {topic.title} (ID: {topic_id})")

        if os.path.exists(theory_template_path):
            theory_content = await invoke_with_prompty(
                theory_template_path,
                topic=topic.title,      
                cpa_phase=current_cpa_phase_value,
                theme=theme
            )

            if ("fractions" in theory_content.lower() and
                "fraction" not in topic.title.lower() and
                "addition" in topic.title.lower()):
                print(f"WARNING: Generated content mentions 'fractions' but topic is {topic.title}. Regenerating...")


                direct_prompt = f"""
                You are teaching SPECIFICALLY about {topic.title}.

                Generate a clear, concise explanation about {topic.title} for a student.
                Do NOT mention fractions or any other unrelated topic.

                Use the {current_cpa_phase_value} phase approach:
                - For Concrete: Use physical examples and real-world situations.
                - For Pictorial: Use visual representations and models.
                - For Abstract: Introduce mathematical notation and formulas.

                Use examples related to the theme: {theme}.
                Keep your explanation focused ONLY on {topic.title}.
                """
                system_message = "You are a math tutor specializing in Single-Digit Addition concepts."
                theory_content = await invoke_llm(direct_prompt, system_message)
        else:
            prompt = f"""Generate a theoretical explanation about {topic.title} for a student.
            Phase: {current_cpa_phase_value}, Theme: {theme}.
            Topic Description: {topic.description}
            Subtopics: {', '.join(topic.subtopics)}

            Use clear language appropriate for students, with concrete examples."""

            system_message = "You are an expert educational tutor who explains mathematical concepts clearly and concisely."
            theory_content = await invoke_llm(prompt, system_message)

        visual_needed = current_cpa_phase_value != CPAPhase.ABSTRACT.value
        image_url = None
        if visual_needed:
            img_prompt = f"Educational visualization for the mathematical concept: {topic.title}, with theme {theme}, clear and educational style for children"
            image_url = await generate_image(img_prompt)

        audio_url = await generate_speech(theory_content)

        state.last_action_type = "present_theory"
        state.waiting_for_input = False

        add_message(state, "ai", theory_content)

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
        print(f"Error in present_theory: {e}")
        import traceback
        traceback.print_exc()
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": f"I couldn't generate a theoretical explanation for {topic.title}. Let's try some practice instead."
        }
    
async def present_guided_practice(state: StudentState) -> Dict[str, Any]:
    """
    Presents a guided exercise with more support
    """

    print(f"Executing present_guided_practice for topic={state.current_topic}")

    topic_id = state.current_topic
    roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id

    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return {"error": f"Roadmap not found for {roadmap_id}"}

    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return {"error": f"Topic {topic_id} not found in the roadmap"}

    mastery = state.topic_mastery.get(topic_id, 0.1)

    current_cpa_phase_value: str
    if isinstance(state.current_cpa_phase, CPAPhase):
        current_cpa_phase_value = state.current_cpa_phase.value
    elif isinstance(state.current_cpa_phase, str):
        current_cpa_phase_value = state.current_cpa_phase
    else:
        print(f"Warning: Unexpected type for current_cpa_phase: {type(state.current_cpa_phase)}. Defaulting.")
        current_cpa_phase_value = CPAPhase.CONCRETE.value

    try:
        practice_template_path = os.path.join(PROMPTS_DIR, "guided_practice.prompty")

        if os.path.exists(practice_template_path):
            practice_content = await invoke_with_prompty(
                practice_template_path,
                topic=topic.title,
                topic_description=topic.description,
                cpa_phase=current_cpa_phase_value,
                theme=state.personalized_theme,
                mastery=mastery,
            )
        else:
            prompt = f"""Generate a GUIDED practice problem about {topic.title} for a student.
            Current mastery level: {mastery:.2f}, Phase: {current_cpa_phase_value}
            Personalization theme: {state.personalized_theme}

            The problem should include step-by-step instructions and hints to help the student.
            Include the expected solution at the end in the format:
            ===SOLUTION FOR EVALUATION===
            [detailed solution]

            Make sure the final numerical answer appears clearly, for example:
            "The answer is 10 space rocks" or "The result is 15 objects."
            """

            system_message = "You are an expert educational tutor who creates math problems adapted to the student's level."
            practice_content = await invoke_llm(prompt, system_message)

        solution_match = re.search(r"===SOLUTION FOR EVALUATION===(.*?)$", practice_content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if not solution_match:
            solution_match = re.search(r"SOLUTION:(.+?)$", practice_content, re.DOTALL | re.IGNORECASE | re.MULTILINE) # Translated "SOLUCIÓN"

        if solution_match:
            full_solution = solution_match.group(1).strip()
            answer_match = re.search(r"(?:answer|final answer|result|answer is|astronaut has)[:\s]*(\d+)\s*(?:space rocks|boxes|moon rocks|objects|items)?", full_solution, re.IGNORECASE)
            if answer_match:
                solution_text = answer_match.group(1).strip()
            else:
                answer_match = re.search(r"(\d+)\s*(?:space rocks|boxes|moon rocks|objects|items)(?:\s*(?:left|remaining|in total|altogether|in all))?", full_solution, re.IGNORECASE)
                if answer_match:
                    solution_text = answer_match.group(1).strip()
                else:
                    solution_text = full_solution
        else:
            solution_text = "No Solution Found"
            print(f"WARNING: Could not extract solution from guided practice content")

        print(f"Extracted solution: '{solution_text}' from guided practice")

        problem_text = practice_content
        if solution_match:
            problem_text = practice_content.replace(solution_match.group(0), "").strip()

        image_url = await generate_image(f"Math problem about {topic.title} with theme {state.personalized_theme}") # Translated prompt
        audio_url = await generate_speech(problem_text)

        state.last_problem_details = {
            "problem": problem_text,
            "solution": solution_text,
            "type": "guided_practice",
            "difficulty": 0.3,
            "mastery_value": 0.2,
            "mastery_penalty": 0.1
        }

        state.last_action_type = "present_guided_practice"
        state.waiting_for_input = True

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
        print(f"Error in present_guided_practice: {e}") 
        import traceback
        traceback.print_exc()
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "I couldn't generate a guided practice problem. Let's try another approach." 
        }

async def present_independent_practice(state: StudentState) -> Dict[str, Any]:
    """
    Presents an exercise for independent practice.
    """
    print(f"Executing present_independent_practice for topic={state.current_topic}")

    topic_id = state.current_topic
    roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id

    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return {"error": f"Roadmap not found for {roadmap_id}"}

    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return {"error": f"Topic {topic_id} not found in the roadmap"}

    mastery = state.topic_mastery.get(topic_id, 0.1)

    previous_context_instruction = ""
    if state.last_problem_details and "problem" in state.last_problem_details:
        previous_problem_text = state.last_problem_details["problem"]
        previous_context_instruction = f"""Here is the previous exercise the student just completed:
            <previous_exercise>
            {previous_problem_text}
            </previous_exercise>
            Based on the previous exercise, create a NEW, similar practice problem for the topic '{topic.title}'.
            Make this new problem slightly more challenging than the previous one, primarily by using different numbers or a slightly varied scenario, while keeping the core mathematical concept the same. Ensure the problem fits the theme '{state.personalized_theme}'."""
    else:
        previous_context_instruction = f"Create an independent practice problem about '{topic.title}' suitable for the student's current level, using the theme '{state.personalized_theme}'."

    try:
        practice_template_path = os.path.join(PROMPTS_DIR, "independent_practice.prompty")

        current_cpa_phase_value: str
        if isinstance(state.current_cpa_phase, CPAPhase):
            current_cpa_phase_value = state.current_cpa_phase.value
        elif isinstance(state.current_cpa_phase, str):
            current_cpa_phase_value = state.current_cpa_phase
        else:
            print(f"Warning: Unexpected type for current_cpa_phase in present_independent_practice: {type(state.current_cpa_phase)}. Defaulting.")
            current_cpa_phase_value = CPAPhase.ABSTRACT.value

        if os.path.exists(practice_template_path):
            practice_content = await invoke_with_prompty(
                practice_template_path,
                topic=topic.title,
                cpa_phase=current_cpa_phase_value,
                theme=state.personalized_theme,
                mastery=mastery,
                previous_context=previous_context_instruction
            )
        else:
            prompt = f"""Generate an INDEPENDENT practice problem about {topic.title} for a student.
            Current mastery level: {mastery:.2f}, Phase: {current_cpa_phase_value}
            Personalization theme: {state.personalized_theme}

            {previous_context_instruction} # Include the detailed instruction here

            The problem should be suitable for independent practice (no step-by-step guidance within the problem text itself).
            Include the expected solution ONLY at the very end in the format:
            ===SOLUTION FOR EVALUATION===
            [detailed solution]

            Make sure the final numerical answer appears clearly within the solution section, for example:
            "The final answer is 10 space rocks" or "The result is 15 objects."
            """

            system_message = "You are an expert educational tutor who creates appropriately challenging math problems adapted to the student's progress and theme."
            practice_content = await invoke_llm(prompt, system_message)

        solution_match = re.search(r"===SOLUTION FOR EVALUATION===(.*?)$", practice_content, re.DOTALL | re.IGNORECASE)
        if not solution_match:
            solution_match = re.search(r"SOLUTION:(.+?)$", practice_content, re.DOTALL | re.IGNORECASE)

        solution_text = "No Solution Found" # Default value
        if solution_match:
            full_solution = solution_match.group(1).strip()
            # Try robust extraction first
            answer_match = re.search(r"(?:answer|final answer|result|answer is)[:=\s]*(\d+)\b", full_solution, re.IGNORECASE)
            if answer_match:
                solution_text = answer_match.group(1).strip()
            else:
                answer_match = re.search(r"(\d+)\s*(?:space rocks|boxes|moon rocks|objects|items|coins|apples|bananas|stars)?(?:left|remaining|in total|altogether|in all)?\.?$", full_solution, re.IGNORECASE | re.MULTILINE)
                if answer_match:
                    solution_text = answer_match.group(1).strip()
                else:
                    all_numbers = re.findall(r'\d+', full_solution)
                    if all_numbers:
                        solution_text = all_numbers[-1]
                        print(f"INFO: Using last number found ('{solution_text}') as solution fallback.")
                    else:
                        print(f"WARNING: Could not extract numerical solution from: '{full_solution}'")
                        solution_text = full_solution 


        else:
            print(f"WARNING: Could not extract solution block using ===SOLUTION FOR EVALUATION=== or SOLUTION: from independent practice content.")


        print(f"Extracted solution: '{solution_text}' from independent practice")

        problem_text = practice_content
        if solution_match:
            problem_text = practice_content.replace(solution_match.group(0), "").strip()
        else:
            problem_text = re.sub(r"The final answer is.*$", "", problem_text, flags=re.IGNORECASE | re.MULTILINE).strip()
            problem_text = re.sub(r"The answer is.*$", "", problem_text, flags=re.IGNORECASE | re.MULTILINE).strip()
            problem_text = re.sub(r"Solution:.*$", "", problem_text, flags=re.IGNORECASE | re.MULTILINE).strip()


        image_url = await generate_image(f"Math problem about {topic.title} with theme {state.personalized_theme}")
        audio_url = await generate_speech(problem_text)

        state.last_problem_details = {
            "problem": problem_text,
            "solution": solution_text, 
            "type": "independent_practice",
            "difficulty": min(0.9, mastery + 0.25), 
            "mastery_value": 0.3,
            "mastery_penalty": 0.15
        }

        state.last_action_type = "present_independent_practice"
        state.waiting_for_input = True

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
        print(f"Error in present_independent_practice: {e}")
        import traceback
        traceback.print_exc()
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "I couldn't generate an independent practice problem. Let's try another approach."
        }
        
async def evaluate_answer(state: StudentState, user_answer: str) -> Dict[str, Any]:
    """
    Evaluates the user's answer using an LLM and updates the state.
    Relies entirely on the LLM's judgment without additional deterministic checks.
    """
    print(f"Executing evaluate_answer for answer='{user_answer}'")

    if not state.last_problem_details:
        print("Error in evaluate_answer: No active problem to evaluate.")
        state.waiting_for_input = False
        return {
            "action": "error",
            "error": "No active problem to evaluate",
            "fallback_text": "I don't remember the problem. Let's try a new one.",
            "waiting_for_input": False
        }

    problem = state.last_problem_details
    problem_text = problem.get("problem", "")
    expected_solution = problem.get("solution", "")
    print(f"Problem has expected solution: '{expected_solution}' (for reference only)")

    try:
        eval_template_path = os.path.join(PROMPTS_DIR, "evaluation.prompty")
        evaluation_result_str = ""

        if os.path.exists(eval_template_path):
            print(f"Using evaluation prompty template: {eval_template_path}")
            evaluation_result_str = await invoke_with_prompty(
                eval_template_path,
                problem=problem_text,
                student_answer=user_answer
            )
        else:
            print(f"Warning: Evaluation template not found. Using fallback.")
            prompt = f"""Evaluate this student's answer to a math problem:
            Problem: {problem_text}
            Student's Answer: {user_answer}

            Solve the problem yourself, then evaluate if the answer is CORRECT, INCORRECT_CONCEPTUAL, or INCORRECT_CALCULATION.
            IMPORTANT: Start your response with EXACTLY "[EVALUATION: X]" where X is one of:
            CORRECT, INCORRECT_CONCEPTUAL, INCORRECT_CALCULATION, UNCLEAR.

            Be strict in your evaluation. For numeric answers, they must match the expected value exactly.
            """
            system_message = "You are an expert educational tutor who accurately evaluates math answers."
            evaluation_result_str = await invoke_llm(prompt, system_message)

        print(f"Raw evaluation result string: '{evaluation_result_str[:200]}...'")
        evaluation_result = EvaluationOutcome.UNCLEAR

        eval_pattern = r"\[EVALUATION:\s*(CORRECT|INCORRECT_CONCEPTUAL|INCORRECT_CALCULATION|UNCLEAR)\]"
        match = re.search(eval_pattern, evaluation_result_str, re.IGNORECASE)

        if match:
            result_type = match.group(1).upper()
            if result_type == "CORRECT":
                evaluation_result = EvaluationOutcome.CORRECT
            elif result_type == "INCORRECT_CONCEPTUAL":
                evaluation_result = EvaluationOutcome.INCORRECT_CONCEPTUAL
            elif result_type == "INCORRECT_CALCULATION":
                evaluation_result = EvaluationOutcome.INCORRECT_CALCULATION
            else:
                evaluation_result = EvaluationOutcome.UNCLEAR
            print(f"Parsed evaluation from tag: {result_type}")
        else:
            print(f"WARNING: Could not parse evaluation tag. Defaulting to UNCLEAR.")
            evaluation_result = EvaluationOutcome.UNCLEAR

        print(f"Final evaluation determined: {evaluation_result.value} for answer '{user_answer}'")

        old_mastery = state.topic_mastery.get(state.current_topic, 0.0)

        if evaluation_result == EvaluationOutcome.CORRECT:
            mastery_increase = problem.get("mastery_value", 0.1)
            state.consecutive_correct += 1
            state.consecutive_incorrect = 0
            update_mastery(state, mastery_increase)
            feedback_text = "Correct! Good job."

            new_mastery = state.topic_mastery.get(state.current_topic, 0.0)
            print(f"MASTERY UPDATE: Topic '{state.current_topic}' mastery increased from {old_mastery:.2f} to {new_mastery:.2f}")
            print(f"PROGRESS: {'%.0f' % (new_mastery * 100)}% mastery, {state.consecutive_correct} consecutive correct")
        else:
            mastery_decrease = problem.get("mastery_penalty", 0.05)
            state.consecutive_correct = 0
            state.consecutive_incorrect += 1
            update_mastery(state, -mastery_decrease)
            feedback_text = "That's not the right answer. Let's see why."

            new_mastery = state.topic_mastery.get(state.current_topic, 0.0)
            print(f"MASTERY UPDATE: Topic '{state.current_topic}' mastery decreased from {old_mastery:.2f} to {new_mastery:.2f}")

        state.last_evaluation = evaluation_result
        state.last_action_type = "evaluate_answer"
        state.waiting_for_input = False
        state.updated_at = datetime.now()

        add_message(state, "human", user_answer)
        add_message(state, "ai", feedback_text)

        audio_url = await generate_speech(feedback_text)
        new_mastery = state.topic_mastery.get(state.current_topic, 0.0)

        return {
            "action": "evaluation_result",
            "evaluation_type": evaluation_result.value,
            "text": feedback_text,
            "audio_url": audio_url,
            "is_correct": evaluation_result == EvaluationOutcome.CORRECT,
            "old_mastery": old_mastery,
            "new_mastery": new_mastery,
            "is_final_step": False,
            "waiting_for_input": False
        }

    except Exception as e:
        print(f"Error in evaluate_answer: {e}")
        import traceback
        traceback.print_exc()
        state.waiting_for_input = False
        state.last_action_type = "error"
        state.updated_at = datetime.now()
        return {
            "action": "error",
            "error": str(e),
            "fallback_text": "There was a problem evaluating your answer. Let's try another problem.",
            "waiting_for_input": False
        }
    
async def provide_targeted_feedback(state: StudentState) -> Dict[str, Any]:
    """
    Provides targeted feedback based on the error type, topic, and CPA phase.
    """
    print(f"Executing provide_targeted_feedback for error_type={state.last_evaluation}")

    if not state.last_evaluation:
        return {
            "action": "error",
            "error": "No evaluation available to provide feedback",
            "fallback_text": "Let's try a new problem."
        }

    error_type_enum = state.last_evaluation
    error_type_value = error_type_enum.value if hasattr(error_type_enum, 'value') else str(error_type_enum)
    topic = state.current_topic
    cpa_phase = state.current_cpa_phase

    problem_text = state.last_problem_details.get("problem", "") if state.last_problem_details else "N/A"
    last_message = get_last_user_message(state)
    user_answer = last_message.content if last_message else "Not available"

    try:
        feedback_template_path = os.path.join(PROMPTS_DIR, "feedback.prompty")

        if os.path.exists(feedback_template_path):
            feedback_text = await invoke_with_prompty(
                feedback_template_path,
                topic=topic,
                error_type=error_type_value,
                cpa_phase=cpa_phase
            )
        else:
            print(f"Warning: Prompty template not found at {feedback_template_path}. Using fallback.")
            system_message = f"""You are an expert math tutor specializing in the Singapore Math method, focused on teaching mathematics through the Concrete-Pictorial-Abstract (CPA) approach. Your goal is to guide the student towards a deep understanding of mathematical concepts, not just memorizing formulas. Provide constructive and specific feedback for a student who has made an error of type {error_type_value} on the topic {topic}. The feedback should be empathetic, specific about the error, clear on improvement, and adapted to the learning phase {cpa_phase}. Do not simply give the correct answer, but guide the student."""
            user_prompt = f"""The student made an '{error_type_value}' error on the topic '{topic}' during the '{cpa_phase}' phase.
            Problem context (optional): {problem_text}
            Student's incorrect answer (optional): {user_answer}
            Please provide guiding feedback."""
            feedback_text = await invoke_llm(user_prompt, system_message)

        image_url = None
        if error_type_enum == EvaluationOutcome.INCORRECT_CONCEPTUAL:
            img_prompt = f"Clear visual explanation of the math concept '{topic.replace('_', ' ')}', theme: {state.personalized_theme}"
            image_url = await generate_image(img_prompt)

        audio_url = await generate_speech(feedback_text)

        state.error_feedback_given_count += 1
        state.last_action_type = "provide_feedback"
        state.waiting_for_input = False

        add_message(state, "ai", feedback_text)

        return {
            "action": "present_content",
            "content_type": "feedback",
            "text": feedback_text,
            "image_url": image_url,
            "audio_url": audio_url,
            "requires_input": False,
            "feedback_type": error_type_value
        }

    except Exception as e:
        print(f"Error in provide_targeted_feedback: {e}")
        return {
            "action": "error",
            "error": f"Failed to generate feedback: {str(e)}",
            "fallback_text": "I couldn't generate specific feedback right now. Let's try another problem."
        }
    
async def simplify_instruction(state: StudentState) -> Dict[str, Any]:
    """
    Simplifies the instruction or reverts to theory based on consecutive errors.
    Handles potential string values for CPA phase and updates state correctly.
    """
    print(f"Executing simplify_instruction for consecutive_incorrect={state.consecutive_incorrect}")

    current_cpa_phase_value: str
    original_cpa_phase = state.current_cpa_phase

    if isinstance(original_cpa_phase, CPAPhase):
        current_cpa_phase_value = original_cpa_phase.value
    elif isinstance(original_cpa_phase, str):
        current_cpa_phase_value = original_cpa_phase
        try:
            original_cpa_phase = CPAPhase(original_cpa_phase)
        except ValueError:
             print(f"Warning: Invalid string value for CPA phase in simplify_instruction: '{original_cpa_phase}'. Defaulting.")
             original_cpa_phase = CPAPhase.CONCRETE
             current_cpa_phase_value = original_cpa_phase.value
    else:
        print(f"Warning: Unexpected type for current_cpa_phase in simplify_instruction: {type(original_cpa_phase)}. Defaulting.")
        original_cpa_phase = CPAPhase.CONCRETE
        current_cpa_phase_value = original_cpa_phase.value

    if state.consecutive_incorrect >= 5:
        if state.current_topic in state.theory_presented_for_topics:
            try:
                state.theory_presented_for_topics.remove(state.current_topic)
                print(f"Removed theory presentation flag for topic {state.current_topic}")
            except ValueError:
                pass

        new_cpa_phase_enum = original_cpa_phase

        if current_cpa_phase_value == CPAPhase.ABSTRACT.value:
            new_cpa_phase_enum = CPAPhase.PICTORIAL
            print("Stepping back CPA phase from Abstract to Pictorial")
        elif current_cpa_phase_value == CPAPhase.PICTORIAL.value:
            new_cpa_phase_enum = CPAPhase.CONCRETE
            print("Stepping back CPA phase from Pictorial to Concrete")
        else:
             print("Already at Concrete phase, cannot step back further.")

        state.current_cpa_phase = new_cpa_phase_enum
        state.last_action_type = "simplify_instruction_theory"
        state.waiting_for_input = False
        state.consecutive_incorrect = 0

        message = "It looks like we're having some trouble. Let's review the theory again to make sure the concepts are clear."
        add_message(state, "ai", message)
        audio_url = await generate_speech(message)

        return {
            "action": "present_content",
            "content_type": "system_message",
            "text": message,
            "audio_url": audio_url,
            "requires_input": False,
            "cpa_phase_changed_to": state.current_cpa_phase.value
        }
    else:
        old_mastery = state.topic_mastery.get(state.current_topic, 0.1)
        reduced_mastery = max(0.05, old_mastery * 0.7)
        state.topic_mastery[state.current_topic] = reduced_mastery
        print(f"Reduced mastery for {state.current_topic} from {old_mastery:.2f} to {reduced_mastery:.2f}")

        state.last_action_type = "simplify_instruction_easier"
        state.waiting_for_input = False

        message = "Don't worry! Let's try a slightly simpler exercise to practice."
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
    Checks if the student should advance to the next topic based on mastery.
    """
    print(f"Executing check_advance_topic for current_topic={state.current_topic}")

    current_topic = state.current_topic
    roadmap_id = current_topic.split('_')[0] if '_' in current_topic else current_topic

    next_topic_id = get_next_topic_id(roadmap_id, current_topic)

    if next_topic_id:
        roadmap = get_roadmap(roadmap_id)
        next_topic = roadmap.get_topic_by_id(next_topic_id) if roadmap else None

        if next_topic:
            state.current_topic = next_topic_id
            state.current_cpa_phase = CPAPhase.CONCRETE
            state.consecutive_correct = 0
            state.consecutive_incorrect = 0
            state.last_evaluation = None
            state.last_problem_details = None
            state.error_feedback_given_count = 0
            state.waiting_for_input = False

            if next_topic_id not in state.topic_mastery:
                state.topic_mastery[next_topic_id] = 0.1 

            state.last_action_type = "advance_topic"

            message = f"Congratulations! You have mastered the current topic. We will move on to the next topic: {next_topic.title}"
            add_message(state, "ai", message)

            audio_url = await generate_speech(message)

            return {
                "action": "topic_change",
                "text": message,
                "audio_url": audio_url,
                "old_topic": current_topic,
                "new_topic": next_topic_id,
                "new_topic_title": next_topic.title,
                "requires_input": False,
                "prompt_for_answer": False,
                "requires_continue": True,
                "is_final_step": False
            }

    message = f"Congratulations! You have completed all the topics in the {roadmap_id} course."
    add_message(state, "ai", message)

    audio_url = await generate_speech(message)

    return {
        "action": "course_completed",
        "text": message,
        "audio_url": audio_url,
        "requires_input": False,
        "is_final_step": True
    }
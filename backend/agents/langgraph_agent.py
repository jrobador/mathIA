"""
Implements the adaptive learning agent using LangGraph.
"""

from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
import uuid
import os
import traceback
from pydantic import BaseModel

# Import LangGraph components
from langgraph.graph import StateGraph, END
import json

# Import existing components
from models.student_state import (
    StudentState, get_current_mastery, initialize_state
)
from agents.functions import (
    determine_next_step, present_theory, present_guided_practice,
    present_independent_practice, evaluate_answer, provide_targeted_feedback,
    simplify_instruction, check_advance_topic
)
from models.curriculum import get_roadmap, get_all_roadmaps_info
from config import (
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_CHAT_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION, OPENAI_AVAILABLE
)

# Type definition for graph state
class GraphState(BaseModel):
    """State wrapper for LangGraph compatibility."""
    student_state: StudentState
    result: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None

# Node functions that wrap the existing functions
async def determine_next_node(state: GraphState) -> GraphState:
    """Determines the next action based on the current state."""
    student_state = state.student_state
    next_step = await determine_next_step(student_state)
    next_action = next_step.get("action")
    
    return GraphState(
        student_state=student_state,
        next_action=next_action,
        result=next_step
    )

async def present_theory_node(state: GraphState) -> GraphState:
    """Presents theory using existing function."""
    student_state = state.student_state
    result = await present_theory(student_state)
    
    # Return the state with the action result
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

async def present_guided_practice_node(state: GraphState) -> GraphState:
    """Presents guided practice using existing function."""
    student_state = state.student_state
    result = await present_guided_practice(student_state)
    
    # Return the state with the action result
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

async def present_independent_practice_node(state: GraphState) -> GraphState:
    """Presents independent practice using existing function."""
    student_state = state.student_state
    result = await present_independent_practice(student_state)
    
    # Return the state with the action result
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

async def provide_targeted_feedback_node(state: GraphState) -> GraphState:
    """Provides targeted feedback using existing function."""
    student_state = state.student_state
    result = await provide_targeted_feedback(student_state)
    
    # Return the state with the action result
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

async def simplify_instruction_node(state: GraphState) -> GraphState:
    """Simplifies instruction using existing function."""
    student_state = state.student_state
    result = await simplify_instruction(student_state)
    
    # Return the state with the action result
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

async def check_advance_topic_node(state: GraphState) -> GraphState:
    """Checks if topic should advance using existing function."""
    student_state = state.student_state
    result = await check_advance_topic(student_state)
    
    # Return the state with the action result
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

async def evaluate_answer_node(state: GraphState, user_answer: str) -> GraphState:
    """Evaluates user answer using existing function."""
    student_state = state.student_state
    result = await evaluate_answer(student_state, user_answer)
    
    return GraphState(
        student_state=student_state,
        result=result,
        next_action="next"
    )

# Router function to determine next node
def router(state: GraphState) -> Literal["present_theory", "present_guided_practice", 
                                         "present_independent_practice", "provide_targeted_feedback", 
                                         "simplify_instruction", "check_advance_topic", "next", "pause"]:
    """Routes to the next node based on the state."""
    student_state = state.student_state
    next_action = state.next_action
    
    # If waiting for input, pause the graph
    if student_state.waiting_for_input:
        return "pause"
    
    # If coming from a node that just executed, go back to decision node
    if next_action == "next":
        return "determine_next"
    
    # Map action names to node names
    action_to_node = {
        "present_theory": "present_theory",
        "present_guided_practice": "present_guided_practice",
        "present_independent_practice": "present_independent_practice",
        "provide_targeted_feedback": "provide_targeted_feedback",
        "simplify_instruction": "simplify_instruction",
        "check_advance_topic": "check_advance_topic",
        "pause": "pause"
    }
    
    return action_to_node.get(next_action, "determine_next")

def create_learning_graph():
    """Creates and compiles the LangGraph for the learning agent."""
    # Create the graph
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("determine_next", determine_next_node)
    graph.add_node("present_theory", present_theory_node)
    graph.add_node("present_guided_practice", present_guided_practice_node)
    graph.add_node("present_independent_practice", present_independent_practice_node)
    graph.add_node("provide_targeted_feedback", provide_targeted_feedback_node)
    graph.add_node("simplify_instruction", simplify_instruction_node)
    graph.add_node("check_advance_topic", check_advance_topic_node)
    
    # Add conditional edges
    graph.add_conditional_edges(
        "determine_next",
        lambda state: router(state),
        {
            "present_theory": "present_theory",
            "present_guided_practice": "present_guided_practice",
            "present_independent_practice": "present_independent_practice",
            "provide_targeted_feedback": "provide_targeted_feedback",
            "simplify_instruction": "simplify_instruction",
            "check_advance_topic": "check_advance_topic",
            "pause": END  # End the graph execution when pausing
        }
    )
    
    # Add edges from each node back to the router
    graph.add_edge("present_theory", "determine_next")
    graph.add_edge("present_guided_practice", "determine_next")
    graph.add_edge("present_independent_practice", "determine_next")
    graph.add_edge("provide_targeted_feedback", "determine_next")
    graph.add_edge("simplify_instruction", "determine_next")
    graph.add_edge("check_advance_topic", "determine_next")
    
    # Set the entry point
    graph.set_entry_point("determine_next")
    
    # Compile the graph
    return graph.compile()

class LangGraphAdaptiveLearningAgent:
    """
    Adaptive learning agent implementing the specified flowchart using LangGraph.
    Manages session state and orchestrates actions.
    """

    def __init__(self):
        """
        Initializes the agent with default configuration.
        """
        self.sessions: Dict[str, StudentState] = {}
        self.llm_config = None
        self.graph = create_learning_graph()

        if OPENAI_AVAILABLE:
            self.llm_config = {
                "config_list": [{
                    "model": AZURE_OPENAI_CHAT_DEPLOYMENT,
                    "api_key": AZURE_OPENAI_API_KEY,
                    "api_base": AZURE_OPENAI_ENDPOINT,
                    "api_type": "azure",
                    "api_version": AZURE_OPENAI_API_VERSION,
                }],
                "temperature": 0.2,
            }
            os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_API_KEY
            print("Azure OpenAI configured for agent.")
        else:
            print("Azure OpenAI not available, agent functions may be limited.")

        self.available_roadmaps = get_all_roadmaps_info()

    async def create_session(self, topic_id: str = "fractions_introduction",
                           personalized_theme: str = "space",
                           initial_mastery: float = 0.0,
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new session and executes the first step.

        Args:
            topic_id: ID of the topic to study.
            personalized_theme: Personalization theme.
            initial_mastery: Initial mastery level (0.0-1.0).
            user_id: User ID (optional).

        Returns:
            Dictionary with session_id and the result of the first action.
        """
        roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id
        roadmap = get_roadmap(roadmap_id)
        if not roadmap:
            raise ValueError(f"Roadmap with ID {roadmap_id} does not exist")

        topic = roadmap.get_topic_by_id(topic_id)
        current_topic_id = topic_id
        if not topic:
            first_topic = roadmap.topics[0] if roadmap.topics else None
            if not first_topic:
                raise ValueError(f"No topics available in roadmap {roadmap_id}")
            current_topic_id = first_topic.id
            print(f"Topic '{topic_id}' not found, starting with first topic: '{current_topic_id}'")

        session_id = str(uuid.uuid4())

        state = initialize_state(
            session_id=session_id,
            topic_id=current_topic_id,
            personalized_theme=personalized_theme,
            user_id=user_id
        )

        if initial_mastery > 0:
            state.topic_mastery[current_topic_id] = min(max(initial_mastery, 0.0), 1.0)

        self.sessions[session_id] = state
        print(f"Session created: {session_id} for topic {current_topic_id}")

        first_step_result = await self.process_step(session_id)

        return {
            "session_id": session_id,
            "initial_output": {
                "text": first_step_result.get("text", ""),
                "image_url": first_step_result.get("image_url"),
                "audio_url": first_step_result.get("audio_url"),
                "prompt_for_answer": first_step_result.get("requires_input", False),
                "evaluation": first_step_result.get("evaluation_type"),
                "is_final_step": first_step_result.get("is_final_step", False),
            },
            "initial_result": first_step_result,
            "state_metadata": self._get_state_metadata(state)
        }

    async def process_step(self, session_id: str) -> Dict[str, Any]:
        """
        Processes an agent step based on the current state using LangGraph.
        This function is called to start the session, when 'continue' is requested,
        or internally after an evaluation if no input is expected.

        Args:
            session_id: ID of the session.

        Returns:
            Result of the processed step (agent action).
        """
        state = self._get_session_state_object(session_id)
        if not state:
            return {"action": "error", "error": "Session not found"}

        state.updated_at = datetime.now()

        if state.waiting_for_input:
            print(f"Warning: process_step called for session {session_id} while waiting_for_input=True")
            return {
                "action": "pause",
                "message": "Waiting for user input.",
                "waiting_for_input": True,
                "state_metadata": self._get_state_metadata(state)
            }

        try:
            # Prepare the graph state
            graph_state = GraphState(student_state=state)
            
            # Run the graph
            final_state = await self.graph.ainvoke(graph_state)
            
            # Debug output
            print(f"DEBUG: Final state type: {type(final_state)}")
            print(f"DEBUG: Final state keys: {list(final_state.keys()) if hasattr(final_state, 'keys') else 'No keys method'}")
            
            # Direct access to the 'result' field in the return value
            if 'result' in final_state and final_state['result']:
                result = final_state['result']
                print(f"DEBUG: Found result in final_state['result']: {result.get('action', 'No action')}")
            else:
                # If no result is found, check the last_action_type in the student state
                print(f"DEBUG: No result found in final_state, using last_action_type: {state.last_action_type}")
                
                # Fallback result based on the last action performed
                if state.last_action_type == "present_theory":
                    # Find the last AI message which should contain the theory content
                    last_ai_message = next((msg for msg in reversed(state.messages) if msg.role == "ai"), None)
                    content = last_ai_message.content if last_ai_message else "Theory presented"
                    
                    result = {
                        "action": "present_content",
                        "content_type": "theory",
                        "text": content,
                        # Other fields might be in the state but not accessible here
                    }
                elif state.last_action_type == "present_guided_practice" or state.last_action_type == "present_independent_practice":
                    # Find the last AI message which should contain the practice content
                    last_ai_message = next((msg for msg in reversed(state.messages) if msg.role == "ai"), None)
                    content = last_ai_message.content if last_ai_message else f"{state.last_action_type} presented"
                    
                    # Get problem details if available
                    problem_details = state.last_problem_details or {}
                    
                    result = {
                        "action": "present_content",
                        "content_type": state.last_action_type.replace("present_", ""),
                        "text": content,
                        "requires_input": state.waiting_for_input,
                        # Other fields from problem_details if available
                        "image_url": problem_details.get("image_url"),
                        "audio_url": problem_details.get("audio_url"),
                    }
                else:
                    # Generic fallback
                    result = {
                        "action": state.last_action_type or "unknown",
                        "text": f"Action executed: {state.last_action_type or 'unknown'}"
                    }
            
            # Add metadata to the result
            result["state_metadata"] = self._get_state_metadata(state)
            result["waiting_for_input"] = state.waiting_for_input

            if not state.waiting_for_input:
                next_determination = await determine_next_step(state)
                result["next_action_hint"] = next_determination.get("action")

            return result

        except Exception as e:
            traceback.print_exc()
            state.last_action_type = "error"
            return {
                "action": "error",
                "error": f"Error processing step for session {session_id}: {str(e)}",
                "fallback_text": "An internal error occurred. Let's try again.",
                "state_metadata": self._get_state_metadata(state)
            }

    async def handle_user_input(self, session_id: str, user_input: str) -> List[Dict[str, Any]]:
        """
        Processes user input by first evaluating the answer, then
        returning BOTH the evaluation result and next step in a single response.
        This simplifies the frontend flow and eliminates race conditions.

        Args:
            session_id: ID of the session.
            user_input: User's answer input.

        Returns:
            A list containing:
            - The evaluation response
            - The next step response (if applicable)
        """
        print(f"[handle_user_input] START - session: {session_id}, input: '{user_input}'")
        state = self._get_session_state_object(session_id)
        if not state:
            print(f"[handle_user_input] ERROR - Session not found: {session_id}")
            return [{"action": "error", "error": "Session not found"}]

        state.updated_at = datetime.now()

        if not state.waiting_for_input:
            print(f"[handle_user_input] Warning: Received input for session {session_id} when agent state.waiting_for_input was False.")

        try:
            print(f"[handle_user_input] Calling evaluate_answer...")
            
            # Directly call evaluate_answer for user input
            eval_result = await evaluate_answer(state, user_input)
            print(f"[handle_user_input] evaluate_answer returned: {eval_result.get('action')}, correct: {eval_result.get('is_correct')}")

            eval_result["state_metadata"] = self._get_state_metadata(state)
            eval_result["waiting_for_input"] = state.waiting_for_input

            if eval_result.get("action") == "error":
                print(f"[handle_user_input] Error occurred within evaluate_answer. Returning error result.")
                eval_result["waiting_for_input"] = False
                return [eval_result]

            print(f"[handle_user_input] Automatically determining next step...")
            next_step_result = await self.process_step(session_id)

            print(f"[handle_user_input] SUCCESS - Returning BOTH evaluation and next step for session {session_id}.")
            return [eval_result, next_step_result]

        except Exception as e:
            print(f"[handle_user_input] UNEXPECTED ERROR for session {session_id}: {e}")
            traceback.print_exc()
            state.last_action_type = "error"
            state.waiting_for_input = False
            state.updated_at = datetime.now()
            return [{
                "action": "error",
                "error": f"Unexpected error handling user input: {str(e)}",
                "fallback_text": "An internal error occurred while processing your answer.",
                "waiting_for_input": False,
                "state_metadata": self._get_state_metadata(state)
            }]

    def _get_session_state_object(self, session_id: str) -> Optional[StudentState]:
        """Gets the StudentState object for a session."""
        return self.sessions.get(session_id)

    def _get_state_metadata(self, state: StudentState) -> Dict[str, Any]:
        """Extracts metadata from the state to include in responses."""
        cpa_phase = state.current_cpa_phase
        if hasattr(cpa_phase, 'value'): cpa_phase = cpa_phase.value

        last_evaluation = state.last_evaluation
        if hasattr(last_evaluation, 'value'): last_evaluation = last_evaluation.value

        return {
            "session_id": state.session_id,
            "current_topic": state.current_topic,
            "current_cpa_phase": cpa_phase,
            "mastery": get_current_mastery(state),
            "waiting_for_input": state.waiting_for_input,
            "consecutive_correct": state.consecutive_correct,
            "consecutive_incorrect": state.consecutive_incorrect,
            "last_action": state.last_action_type,
            "last_evaluation": last_evaluation,
            "personalized_theme": state.personalized_theme,
            "updated_at": state.updated_at.isoformat()
        }

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Gets the *serialized* state of a session to send to the client."""
        state = self._get_session_state_object(session_id)
        if state:
            try:
                state_dict = state.dict()

                if 'created_at' in state_dict and isinstance(state_dict['created_at'], datetime):
                    state_dict['created_at'] = state_dict['created_at'].isoformat()
                if 'updated_at' in state_dict and isinstance(state_dict['updated_at'], datetime):
                    state_dict['updated_at'] = state_dict['updated_at'].isoformat()

                state_dict['message_count'] = len(state.messages)
                if 'messages' in state_dict:
                    del state_dict['messages']

                return state_dict
            except Exception as e:
                 print(f"Error serializing state for session {session_id}: {e}")
                 return self._get_state_metadata(state)
        return None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Gets basic info of active sessions."""
        return [self._get_state_metadata(state) for state in self.sessions.values()]


    def cleanup_inactive_sessions(self, max_age_minutes: int = 60) -> int:
        """Cleans up inactive sessions."""
        now = datetime.now()
        sessions_to_remove = [
            session_id for session_id, state in self.sessions.items()
            if (now - state.updated_at).total_seconds() / 60 > max_age_minutes
        ]
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            print(f"Cleaned up inactive session: {session_id}")
        return len(sessions_to_remove)

    def get_available_roadmaps(self) -> List[Dict[str, Any]]:
        """Gets the list of available roadmaps."""
        return self.available_roadmaps
"""
Implements the adaptive learning agent.
It acts as the main class that orchestrates the learning flow.
"""

from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
import os
import traceback 

from models.student_state import (
    StudentState, initialize_state,
    get_current_mastery
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

AgentResponse = Dict[str, Any]
SessionCreationResponse = Dict[str, Any]
UserInputHandlingResponse = List[AgentResponse]

class AdaptiveLearningAgent:
    """
    Adaptive learning agent implementing the specified flowchart.
    Manages session state and orchestrates actions.
    """

    def __init__(self):
        """
        Initializes the agent with default configuration.
        """
        self.sessions: Dict[str, StudentState] = {}
        self.llm_config = None

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
                           user_id: Optional[str] = None) -> SessionCreationResponse:
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

    async def process_step(self, session_id: str) -> AgentResponse:
        """
        Processes an agent step based on the current state.
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
            next_step_decision = await determine_next_step(state)
            action_name = next_step_decision.get("action")

            if not action_name or action_name == "pause":
                state.waiting_for_input = True
                return {
                    "action": "pause",
                    "message": "Agent determined to pause.",
                    "waiting_for_input": True,
                    "state_metadata": self._get_state_metadata(state)
                }

            result = await self._execute_action(action_name, state)
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

    async def handle_user_input(self, session_id: str, user_input: str) -> UserInputHandlingResponse:
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

    async def _execute_action(self, action: str, state: StudentState) -> AgentResponse:
        """
        Helper to execute a specific action based on its name.
        Action functions are responsible for updating the state,
        including `state.waiting_for_input`.

        Args:
            action: Name of the action to execute (must match a function in agents.functions).
            state: Current session state.

        Returns:
            Result of the executed action.
        """
        result: AgentResponse = {}
        action_function = None

        action_map = {
            "present_theory": present_theory,
            "present_guided_practice": present_guided_practice,
            "present_independent_practice": present_independent_practice,
            "provide_targeted_feedback": provide_targeted_feedback,
            "simplify_instruction": simplify_instruction,
            "check_advance_topic": check_advance_topic,
        }

        action_function = action_map.get(action)

        if action_function:
            print(f"Executing action: {action} for session {state.session_id}")
            try:
                result = await action_function(state)
                if "action" not in result:
                    result["action"] = "executed_step"
                result["executed_action_name"] = action

            except Exception as e:
                traceback.print_exc()
                result = {
                    "action": "error",
                    "error": f"Error executing action '{action}': {str(e)}",
                    "executed_action_name": action
                }
                state.last_action_type = "error"
        else:
            print(f"Error: Unknown action requested: {action}")
            result = {"action": "error", "error": f"Unknown action: {action}"}
            state.last_action_type = "error"

        return result

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
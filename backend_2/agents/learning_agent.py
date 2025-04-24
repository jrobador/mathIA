# backend_2/agents/learning_agent.py

"""
Implementa el agente educativo adaptativo.
Actúa como la clase principal que orquesta el flujo de aprendizaje.
"""

from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
import os

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

# Define consistent response structures
AgentResponse = Dict[str, Any]
SessionCreationResponse = Dict[str, Any]
UserInputHandlingResponse = List[AgentResponse] # Can return multiple steps (eval + next action)

class AdaptiveLearningAgent:
    """
    Agente adaptativo de aprendizaje que implementa el diagrama de flujo especificado.
    Gestiona el estado de la sesión y orquesta las acciones.
    """

    def __init__(self):
        """
        Inicializa el agente con configuración por defecto.
        """
        self.sessions: Dict[str, StudentState] = {}  # Almacena las sesiones activas
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
            os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_API_KEY # Fallback for some libraries
            print("Azure OpenAI configured for agent.")
        else:
            print("Azure OpenAI not available, agent functions may be limited.")

        # Cargar información de roadmaps disponibles
        self.available_roadmaps = get_all_roadmaps_info()

    async def create_session(self, topic_id: str = "fractions_introduction",
                           personalized_theme: str = "space",
                           initial_mastery: float = 0.0,
                           user_id: Optional[str] = None) -> SessionCreationResponse:
        """
        Crea una nueva sesión y ejecuta el primer paso.

        Args:
            topic_id: ID del tema a estudiar
            personalized_theme: Tema de personalización
            initial_mastery: Nivel inicial de dominio (0.0-1.0)
            user_id: ID del usuario (opcional)

        Returns:
            Diccionario con session_id y el resultado de la primera acción.
        """
        # Validar que el tema exista
        roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id
        roadmap = get_roadmap(roadmap_id)
        if not roadmap:
            raise ValueError(f"El roadmap con ID {roadmap_id} no existe")

        # Ensure the specific topic exists, or default to the first topic
        topic = roadmap.get_topic_by_id(topic_id)
        current_topic_id = topic_id
        if not topic:
            first_topic = roadmap.topics[0] if roadmap.topics else None
            if not first_topic:
                raise ValueError(f"No hay temas disponibles en el roadmap {roadmap_id}")
            current_topic_id = first_topic.id
            print(f"Topic '{topic_id}' not found, starting with first topic: '{current_topic_id}'")


        # Crear ID de sesión
        session_id = str(uuid.uuid4())

        # Crear estado inicial
        state = initialize_state(
            session_id=session_id,
            topic_id=current_topic_id, # Use validated/defaulted topic_id
            personalized_theme=personalized_theme,
            user_id=user_id
        )

        # Inicializar mastery si se proporciona
        if initial_mastery > 0:
            state.topic_mastery[current_topic_id] = min(max(initial_mastery, 0.0), 1.0)

        # Almacenar la sesión
        self.sessions[session_id] = state
        print(f"Session created: {session_id} for topic {current_topic_id}")

        # Procesar primer paso para iniciar la sesión
        first_step_result = await self.process_step(session_id)

        return {
            "session_id": session_id,
            "initial_output": {  # Add this structure
                "text": first_step_result.get("text", ""),
                "image_url": first_step_result.get("image_url"),
                "audio_url": first_step_result.get("audio_url"),
                "prompt_for_answer": first_step_result.get("requires_input", False),
                "evaluation": first_step_result.get("evaluation_type"),
                "is_final_step": first_step_result.get("is_final_step", False),
            },
            "initial_result": first_step_result,  # Keep this for backward compatibility
            "state_metadata": self._get_state_metadata(state)
        }

    async def process_step(self, session_id: str) -> AgentResponse:
        """
        Procesa un paso del agente basado en el estado actual.
        Esta función es llamada para iniciar la sesión, cuando se pide 'continue',
        o internamente después de una evaluación si no se espera input.

        Args:
            session_id: ID de la sesión

        Returns:
            Resultado del paso procesado (acción del agente).
        """
        state = self._get_session_state_object(session_id)
        if not state:
            return {"action": "error", "error": "Sesión no encontrada"}

        # Marcar la sesión como actualizada
        state.updated_at = datetime.now()

        # Si está esperando input, devolver un indicador de pausa
        # (Esto generalmente no debería ocurrir si process_step se llama correctamente)
        if state.waiting_for_input:
            print(f"Warning: process_step called for session {session_id} while waiting_for_input=True")
            return {
                "action": "pause",
                "message": "Waiting for user input.",
                "waiting_for_input": True,
                "state_metadata": self._get_state_metadata(state)
            }

        try:
            # Determinar el próximo paso
            next_step_decision = await determine_next_step(state)
            action_name = next_step_decision.get("action")

            if not action_name or action_name == "pause":
                 # Si la determinación es pausar (quizás por un estado inesperado), pausamos.
                state.waiting_for_input = True # Ensure consistency
                return {
                    "action": "pause",
                    "message": "Agent determined to pause.",
                    "waiting_for_input": True,
                    "state_metadata": self._get_state_metadata(state)
                }

            # Ejecutar la acción determinada
            result = await self._execute_action(action_name, state)

            # Añadir metadatos del estado actualizado a la respuesta
            result["state_metadata"] = self._get_state_metadata(state)

            # Ensure waiting_for_input status from state is reflected in result
            result["waiting_for_input"] = state.waiting_for_input

            # Si después de ejecutar la acción, *aún no* se espera input,
            # podemos predecir la siguiente acción para información del frontend.
            if not state.waiting_for_input:
                 next_determination = await determine_next_step(state)
                 result["next_action_hint"] = next_determination.get("action")

            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            state.last_action_type = "error"
            return {
                "action": "error",
                "error": f"Error processing step for session {session_id}: {str(e)}",
                "fallback_text": "Hubo un error interno. Intentemos de nuevo.",
                "state_metadata": self._get_state_metadata(state)
            }

    async def handle_user_input(self, session_id: str, user_input: str) -> UserInputHandlingResponse:
        """
        Procesa la entrada del usuario, evalúa la respuesta, y si no se
        requiere más input, ejecuta el siguiente paso del agente automáticamente.

        Args:
            session_id: ID de la sesión
            user_input: Entrada del usuario

        Returns:
            Una lista de respuestas del agente. Típicamente contendrá:
            1. El resultado de la evaluación.
            2. (Si aplica) El resultado del siguiente paso del agente.
        """
        state = self._get_session_state_object(session_id)
        if not state:
            return [{"action": "error", "error": "Sesión no encontrada"}]

        # Marcar la sesión como actualizada
        state.updated_at = datetime.now()

        # Verificar si está esperando input
        if not state.waiting_for_input:
             print(f"Warning: Received user input for session {session_id} when not waiting.")
             # Decide how to handle this - ignore, error, or process anyway? Let's process anyway for robustness.
             # return [{"action": "error", "error": "El agente no está esperando respuesta", "state_metadata": self._get_state_metadata(state)}]


        results: UserInputHandlingResponse = []

        try:
            # 1. Evaluar la respuesta del usuario
            # Note: evaluate_answer should set state.waiting_for_input = False
            eval_result = await evaluate_answer(state, user_input)
            eval_result["state_metadata"] = self._get_state_metadata(state) # Add metadata
            eval_result["waiting_for_input"] = state.waiting_for_input # Reflect state after eval
            results.append(eval_result)

            # Check for evaluation errors before proceeding
            if eval_result.get("action") == "error":
                return results # Return immediately if evaluation failed

            # 2. Si la evaluación NO resultó en esperar input, procesar el siguiente paso
            if not state.waiting_for_input:
                print(f"Session {session_id}: Not waiting for input after evaluation, processing next step.")
                next_step_result = await self.process_step(session_id)
                # Ensure metadata and waiting status are updated for the second step too
                next_step_result["state_metadata"] = self._get_state_metadata(state)
                next_step_result["waiting_for_input"] = state.waiting_for_input
                results.append(next_step_result)
            else:
                 print(f"Session {session_id}: Waiting for input after evaluation.")


            return results

        except Exception as e:
            import traceback
            traceback.print_exc()
            state.last_action_type = "error"
            # Return an error message as the last item in the list
            results.append({
                "action": "error",
                "error": f"Error handling user input for session {session_id}: {str(e)}",
                "fallback_text": "Hubo un error procesando tu respuesta.",
                "state_metadata": self._get_state_metadata(state)
            })
            return results


    async def _execute_action(self, action: str, state: StudentState) -> AgentResponse:
        """
        Helper para ejecutar una acción específica basada en el nombre.
        Las funciones de acción son responsables de actualizar el estado,
        incluyendo `state.waiting_for_input`.

        Args:
            action: Nombre de la acción a ejecutar (debe coincidir con una función en agents.functions)
            state: Estado actual de la sesión

        Returns:
            Resultado de la acción ejecutada
        """
        result: AgentResponse = {}
        action_function = None

        # Mapeo de nombres de acción a funciones
        action_map = {
            "present_theory": present_theory,
            "present_guided_practice": present_guided_practice,
            "present_independent_practice": present_independent_practice,
            "provide_targeted_feedback": provide_targeted_feedback,
            "simplify_instruction": simplify_instruction,
            "check_advance_topic": check_advance_topic,
            # evaluate_answer is called directly in handle_user_input
        }

        action_function = action_map.get(action)

        if action_function:
            print(f"Executing action: {action} for session {state.session_id}")
            try:
                result = await action_function(state)
                # Ensure action name is part of the result for clarity
                if "action" not in result:
                    result["action"] = "executed_step" # Provide a default if missing
                result["executed_action_name"] = action # Add the name of the function executed

            except Exception as e:
                import traceback
                traceback.print_exc()
                result = {
                    "action": "error",
                    "error": f"Error ejecutando la acción '{action}': {str(e)}",
                    "executed_action_name": action
                }
                state.last_action_type = "error" # Update state on error
        else:
            print(f"Error: Acción desconocida solicitada: {action}")
            result = {"action": "error", "error": f"Acción desconocida: {action}"}
            state.last_action_type = "error"

        return result

    def _get_session_state_object(self, session_id: str) -> Optional[StudentState]:
        """Obtiene el objeto StudentState para una sesión."""
        return self.sessions.get(session_id)

    def _get_state_metadata(self, state: StudentState) -> Dict[str, Any]:
        """Extrae metadatos del estado para incluir en respuestas."""
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
            "updated_at": state.updated_at.isoformat() # Added timestamp
        }

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado *serializado* de una sesión para enviar al cliente."""
        state = self._get_session_state_object(session_id)
        if state:
            # Use Pydantic's serialization or manually build the dict
            # Ensure enums are converted to their values
            state_dict = state.dict() # Use Pydantic's dict() method

            # --- Explicitly convert datetime objects to ISO strings ---
            if 'created_at' in state_dict and isinstance(state_dict['created_at'], datetime):
                state_dict['created_at'] = state_dict['created_at'].isoformat()
            if 'updated_at' in state_dict and isinstance(state_dict['updated_at'], datetime):
                state_dict['updated_at'] = state_dict['updated_at'].isoformat()

            # If message history were included, timestamps would need conversion too:
            # if 'messages' in state_dict:
            #     for msg in state_dict['messages']:
            #         if 'timestamp' in msg and isinstance(msg['timestamp'], datetime):
            #             msg['timestamp'] = msg['timestamp'].isoformat()
            # --- End datetime conversion ---

            # Or just add message count
            state_dict['message_count'] = len(state.messages) # Use state.messages before potential deletion
            if 'messages' in state_dict:
                del state_dict['messages'] # Remove potentially large list

            return state_dict
        return None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Obtiene info básica de sesiones activas."""
        return [self._get_state_metadata(state) for state in self.sessions.values()]


    def cleanup_inactive_sessions(self, max_age_minutes: int = 60) -> int: # Increased default timeout
        """Limpia sesiones inactivas."""
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
        """Obtiene la lista de roadmaps disponibles."""
        return self.available_roadmaps
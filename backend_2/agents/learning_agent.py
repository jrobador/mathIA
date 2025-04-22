"""
Implementa el agente educativo adaptativo usando AutoGen.
Actúa como la clase principal que orquesta el flujo de aprendizaje.
"""

from typing import Dict, Any, Optional, List, Tuple
import uuid
import autogen
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

class AdaptiveLearningAgent:
    """
    Agente adaptativo de aprendizaje que implementa el diagrama de flujo especificado.
    Integra AutoGen para la generación de contenido educativo.
    """
    
    def __init__(self):
        """
        Inicializa el agente con configuración por defecto.
        """
        self.sessions = {}  # Almacena las sesiones activas
        
        # Configurar el agente de AutoGen para generación de contenido
        # Solo crear el agente si OpenAI está disponible
        self.content_agent = None
        
        if OPENAI_AVAILABLE:
            # Use Azure OpenAI configuration
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
            
            # Set OpenAI API key as environment variable as a fallback
            os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_API_KEY
            
            try:
                # Create agent only if OpenAI is available
                self.content_agent = autogen.AssistantAgent(
                    name="content_tutor",
                    llm_config=self.llm_config,
                    system_message="""Eres un tutor educativo experto que genera contenido adaptativo.
                    Tu objetivo es explicar conceptos de manera clara y proporcionar problemas de práctica apropiados.
                    Adapta tu respuesta según el nivel de dominio del estudiante y el tema."""
                )
                print("AutoGen content agent initialized successfully")
            except Exception as e:
                print(f"Warning: Could not initialize AutoGen agent: {e}")
                # Continue without AutoGen agent - will use alternative methods
        else:
            print("Azure OpenAI not available, AutoGen content agent will not be used")
        
        # Cargar información de roadmaps disponibles
        self.available_roadmaps = get_all_roadmaps_info()
    
    async def create_session(self, topic_id: str = "fractions_introduction", 
                           personalized_theme: str = "space", 
                           initial_mastery: float = 0.0, 
                           user_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Crea una nueva sesión para un tema específico
        
        Args:
            topic_id: ID del tema a estudiar
            personalized_theme: Tema de personalización
            initial_mastery: Nivel inicial de dominio (0.0-1.0)
            user_id: ID del usuario (opcional)
            
        Returns:
            Tupla con (ID de sesión, resultado de la primera acción)
        """
        # Validar que el tema exista
        roadmap_id = topic_id.split('_')[0] if '_' in topic_id else topic_id
        roadmap = get_roadmap(roadmap_id)
        if not roadmap:
            raise ValueError(f"El roadmap con ID {roadmap_id} no existe")
        
        topic = roadmap.get_topic_by_id(topic_id)
        if not topic:
            # Si el topic específico no existe, usar el primer tema del roadmap
            topic_id = roadmap.topics[0].id if roadmap.topics else None
            if not topic_id:
                raise ValueError(f"No hay temas disponibles en el roadmap {roadmap_id}")
        
        # Crear ID de sesión
        session_id = str(uuid.uuid4())
        
        # Crear estado inicial
        state = initialize_state(
            session_id=session_id,
            topic_id=topic_id,
            personalized_theme=personalized_theme,
            user_id=user_id
        )
        
        # Inicializar mastery si se proporciona
        if initial_mastery > 0:
            state.topic_mastery[topic_id] = min(initial_mastery, 1.0)
        
        # Almacenar la sesión
        self.sessions[session_id] = state
        
        # Procesar primer paso para iniciar la sesión
        result = await self.process_step(session_id)
        
        return session_id, result
    
    async def process_step(self, session_id: str) -> Dict[str, Any]:
        """
        Procesa un paso del agente basado en el estado actual
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Resultado del paso procesado
        """
        # Verificar que la sesión existe
        if session_id not in self.sessions:
            return {"error": "Sesión no encontrada"}
        
        # Obtener el estado actual
        state = self.sessions[session_id]
        
        # Si está esperando input, devolver un indicador de pausa
        if state.waiting_for_input:
            return {
                "action": "pause",
                "waiting_for_input": True,
                "state_metadata": self._get_state_metadata(state)
            }
        
        try:
            # Determinar el próximo paso
            next_step_result = await determine_next_step(state)
            
            # Ejecutar la acción determinada
            action = next_step_result.get("action")
            if action == "pause":
                # Si debe pausar, devolver un resultado vacío
                return {
                    "action": "pause",
                    "waiting_for_input": True,
                    "state_metadata": self._get_state_metadata(state)
                }
            else:
                # Ejecutar la acción correspondiente
                result = await self._execute_action(action, state)
                
                # Añadir metadatos del estado actualizado
                result["state_metadata"] = self._get_state_metadata(state)
                
                # Si la acción configura waiting_for_input, reflejarlo en la respuesta
                if state.waiting_for_input:
                    result["waiting_for_input"] = True
                
                # Si no está esperando input, determinar el siguiente paso (similar a LangGraph)
                if not state.waiting_for_input:
                    next_determination = await determine_next_step(state)
                    result["next_action"] = next_determination.get("action")
                
                return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # Manejar errores de manera uniforme
            state.last_action_type = "error"
            return {
                "action": "error",
                "error": str(e),
                "fallback_text": f"Hubo un error procesando tu solicitud. Intentemos un enfoque diferente.",
                "state_metadata": self._get_state_metadata(state)
            }
    
    async def process_user_input(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """
        Procesa la entrada del usuario para una sesión existente
        
        Args:
            session_id: ID de la sesión
            user_input: Entrada del usuario
            
        Returns:
            Resultado del procesamiento
        """
        # Verificar que la sesión existe
        if session_id not in self.sessions:
            return {"error": "Sesión no encontrada"}
        
        # Obtener el estado actual
        state = self.sessions[session_id]
        
        # Verificar si está esperando input
        if not state.waiting_for_input:
            return {"error": "El agente no está esperando respuesta", "state_metadata": self._get_state_metadata(state)}
        
        try:
            # Evaluar la respuesta
            eval_result = await evaluate_answer(state, user_input)
            
            # Marcar que ya no está esperando input
            state.waiting_for_input = False
            
            # Añadir metadatos del estado actualizado
            eval_result["state_metadata"] = self._get_state_metadata(state)
            
            # Determinar el siguiente paso (similar a LangGraph)
            if not state.waiting_for_input:
                next_determination = await determine_next_step(state)
                eval_result["next_action"] = next_determination.get("action")
            
            return eval_result
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # Manejar errores de manera uniforme
            state.last_action_type = "error"
            return {
                "action": "error",
                "error": str(e),
                "fallback_text": f"Hubo un error evaluando tu respuesta. Intentemos un enfoque diferente.",
                "state_metadata": self._get_state_metadata(state)
            }
    
    async def _execute_action(self, action: str, state: StudentState) -> Dict[str, Any]:
        """
        Ejecuta una acción específica del agente
        
        Args:
            action: Nombre de la acción a ejecutar
            state: Estado actual del agente
            
        Returns:
            Resultado de la acción ejecutada
        """
        result = {}
        
        try:
            if action == "present_theory":
                result = await present_theory(state)
                
            elif action == "present_guided_practice":
                result = await present_guided_practice(state)
                
            elif action == "present_independent_practice":
                result = await present_independent_practice(state)
                
            elif action == "provide_targeted_feedback":
                result = await provide_targeted_feedback(state)
                
            elif action == "simplify_instruction":
                result = await simplify_instruction(state)
                
            elif action == "check_advance_topic":
                result = await check_advance_topic(state)
                
            else:
                result = {"error": f"Acción desconocida: {action}"}
            
            # Añadir consistency con LangGraph - añadir un campo "next_node"
            result["next_node"] = "determine_next_step"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = {"error": f"Error ejecutando {action}: {str(e)}"}
        
        return result
    
    def _get_state_metadata(self, state: StudentState) -> Dict[str, Any]:
        """
        Extrae metadatos del estado actual para incluir en la respuesta
        
        Args:
            state: Estado actual del agente
            
        Returns:
            Diccionario con metadatos relevantes
        """
        # Get current_cpa_phase value - handle both enum and string values
        cpa_phase = state.current_cpa_phase
        if hasattr(cpa_phase, 'value'):
            # It's an enum, extract the value
            cpa_phase = cpa_phase.value
        
        # Get last_evaluation value - handle both enum and string values
        last_evaluation = state.last_evaluation
        if hasattr(last_evaluation, 'value'):
            # It's an enum, extract the value
            last_evaluation = last_evaluation.value
        
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
            "personalized_theme": state.personalized_theme
        }
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado actual de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Estado serializado o None si no existe
        """
        if session_id in self.sessions:
            state = self.sessions[session_id]
            return {
                "session_id": state.session_id,
                "user_id": state.user_id,
                "current_topic": state.current_topic,
                "current_cpa_phase": state.current_cpa_phase.value,
                "topic_mastery": state.topic_mastery,
                "consecutive_correct": state.consecutive_correct,
                "consecutive_incorrect": state.consecutive_incorrect,
                "waiting_for_input": state.waiting_for_input,
                "last_action_type": state.last_action_type,
                "last_evaluation": state.last_evaluation.value if state.last_evaluation else None,
                "message_count": len(state.messages),
                "personalized_theme": state.personalized_theme,
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            }
        return None
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Obtiene información básica de todas las sesiones activas
        
        Returns:
            Lista con información resumida de las sesiones
        """
        sessions_info = []
        for session_id, state in self.sessions.items():
            sessions_info.append({
                "session_id": session_id,
                "user_id": state.user_id,
                "current_topic": state.current_topic,
                "mastery": get_current_mastery(state),
                "waiting_for_input": state.waiting_for_input,
                "updated_at": state.updated_at.isoformat()
            })
        return sessions_info
    
    def cleanup_inactive_sessions(self, max_age_minutes: int = 30) -> int:
        """
        Limpia las sesiones inactivas
        
        Args:
            max_age_minutes: Tiempo máximo de inactividad en minutos
            
        Returns:
            Número de sesiones eliminadas
        """
        now = datetime.now()
        sessions_to_remove = []
        
        for session_id, state in self.sessions.items():
            age_minutes = (now - state.updated_at).total_seconds() / 60
            if age_minutes > max_age_minutes:
                sessions_to_remove.append(session_id)
        
        # Eliminar las sesiones inactivas
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        return len(sessions_to_remove)
    
    def get_available_roadmaps(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de roadmaps disponibles
        
        Returns:
            Lista de información de roadmaps
        """
        return self.available_roadmaps
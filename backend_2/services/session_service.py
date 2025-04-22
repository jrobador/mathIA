from typing import Dict, Any, Optional, List
import time
import json
from agents.learning_agent import AdaptiveLearningAgent
import config

class SessionService:
    """
    Servicio para gestionar las sesiones de aprendizaje
    """
    
    def __init__(self, curriculum_path: str = "data/curriculum.json"):
        """
        Inicializa el servicio de sesiones
        
        Args:
            curriculum_path: Ruta al archivo JSON del currículo
        """
        self.active_sessions = {}  # Mapeo de ID de sesión a instancia de agente
        self.session_data = {}  # Datos adicionales de sesión
        self.curriculum_data = self._load_curriculum(curriculum_path)
        
        # Crear agente principal
        self.learning_agent = AdaptiveLearningAgent(self.curriculum_data)
    
    def _load_curriculum(self, curriculum_path: str) -> Dict[str, Any]:
        """
        Carga los datos del currículo desde un archivo JSON
        
        Args:
            curriculum_path: Ruta al archivo JSON
            
        Returns:
            Datos del currículo
        """
        try:
            with open(curriculum_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            # Si hay error, devolver un currículo vacío
            print(f"Error al cargar el currículo: {e}")
            return {"topics": []}
    
    def create_session(self, topic_id: str, user_id: Optional[str] = None, 
                      initial_mastery: float = 0.0) -> Dict[str, Any]:
        """
        Crea una nueva sesión de aprendizaje
        
        Args:
            topic_id: ID del tema a estudiar
            user_id: ID del usuario (opcional)
            initial_mastery: Nivel inicial de dominio
            
        Returns:
            Datos de la sesión creada
        """
        try:
            # Crear sesión en el agente
            session_id = self.learning_agent.create_session(
                topic_id=topic_id,
                initial_mastery=initial_mastery,
                user_id=user_id
            )
            
            # Almacenar timestamp para control de tiempo de sesión
            self.session_data[session_id] = {
                "created_at": time.time(),
                "last_active": time.time(),
                "user_id": user_id
            }
            
            # Obtener estado inicial de la sesión
            state = self.learning_agent.get_session_state(session_id)
            
            # Procesar primer paso para iniciar la sesión
            first_step = self.learning_agent.process_step(session_id)
            
            return {
                "session_id": session_id,
                "topic_id": topic_id,
                "state": state,
                "content": first_step
            }
            
        except Exception as e:
            return {"error": f"Error al crear la sesión: {str(e)}"}
    
    def process_user_input(self, session_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa la entrada del usuario para una sesión
        
        Args:
            session_id: ID de la sesión
            user_input: Entrada del usuario
            
        Returns:
            Resultado del procesamiento
        """
        try:
            # Verificar que la sesión existe
            if session_id not in self.session_data:
                return {"error": "Sesión no encontrada"}
            
            # Actualizar timestamp de actividad
            self.session_data[session_id]["last_active"] = time.time()
            
            # Procesar la entrada con el agente
            result = self.learning_agent.process_step(session_id, user_input)
            
            return result
            
        except Exception as e:
            return {"error": f"Error al procesar la entrada: {str(e)}"}
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Estado de la sesión
        """
        try:
            # Verificar que la sesión existe
            if session_id not in self.session_data:
                return {"error": "Sesión no encontrada"}
            
            # Obtener estado de la sesión
            state = self.learning_agent.get_session_state(session_id)
            
            if not state:
                return {"error": "No se pudo obtener el estado de la sesión"}
            
            # Añadir metadatos de la sesión
            session_info = self.session_data[session_id]
            state["session_duration"] = time.time() - session_info["created_at"]
            state["last_active"] = session_info["last_active"]
            
            return state
            
        except Exception as e:
            return {"error": f"Error al obtener el estado: {str(e)}"}
    
    def reset_session(self, session_id: str) -> Dict[str, Any]:
        """
        Reinicia una sesión a su estado inicial
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Resultado del reinicio
        """
        try:
            # Verificar que la sesión existe
            if session_id not in self.session_data:
                return {"error": "Sesión no encontrada"}
            
            # Reiniciar la sesión
            result = self.learning_agent.reset_session(session_id)
            
            if not result:
                return {"error": "No se pudo reiniciar la sesión"}
            
            # Actualizar timestamp de actividad
            self.session_data[session_id]["last_active"] = time.time()
            
            # Obtener nuevo estado
            state = self.learning_agent.get_session_state(session_id)
            
            # Procesar primer paso para reiniciar la sesión
            first_step = self.learning_agent.process_step(session_id)
            
            return {
                "session_id": session_id,
                "state": state,
                "content": first_step,
                "message": "Sesión reiniciada correctamente"
            }
            
        except Exception as e:
            return {"error": f"Error al reiniciar la sesión: {str(e)}"}
    
    def cleanup_inactive_sessions(self, max_idle_time: int = config.SESSION_TIMEOUT) -> int:
        """
        Limpia las sesiones inactivas
        
        Args:
            max_idle_time: Tiempo máximo de inactividad en segundos
            
        Returns:
            Número de sesiones eliminadas
        """
        current_time = time.time()
        sessions_to_remove = []
        
        # Identificar sesiones inactivas
        for session_id, data in self.session_data.items():
            if current_time - data["last_active"] > max_idle_time:
                sessions_to_remove.append(session_id)
        
        # Eliminar sesiones inactivas
        for session_id in sessions_to_remove:
            del self.session_data[session_id]
        
        return len(sessions_to_remove)
    
    def get_topics(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de temas disponibles
        
        Returns:
            Lista de temas
        """
        topics = self.curriculum_data.get("topics", [])
        # Devolver solo información básica de los temas
        return [
            {
                "id": topic.get("id"),
                "name": topic.get("name"),
                "description": topic.get("description", ""),
                "difficulty": topic.get("difficulty", 1)
            }
            for topic in topics
        ]
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class RoadmapTopic(BaseModel):
    """
    Representa un tema dentro de un roadmap de aprendizaje.
    """
    id: str
    title: str
    description: str
    cpa_phases: List[str] = ["Concrete", "Pictorial", "Abstract"]
    prerequisites: List[str] = []
    required_mastery: float = 0.8
    practice_problems_min: int = 3
    subtopics: List[str] = []

class LearningRoadmap(BaseModel):
    """
    Define un roadmap completo de aprendizaje con una secuencia de temas.
    """
    id: str
    title: str
    description: str
    topics: List[RoadmapTopic]
    
    def get_topic_ids(self) -> List[str]:
        """Retorna la lista de IDs de temas en el roadmap."""
        return [topic.id for topic in self.topics]
    
    def get_topic_by_id(self, topic_id: str) -> Optional[RoadmapTopic]:
        """Encuentra un tema por su ID."""
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        return None
    
    def get_next_topic(self, current_topic_id: str) -> Optional[RoadmapTopic]:
        """Obtiene el siguiente tema en la secuencia."""
        topic_ids = self.get_topic_ids()
        try:
            current_index = topic_ids.index(current_topic_id)
            if current_index < len(topic_ids) - 1:
                next_id = topic_ids[current_index + 1]
                return self.get_topic_by_id(next_id)
        except ValueError:
            pass
        return None

# Importar las definiciones de roadmaps desde el archivo original
from data.roadmaps import AVAILABLE_ROADMAPS

def get_roadmap(roadmap_id: str) -> Optional[LearningRoadmap]:
    """
    Obtiene un roadmap por su ID.
    
    Args:
        roadmap_id: ID del roadmap a recuperar.
    
    Returns:
        LearningRoadmap o None si no existe.
    """
    roadmap_data = AVAILABLE_ROADMAPS.get(roadmap_id)
    if roadmap_data:
        # Convertir el roadmap del formato original al nuevo formato Pydantic
        topics = [
            RoadmapTopic(
                id=topic.id,
                title=topic.title,
                description=topic.description,
                cpa_phases=topic.cpa_phases,
                prerequisites=topic.prerequisites,
                required_mastery=topic.required_mastery,
                practice_problems_min=topic.practice_problems_min,
                subtopics=topic.subtopics
            ) for topic in roadmap_data.topics
        ]
        
        return LearningRoadmap(
            id=roadmap_data.id,
            title=roadmap_data.title,
            description=roadmap_data.description,
            topics=topics
        )
    return None

def get_topic_sequence(roadmap_id: str) -> List[str]:
    """
    Obtiene la secuencia de IDs de temas para un roadmap específico.
    
    Args:
        roadmap_id: ID del roadmap.
        
    Returns:
        Lista de IDs de temas en orden secuencial.
    """
    roadmap = get_roadmap(roadmap_id)
    if roadmap:
        return roadmap.get_topic_ids()
    return []

def get_next_topic_id(roadmap_id: str, current_topic_id: str) -> Optional[str]:
    """
    Obtiene el ID del siguiente tema en el roadmap.
    
    Args:
        roadmap_id: ID del roadmap.
        current_topic_id: ID del tema actual.
    
    Returns:
        ID del siguiente tema o None si es el último o no se encuentra.
    """
    roadmap = get_roadmap(roadmap_id)
    if roadmap:
        next_topic = roadmap.get_next_topic(current_topic_id)
        if next_topic:
            return next_topic.id
    return None

def get_all_roadmaps_info() -> List[Dict[str, Any]]:
    """
    Retorna información básica sobre todos los roadmaps disponibles.
    
    Returns:
        Lista de diccionarios con información sobre cada roadmap.
    """
    return [
        {
            "id": roadmap_id,
            "title": roadmap_data.title,
            "description": roadmap_data.description,
            "topic_count": len(roadmap_data.topics)
        }
        for roadmap_id, roadmap_data in AVAILABLE_ROADMAPS.items()
    ]
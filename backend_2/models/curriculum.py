from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from data.roadmaps import AVAILABLE_ROADMAPS

class RoadmapTopic(BaseModel):
    """
    Represents a topic within a learning roadmap.
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
    Defines a complete learning roadmap with a sequence of topics.
    """
    id: str
    title: str
    description: str
    topics: List[RoadmapTopic]

    def get_topic_ids(self) -> List[str]:
        """Returns the list of topic IDs in the roadmap."""
        return [topic.id for topic in self.topics]

    def get_topic_by_id(self, topic_id: str) -> Optional[RoadmapTopic]:
        """Finds a topic by its ID."""
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        return None

    def get_next_topic(self, current_topic_id: str) -> Optional[RoadmapTopic]:
        """Gets the next topic in the sequence."""
        topic_ids = self.get_topic_ids()
        try:
            current_index = topic_ids.index(current_topic_id)
            if current_index < len(topic_ids) - 1:
                next_id = topic_ids[current_index + 1]
                return self.get_topic_by_id(next_id)
        except ValueError:
            pass
        return None

def get_roadmap(roadmap_id: str) -> Optional[LearningRoadmap]:
    """
    Gets a roadmap by its ID.

    Args:
        roadmap_id: ID of the roadmap to retrieve.

    Returns:
        LearningRoadmap instance or None if it doesn't exist.
    """
    roadmap_data = AVAILABLE_ROADMAPS.get(roadmap_id)
    if roadmap_data:
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
    Gets the sequence of topic IDs for a specific roadmap.

    Args:
        roadmap_id: ID of the roadmap.

    Returns:
        List of topic IDs in sequential order.
    """
    roadmap = get_roadmap(roadmap_id)
    if roadmap:
        return roadmap.get_topic_ids()
    return []

def get_next_topic_id(roadmap_id: str, current_topic_id: str) -> Optional[str]:
    """
    Gets the ID of the next topic in the roadmap.

    Args:
        roadmap_id: ID of the roadmap.
        current_topic_id: ID of the current topic.

    Returns:
        ID of the next topic or None if it's the last or not found.
    """
    roadmap = get_roadmap(roadmap_id)
    if roadmap:
        next_topic = roadmap.get_next_topic(current_topic_id)
        if next_topic:
            return next_topic.id
    return None

def get_all_roadmaps_info() -> List[Dict[str, Any]]:
    """
    Returns basic information about all available roadmaps.

    Returns:
        List of dictionaries with information about each roadmap.
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
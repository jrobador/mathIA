# -*- coding: utf-8 -*-
"""
Defines learning paths (roadmaps) for different mathematical topics.
Each roadmap contains the sequence of topics and the requirements for progression.
"""

from typing import Dict, List, Any, Optional

class RoadmapTopic:
    """
    Represents a topic within a learning roadmap.
    """
    def __init__(
        self, 
        id: str, 
        title: str, 
        description: str,
        cpa_phases: List[str] = ["Concrete", "Pictorial", "Abstract"], # Concrete, Pictorial, Abstract phases (CPA approach)
        prerequisites: Optional[List[str]] = None, # List of topic IDs that must be mastered before this one
        required_mastery: float = 0.8, # Required score (e.g., 80%) to consider the topic mastered
        practice_problems_min: int = 3, # Minimum number of practice problems to attempt
        subtopics: Optional[List[str]] = None # Optional list of sub-concepts within this topic
    ):
        self.id = id
        self.title = title
        self.description = description
        self.cpa_phases = cpa_phases
        self.prerequisites = prerequisites or []
        self.required_mastery = required_mastery
        self.practice_problems_min = practice_problems_min
        self.subtopics = subtopics or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the topic to a dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "cpa_phases": self.cpa_phases,
            "prerequisites": self.prerequisites,
            "required_mastery": self.required_mastery,
            "practice_problems_min": self.practice_problems_min,
            "subtopics": self.subtopics
        }

class LearningRoadmap:
    """
    Defines a complete learning roadmap with a sequence of topics.
    """
    def __init__(self, id: str, title: str, description: str, topics: List[RoadmapTopic]):
        self.id = id
        self.title = title
        self.description = description
        self.topics = topics # The list of topics in the roadmap, ordered sequentially
    
    def get_topic_ids(self) -> List[str]:
        """Returns the list of topic IDs in the roadmap."""
        return [topic.id for topic in self.topics]
    
    def get_topic_by_id(self, topic_id: str) -> Optional[RoadmapTopic]:
        """Finds a topic by its ID."""
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        return None # Return None if topic ID is not found
    
    def get_next_topic(self, current_topic_id: str) -> Optional[RoadmapTopic]:
        """Gets the next topic in the sequence."""
        topic_ids = self.get_topic_ids()
        try:
            current_index = topic_ids.index(current_topic_id)
            if current_index < len(topic_ids) - 1: # Check if it's not the last topic
                next_id = topic_ids[current_index + 1]
                return self.get_topic_by_id(next_id)
        except ValueError: # Handle case where current_topic_id is not in the list
            pass
        return None # Return None if it's the last topic or ID not found
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the roadmap to a dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "topics": [topic.to_dict() for topic in self.topics] # Convert each topic to its dictionary representation
        }

# ----- Roadmap Definitions -----

# Fractions Roadmap
fractions_roadmap = LearningRoadmap(
    id="fractions",
    title="Fractions",
    description="Learn about fractions, from basic concepts to advanced operations.",
    topics=[
        RoadmapTopic(
            id="fractions_introduction",
            title="Introduction to Fractions",
            description="What fractions are and how they represent parts of a whole.",
            subtopics=["Concept of a fraction", "Numerator and denominator", "Visual representation"]
        ),
        RoadmapTopic(
            id="fractions_equivalent",
            title="Equivalent Fractions",
            description="How to identify and create equivalent fractions.",
            prerequisites=["fractions_introduction"],
            subtopics=["Simplification", "Expansion", "Comparing fractions"] # "Amplificación" translated as "Expansion"
        ),
        RoadmapTopic(
            id="fractions_comparison",
            title="Comparing Fractions",
            description="How to compare fractions and order them.",
            prerequisites=["fractions_equivalent"],
            subtopics=["Common denominator", "Cross-multiplication method", "Comparison using benchmarks"] # "Método de cruz" -> "Cross-multiplication method", "Comparación con referentes" -> "Comparison using benchmarks"
        ),
        RoadmapTopic(
            id="fractions_addition",
            title="Adding Fractions",
            description="How to add fractions with like and unlike denominators.",
            prerequisites=["fractions_equivalent", "fractions_comparison"],
            subtopics=["Like denominators", "Unlike denominators", "Mixed numbers"]
        ),
        RoadmapTopic(
            id="fractions_subtraction",
            title="Subtracting Fractions",
            description="How to subtract fractions with like and unlike denominators.",
            prerequisites=["fractions_addition"],
            subtopics=["Like denominators", "Unlike denominators", "Mixed numbers"]
        ),
        RoadmapTopic(
            id="fractions_multiplication",
            title="Multiplying Fractions",
            description="How to multiply fractions and mixed numbers.",
            prerequisites=["fractions_subtraction"],
            subtopics=["Direct multiplication", "With whole numbers", "With mixed numbers"]
        ),
        RoadmapTopic(
            id="fractions_division",
            title="Dividing Fractions",
            description="How to divide fractions and mixed numbers.",
            prerequisites=["fractions_multiplication"],
            subtopics=["Reciprocal or inverse", "Division by whole numbers", "Division of mixed numbers"]
        )
    ]
)

# Addition Roadmap
addition_roadmap = LearningRoadmap(
    id="addition",
    title="Addition",
    description="Learn to add, from basic concepts to addition with carrying and multiple digits.",
    topics=[
        RoadmapTopic(
            id="addition_introduction",
            title="Introduction to Addition",
            description="What addition means and how to combine quantities.",
            subtopics=["Concept of addition", "Signs and symbols", "Basic properties"]
        ),
        RoadmapTopic(
            id="addition_single_digit",
            title="Single-Digit Addition",
            description="How to fluently add single-digit numbers.",
            prerequisites=["addition_introduction"],
            subtopics=["Basic combinations", "Mental strategies", "Number facts"]
        ),
        RoadmapTopic(
            id="addition_double_digit",
            title="Double-Digit Addition",
            description="How to add two-digit numbers without carrying.",
            prerequisites=["addition_single_digit"],
            subtopics=["Place value", "Vertical method", "Estimation"]
        ),
        RoadmapTopic(
            id="addition_carrying",
            title="Addition with Carrying",
            description="How to add numbers when the sum of a column is greater than 9.",
            prerequisites=["addition_double_digit"],
            subtopics=["Concept of carrying", "Step-by-step method", "Practical applications"]
        ),
        RoadmapTopic(
            id="addition_multiple_digit",
            title="Multi-Digit Addition",
            description="How to efficiently add large numbers.",
            prerequisites=["addition_carrying"],
            subtopics=["Column alignment", "Multiple carries", "Result estimation"]
        ),
        RoadmapTopic(
            id="addition_mental",
            title="Mental Addition",
            description="Strategies for quick mental addition.",
            prerequisites=["addition_multiple_digit"],
            subtopics=["Decomposition", "Rounding", "Compensation"]
        ),
        RoadmapTopic(
            id="addition_word_problems",
            title="Addition Word Problems",
            description="How to apply addition to solve practical problems.",
            prerequisites=["addition_mental"],
            subtopics=["Identifying operations", "Solution strategies", "Checking results"]
        )
    ]
)

# Subtraction Roadmap
subtraction_roadmap = LearningRoadmap(
    id="subtraction",
    title="Subtraction",
    description="Learn to subtract, from basic concepts to subtraction with borrowing and multiple digits.",
    topics=[
        RoadmapTopic(
            id="subtraction_introduction",
            title="Introduction to Subtraction",
            description="What subtraction means and how to take away quantities.",
            subtopics=["Concept of subtraction", "Signs and symbols", "Relationship with addition"]
        ),
        RoadmapTopic(
            id="subtraction_single_digit",
            title="Single-Digit Subtraction",
            description="How to fluently subtract single-digit numbers.",
            prerequisites=["subtraction_introduction"],
            subtopics=["Basic combinations", "Mental strategies", "Number facts"]
        ),
        RoadmapTopic(
            id="subtraction_double_digit",
            title="Double-Digit Subtraction",
            description="How to subtract two-digit numbers without borrowing.",
            prerequisites=["subtraction_single_digit"],
            subtopics=["Place value", "Vertical method", "Estimation"]
        ),
        RoadmapTopic(
            id="subtraction_borrowing",
            title="Subtraction with Borrowing", # "Resta con Préstamo" is Subtraction with Borrowing/Regrouping
            description="How to subtract when the top digit is smaller than the bottom digit.",
            prerequisites=["subtraction_double_digit"],
            subtopics=["Concept of borrowing", "Step-by-step method", "Checking"] # "Verificación" -> "Checking"
        ),
        RoadmapTopic(
            id="subtraction_multiple_digit",
            title="Multi-Digit Subtraction",
            description="How to efficiently subtract large numbers.",
            prerequisites=["subtraction_borrowing"],
            subtopics=["Column alignment", "Multiple borrows", "Result estimation"]
        ),
        RoadmapTopic(
            id="subtraction_mental",
            title="Mental Subtraction",
            description="Strategies for quick mental subtraction.",
            prerequisites=["subtraction_multiple_digit"],
            subtopics=["Decomposition", "Rounding", "Complement method"] # "Método de complemento" -> "Complement method"
        ),
        RoadmapTopic(
            id="subtraction_word_problems",
            title="Subtraction Word Problems",
            description="How to apply subtraction to solve practical problems.",
            prerequisites=["subtraction_mental"],
            subtopics=["Identifying operations", "Solution strategies", "Checking results"]
        )
    ]
)

# Multiplication Roadmap
multiplication_roadmap = LearningRoadmap(
    id="multiplication",
    title="Multiplication",
    description="Learn to multiply, from basic concepts to multi-digit multiplication.",
    topics=[
        RoadmapTopic(
            id="multiplication_introduction",
            title="Introduction to Multiplication",
            description="What multiplication means and its relationship to repeated addition.",
            subtopics=["Concept of multiplication", "Signs and symbols", "Repeated addition"]
        ),
        RoadmapTopic(
            id="multiplication_tables",
            title="Multiplication Tables",
            description="How to learn and remember the multiplication tables.",
            prerequisites=["multiplication_introduction"],
            subtopics=["Tables 1-5", "Tables 6-10", "Patterns and tricks"]
        ),
        RoadmapTopic(
            id="multiplication_single_digit",
            title="Multiplication by a Single Digit",
            description="How to multiply a multi-digit number by a single-digit number.",
            prerequisites=["multiplication_tables"],
            subtopics=["Vertical method", "Carrying", "Estimation"]
        ),
        RoadmapTopic(
            id="multiplication_double_digit",
            title="Multiplication by Two Digits",
            description="How to multiply when both factors have two or more digits.",
            prerequisites=["multiplication_single_digit"],
            subtopics=["Extended vertical method", "Partial products", "Checking"]
        ),
        RoadmapTopic(
            id="multiplication_mental",
            title="Mental Multiplication",
            description="Strategies for quick mental multiplication.",
            prerequisites=["multiplication_double_digit"],
            subtopics=["Decomposition", "Using multiples of 10", "Properties"]
        ),
        RoadmapTopic(
            id="multiplication_word_problems",
            title="Multiplication Word Problems",
            description="How to apply multiplication to solve practical problems.",
            prerequisites=["multiplication_mental"],
            subtopics=["Identifying situations", "Solution strategies", "Checking results"]
        )
    ]
)

# Division Roadmap
division_roadmap = LearningRoadmap(
    id="division",
    title="Division",
    description="Learn to divide, from basic concepts to multi-digit division.",
    topics=[
        RoadmapTopic(
            id="division_introduction",
            title="Introduction to Division",
            description="What division means and its relationship to multiplication.",
            subtopics=["Concept of division", "Signs and symbols", "Parts of division (dividend, divisor, quotient, remainder)"] # Added standard terms
        ),
        RoadmapTopic(
            id="division_basic",
            title="Basic Division",
            description="How to divide using multiplication tables.",
            prerequisites=["division_introduction"],
            subtopics=["Exact divisions", "Relationship with multiplication", "Checking"]
        ),
        RoadmapTopic(
            id="division_single_digit",
            title="Division by a Single Digit",
            description="How to divide numbers by a single-digit divisor.",
            prerequisites=["division_basic"],
            subtopics=["Division algorithm (long division)", "Division with remainder", "Estimation"] # Clarified algorithm
        ),
        RoadmapTopic(
            id="division_double_digit",
            title="Division by Two Digits",
            description="How to divide numbers by two-digit (or more) divisors.",
            prerequisites=["division_single_digit"],
            subtopics=["Extended algorithm", "Estimating quotients", "Checking"]
        ),
        RoadmapTopic(
            id="division_decimal",
            title="Division with Decimals",
            description="How to divide when there are decimals in the dividend or divisor.",
            prerequisites=["division_double_digit"],
            subtopics=["Decimal placement", "Decimal division", "Approximation"] # "Desplazamiento decimal" -> "Decimal placement"
        ),
        RoadmapTopic(
            id="division_word_problems",
            title="Division Word Problems",
            description="How to apply division to solve practical problems.",
            prerequisites=["division_decimal"],
            subtopics=["Identifying situations", "Solution strategies", "Checking results"]
        )
    ]
)

# Dictionary of available roadmaps
AVAILABLE_ROADMAPS = {
    "fractions": fractions_roadmap,
    "addition": addition_roadmap,
    "subtraction": subtraction_roadmap,
    "multiplication": multiplication_roadmap,
    "division": division_roadmap
}

def get_roadmap(roadmap_id: str) -> Optional[LearningRoadmap]:
    """
    Gets a roadmap by its ID.
    
    Args:
        roadmap_id: ID of the roadmap to retrieve.
    
    Returns:
        LearningRoadmap or None if it doesn't exist.
    """
    return AVAILABLE_ROADMAPS.get(roadmap_id)

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
    return [] # Return empty list if roadmap not found

def get_next_topic_id(roadmap_id: str, current_topic_id: str) -> Optional[str]:
    """
    Gets the ID of the next topic in the roadmap.
    
    Args:
        roadmap_id: ID of the roadmap.
        current_topic_id: ID of the current topic.
    
    Returns:
        ID of the next topic or None if it's the last one or not found.
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
            "title": roadmap.title,
            "description": roadmap.description,
            "topic_count": len(roadmap.topics)
        }
        for roadmap_id, roadmap in AVAILABLE_ROADMAPS.items()
    ]

def get_roadmap_topic_info(roadmap_id: str, topic_id: str) -> Optional[Dict[str, Any]]:
    """
    Gets detailed information about a specific topic within a roadmap.
    
    Args:
        roadmap_id: ID of the roadmap.
        topic_id: ID of the topic.
    
    Returns:
        Dictionary with topic information or None if the roadmap or topic doesn't exist.
    """
    roadmap = get_roadmap(roadmap_id)
    if not roadmap:
        return None # Roadmap not found
    
    topic = roadmap.get_topic_by_id(topic_id)
    if not topic:
        return None # Topic not found in this roadmap
    
    # Convert the topic to a dictionary
    topic_info = topic.to_dict()
    
    # Add information about prerequisite topics (ID and Title)
    if topic.prerequisites:
        topic_info['prerequisite_topics'] = []
        for prereq_id in topic.prerequisites:
            prereq_topic = roadmap.get_topic_by_id(prereq_id)
            if prereq_topic: # Ensure the prerequisite topic exists in the roadmap
                topic_info['prerequisite_topics'].append({
                    'id': prereq_id,
                    'title': prereq_topic.title
                })
            else: # Handle cases where a prerequisite might be defined but not found (data integrity issue)
                 topic_info['prerequisite_topics'].append({
                    'id': prereq_id,
                    'title': f"Prerequisite topic '{prereq_id}' not found"
                 })

    # Add information about the next topic (ID and Title)
    next_topic = roadmap.get_next_topic(topic_id)
    if next_topic:
        topic_info['next_topic'] = {
            'id': next_topic.id,
            'title': next_topic.title
        }
    else:
        topic_info['next_topic'] = None # Explicitly state there's no next topic

    return topic_info
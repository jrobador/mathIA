# -*- coding: utf-8 -*-
from typing import Dict, List, Any, Optional, TypedDict, Union
from enum import Enum
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# ----- Enums for the model -----
class CPAPhase(str, Enum):
    """Enum representing the Concrete-Pictorial-Abstract teaching phases."""
    CONCRETE = "Concrete"
    PICTORIAL = "Pictorial"
    ABSTRACT = "Abstract"

class EvaluationOutcome(str, Enum):
    """Enum representing the possible outcomes of evaluating a student's answer."""
    CORRECT = "Correct"
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual" # Incorrect due to misunderstanding the concept
    INCORRECT_CALCULATION = "Incorrect_Calculation" # Incorrect due to a calculation mistake
    UNCLEAR = "Unclear" # The answer or reasoning is not clear enough to evaluate

# ----- Agent State -----
class StudentSessionState(TypedDict, total=False):
    """
    Represents the state of a student's learning session.
    `total=False` means keys are not required.
    """
    # Message history (Langchain format)
    messages: List[Union[HumanMessage, AIMessage, SystemMessage]]

    # Educational state
    current_topic: str # ID of the current topic being learned (e.g., "fractions_introduction")
    current_cpa_phase: str  # Using string instead of enum for JSON compatibility (e.g., "Concrete", "Pictorial")
    topic_mastery: Dict[str, float]  # Mastery level (0.0 to 1.0) per topic ID

    # Progress tracking
    consecutive_correct: int # Count of consecutive correct answers
    consecutive_incorrect: int # Count of consecutive incorrect answers
    error_feedback_given_count: int # How many times feedback for the current error type has been given

    # State of the last action/interaction
    last_action_type: Optional[str] # Type of the last action performed by the agent (e.g., "generate_problem", "evaluate_answer")
    last_evaluation: Optional[str]  # Outcome of the last evaluation (using string, e.g., "Correct", "Incorrect_Conceptual")
    last_problem_details: Optional[Dict[str, Any]] # Details of the last problem presented

    # Output of the current step (will be sent to the frontend via API response)
    current_step_output: Dict[str, Any] # Data to be sent to the UI for the current interaction

    # Student personalization
    personalized_theme: str # Theme for personalization (e.g., "space", "animals")
    
    # For the conditional graph flow (used by LangGraph)
    next: Optional[str] # Determines the next node to execute in the graph

# Helper functions for working with the state
def initialize_state(personalized_theme: str = "space") -> StudentSessionState:
    """Initializes a new session state with default values."""
    return {
        "messages": [],
        "current_topic": "fractions_introduction", # Default starting topic
        "current_cpa_phase": CPAPhase.CONCRETE.value, # Start with Concrete phase
        "topic_mastery": {"fractions_introduction": 0.1}, # Initial low mastery for the starting topic
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "error_feedback_given_count": 0,
        "last_action_type": None,
        "last_evaluation": None,
        "last_problem_details": None,
        "current_step_output": {},
        "personalized_theme": personalized_theme, # Set the theme
        "next": None # Initially no specific next step defined
    }

def get_current_mastery(state: StudentSessionState) -> float:
    """Gets the current mastery level for the topic."""
    # Get the current topic, defaulting if not present
    current_topic = state.get("current_topic", "fractions_introduction")
    # Get the mastery for that topic from the mastery dictionary, defaulting to 0.0
    return state.get("topic_mastery", {}).get(current_topic, 0.0)

def update_mastery(state: StudentSessionState, delta: float) -> None:
    """
    Updates the mastery level of the current topic by a given delta.
    Ensures mastery stays between 0.0 and 1.0.
    
    Args:
        state: The current session state.
        delta: The amount to change the mastery by (can be positive or negative).
    """
    current_topic = state.get("current_topic", "fractions_introduction")
    
    # Ensure the topic_mastery dictionary exists
    if "topic_mastery" not in state:
        state["topic_mastery"] = {}
    
    # Get current mastery, defaulting to 0.0 if topic not yet in dictionary
    current_mastery = state["topic_mastery"].get(current_topic, 0.0)
    
    # Calculate new mastery, clamping between 0.0 and 1.0
    new_mastery = max(0.0, min(1.0, current_mastery + delta))
    
    # Update the state
    state["topic_mastery"][current_topic] = new_mastery
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class CPAPhase(str, Enum):
    """Enum representing the Concrete-Pictorial-Abstract teaching phases."""
    CONCRETE = "Concrete"
    PICTORIAL = "Pictorial"
    ABSTRACT = "Abstract"

class EvaluationOutcome(str, Enum):
    """Enum representing the possible outcomes of evaluating a student's answer."""
    CORRECT = "Correct"
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual"
    INCORRECT_CALCULATION = "Incorrect_Calculation"
    UNCLEAR = "Unclear"

class Message(BaseModel):
    """Model to represent messages in the conversation."""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class StudentState(BaseModel):
    """
    Model for the state of a student's learning session.
    """
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    current_topic: str
    current_cpa_phase: CPAPhase = CPAPhase.CONCRETE
    topic_mastery: Dict[str, float] = {}

    messages: List[Message] = []

    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    error_feedback_given_count: int = 0

    last_action_type: Optional[str] = None
    last_evaluation: Optional[EvaluationOutcome] = None
    last_problem_details: Optional[Dict[str, Any]] = None

    waiting_for_input: bool = False
    theory_presented_for_topics: List[str] = []

    personalized_theme: str = "space"

    class Config:
        use_enum_values = True

class AgentOutput(BaseModel):
    """Structure for the agent's output towards the frontend."""
    text: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    prompt_for_answer: bool = False
    evaluation: Optional[EvaluationOutcome] = None
    is_final_step: bool = False

def initialize_state(session_id: str, topic_id: str = "fractions_introduction",
                    personalized_theme: str = "space", user_id: Optional[str] = None) -> StudentState:
    """Initializes a new session state with default values."""
    concrete_phase = CPAPhase.CONCRETE

    return StudentState(
        session_id=session_id,
        user_id=user_id,
        current_topic=topic_id,
        current_cpa_phase=concrete_phase,
        topic_mastery={topic_id: 0.1},
        personalized_theme=personalized_theme,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

def get_current_mastery(state: StudentState) -> float:
    """Gets the current mastery level for the topic."""
    return state.topic_mastery.get(state.current_topic, 0.0)

def update_mastery(state: StudentState, delta: float) -> None:
    """
    Updates the mastery level of the current topic by a given delta.
    Ensures mastery stays between 0.0 and 1.0.

    Args:
        state: The current session state.
        delta: The amount to change the mastery by (can be positive or negative).
    """
    current_mastery = state.topic_mastery.get(state.current_topic, 0.0)
    new_mastery = max(0.0, min(1.0, current_mastery + delta))
    state.topic_mastery[state.current_topic] = new_mastery
    state.updated_at = datetime.now()

def add_message(state: StudentState, role: str, content: str) -> None:
    """
    Adds a message to the conversation history.

    Args:
        state: The current session state.
        role: The role of the message ('human' or 'ai').
        content: The content of the message.
    """
    message = Message(role=role, content=content)
    state.messages.append(message)
    state.updated_at = datetime.now()

def get_last_user_message(state: StudentState) -> Optional[Message]:
    """
    Gets the last message from the user.

    Args:
        state: The current session state.

    Returns:
        The last user message or None if there isn't one.
    """
    for message in reversed(state.messages):
        if message.role == "human":
            return message
    return None
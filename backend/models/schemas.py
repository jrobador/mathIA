from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from enum import Enum

class SessionStartRequest(BaseModel):
    """Model for starting a new learning session."""
    topic_id: str = Field(..., description="ID of the topic to study")
    user_id: Optional[str] = Field(None, description="User ID (optional)")
    initial_mastery: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Initial mastery level")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SubmitAnswerRequest(BaseModel):
    """Model for submitting a user's answer."""
    answer: str = Field(..., description="User's answer")
    problem_id: Optional[str] = Field(None, description="Problem ID (if applicable)")
    time_taken: Optional[int] = Field(None, description="Time taken to answer in seconds")

class MessageType(str, Enum):
    """Enumeration for the type of message sent by the agent."""
    THEORY = "THEORY"
    GUIDED_PRACTICE = "GUIDED_PRACTICE"
    INDEPENDENT_PRACTICE = "INDEPENDENT_PRACTICE"
    FEEDBACK = "FEEDBACK"
    EVALUATION = "EVALUATION"
    SYSTEM = "SYSTEM"
    ERROR = "ERROR"

class AgentMessage(BaseModel):
    """Model representing a message sent from the learning agent to the client."""
    type: MessageType
    content: Dict[str, Any]
    requires_input: bool = Field(False, description="Indicates if user input is required")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Data for visualization")

class ClientMessage(BaseModel):
    """Model representing a message sent from the client to the learning agent."""
    action: str = Field(..., description="Requested action (submit_answer, request_hint, etc.)")
    data: Dict[str, Any] = Field(..., description="Data associated with the action")

class SessionState(BaseModel):
    """Model representing the basic state of a learning session."""
    session_id: str
    topic_id: str
    mastery: float
    waiting_for_input: bool
    current_phase: str
    timestamp: str
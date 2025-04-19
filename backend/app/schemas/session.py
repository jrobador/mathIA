from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# --- Request Schemas ---
class StartSessionRequest(BaseModel):
    personalized_theme: Optional[str] = "espacio" # Default theme

class ProcessInputRequest(BaseModel):
    message: str

# --- Response Schemas ---
class AgentOutput(BaseModel):
    """Structure expected by the frontend for each agent step output."""
    text: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    feedback: Optional[Dict[str, str]] = None # e.g., {"type": "correct", "message": "..."}
    prompt_for_answer: Optional[bool] = False
    evaluation: Optional[str] = None # e.g., "Correct", "Incorrect_Conceptual"

class StartSessionResponse(BaseModel):
    session_id: str
    initial_output: AgentOutput

class ProcessInputResponse(BaseModel):
    session_id: str
    agent_output: AgentOutput
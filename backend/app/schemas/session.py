# -*- coding: utf-8 -*-
"""
Pydantic schemas for the math tutor sessions.
Defines the data models used in the API.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum

# --- Enumerations ---

class CPAPhase(str, Enum):
    """Represents the Concrete-Pictorial-Abstract teaching phases."""
    CONCRETE = "Concrete"
    PICTORIAL = "Pictorial"
    ABSTRACT = "Abstract"

class EvaluationOutcome(str, Enum):
    """Represents the possible outcomes of evaluating a student's answer."""
    CORRECT = "Correct"
    INCORRECT_CONCEPTUAL = "Incorrect_Conceptual"
    INCORRECT_CALCULATION = "Incorrect_Calculation"
    UNCLEAR = "Unclear"

class DifficultySetting(str, Enum):
    """Represents possible difficulty levels."""
    INITIAL = "initial"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class LearningPath(str, Enum):
    """Represents the available learning paths or subjects."""
    FRACTIONS = "fractions"
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"

# --- Diagnostic Schemas ---

class DiagnosticQuestionResult(BaseModel):
    """Represents the result for a single question in the diagnostic test."""
    question_id: str = Field(..., description="Identifier for the question.")
    correct: bool = Field(..., description="Whether the student answered correctly.")
    concept_tested: Optional[str] = Field(None, description="The primary math concept tested by this question.")
    # Add other relevant fields like 'student_answer', 'correct_answer', 'time_taken', etc. if needed

class DiagnosticData(BaseModel):
    """Represents the overall results of a diagnostic test."""
    score: float = Field(..., description="Overall score, potentially normalized or weighted.")
    correct_answers: int = Field(..., description="Number of questions answered correctly.")
    total_questions: int = Field(..., description="Total number of questions in the diagnostic.")
    recommended_level: DifficultySetting = Field(..., description="Suggested starting difficulty based on performance.")
    question_results: Optional[List[DiagnosticQuestionResult]] = Field(None, description="Detailed results for each question.")

    class Config:
        use_enum_values = True # Serialize enums to their string values

# --- Tutor Configuration ---

class TutorConfig(BaseModel):
    """Configuration settings to customize the tutor's behavior."""
    initial_topic: Optional[str] = Field(None, description="Optional starting topic ID.")
    initial_cpa_phase: Optional[CPAPhase] = Field(None, description="Optional starting CPA phase.")
    initial_difficulty: Optional[DifficultySetting] = Field(None, description="Optional starting difficulty level.")
    difficulty_adjustment_rate: Optional[float] = Field(0.1, description="Optional rate influencing mastery changes.")
    enable_audio: Optional[bool] = Field(True, description="Flag to enable/disable audio generation.")
    enable_images: Optional[bool] = Field(True, description="Flag to enable/disable image generation.")
    language: Optional[str] = Field("en", description="Preferred language (e.g., 'en', 'es').") # Default to English
    
    class Config:
        use_enum_values = True # Serialize enums to their string values

# --- Request Schemas ---

class StartSessionRequest(BaseModel):
    """Request model to start a new tutoring session."""
    personalized_theme: Optional[str] = Field("space", description="Optional theme for personalization (e.g., 'space', 'animals').")
    initial_message: Optional[str] = Field(None, description="Optional initial message from the user.")
    config: Optional[TutorConfig] = Field(None, description="Optional tutor configuration settings.")
    diagnostic_results: Optional[DiagnosticData] = Field(None, description="Optional results from a diagnostic test to initialize state.")
    learning_path: Optional[LearningPath] = Field(None, description="Optional learning path to follow (e.g., 'fractions', 'addition').")
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "personalized_theme": "ocean",
                "initial_message": "Hi, I want to learn about fractions.",
                "config": {
                    "initial_topic": "fractions_introduction",
                    "initial_cpa_phase": "Concrete",
                    "enable_audio": True,
                    "language": "en"
                },
                "learning_path": "fractions",
                 "diagnostic_results": {
                    "score": 75.0,
                    "correct_answers": 3,
                    "total_questions": 4,
                    "recommended_level": "intermediate",
                    "question_results": [
                        {"question_id": "q1", "correct": True, "concept_tested": "fractions_introduction"},
                        {"question_id": "q2", "correct": True, "concept_tested": "fractions_equivalent"},
                        {"question_id": "q3", "correct": False, "concept_tested": "fractions_comparison"},
                        {"question_id": "q4", "correct": True, "concept_tested": "fractions_addition"}
                    ]
                }
            }
        }

class ProcessInputRequest(BaseModel):
    """Request model for processing user input within an active session."""
    message: str = Field(..., description="The user's input message.")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "I think the answer is 3/4"
            }
        }

# --- Response Schemas ---

class FeedbackDetails(BaseModel):
    """Detailed information about specific feedback provided."""
    # This might be redundant if feedback is embedded in AgentOutput text, 
    # but could be used for structured feedback types.
    type: Optional[str] = Field(None, description="Type of feedback (e.g., hint, clarification).")
    message: Optional[str] = Field(None, description="The detailed feedback message.")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "hint",
                "message": "Remember to find a common denominator first."
            }
        }

class AgentOutput(BaseModel):
    """Structure representing the output from the agent to the frontend."""
    text: Optional[str] = Field(None, description="Main text content of the agent's response.")
    image_url: Optional[str] = Field(None, description="URL of a generated image, if any.")
    audio_url: Optional[str] = Field(None, description="URL of generated audio, if any.")
    # feedback: Optional[FeedbackDetails] = Field(None, description="Specific feedback details (if structured feedback is used).")
    prompt_for_answer: Optional[bool] = Field(False, description="Indicates if the agent is expecting a response from the user.")
    evaluation: Optional[EvaluationOutcome] = Field(None, description="Result of the evaluation, if the previous step was an evaluation.")
    is_final_step: Optional[bool] = Field(False, description="Indicates if this is the final step of the session/roadmap.")

    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "text": "Let's learn about fractions. A fraction represents a part of a whole...",
                "image_url": "https://example.com/images/fractions.png",
                "audio_url": "https://example.com/audio/explanation.mp3",
                "prompt_for_answer": True,
                "evaluation": None,
                 "is_final_step": False
            }
        }

class StartSessionResponse(BaseModel):
    """Response returned when a new session is successfully started."""
    session_id: str = Field(..., description="Unique identifier for the session.")
    initial_output: AgentOutput = Field(..., description="The agent's first output to the user.")
    status: str = Field("active", description="Initial status of the session.")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "initial_output": {
                    "text": "Hi! Let's start learning about Fractions. What do you know about them?",
                    "image_url": "https://example.com/images/welcome_fractions.png",
                    "audio_url": "https://example.com/audio/welcome.mp3",
                    "prompt_for_answer": True
                },
                "status": "active"
            }
        }

class ProcessInputResponse(BaseModel):
    """Response returned after processing user input."""
    session_id: str = Field(..., description="Identifier for the session.")
    agent_output: AgentOutput = Field(..., description="The agent's output generated in response to the user input.")
    mastery_level: Optional[float] = Field(None, description="Current estimated mastery level for the active topic (0.0-1.0).")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "agent_output": {
                    "text": "That's correct! 1/2 is indeed equivalent to 2/4. Let's try another one.",
                    "evaluation": "Correct",
                    "prompt_for_answer": True
                },
                "mastery_level": 0.65
            }
        }

class SessionStatusResponse(BaseModel):
    """Response containing the current status and progress of a session."""
    session_id: str = Field(..., description="Identifier for the session.")
    current_topic: str = Field(..., description="ID of the topic currently being covered.")
    mastery_levels: Dict[str, float] = Field(..., description="Dictionary mapping topic IDs to estimated mastery levels (0.0-1.0).")
    current_cpa_phase: CPAPhase = Field(..., description="Current CPA phase (Concrete, Pictorial, Abstract).")
    is_active: bool = Field(..., description="Indicates if the session is considered active.")
    created_at: Optional[float] = Field(None, description="Timestamp when the session was created (Unix epoch).")
    last_updated: Optional[float] = Field(None, description="Timestamp when the session was last updated (Unix epoch).")
    
    class Config:
        use_enum_values = True
        schema_extra = {
             "example": {
                "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "current_topic": "fractions_comparison",
                "mastery_levels": {
                    "fractions_introduction": 1.0,
                    "fractions_equivalent": 0.8,
                    "fractions_comparison": 0.4
                 },
                 "current_cpa_phase": "Pictorial",
                 "is_active": True,
                 "created_at": 1678886400.0,
                 "last_updated": 1678887000.0
            }
        }
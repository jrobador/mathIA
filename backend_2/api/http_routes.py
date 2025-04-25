"""
http routes for handling real-time communication with clients.
"""

from fastapi import APIRouter, HTTPException, Body, Request, Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

router = APIRouter()

class DiagnosticQuestionResult(BaseModel):
    """Model for a single diagnostic question result."""
    question_id: str
    correct: bool
    concept_tested: Optional[str] = None

class StartSessionRequest(BaseModel):
    """Model for session start request with diagnostic results support."""
    topic_id: str = Field("fractions_introduction", description="ID of the topic to study")
    user_id: Optional[str] = Field(None, description="User ID (optional)")
    initial_mastery: float = Field(0.0, ge=0.0, le=1.0, description="Initial mastery level")
    personalized_theme: str = Field("space", description="Personalization theme (space, ocean, etc.)")
    diagnostic_results: Optional[List[DiagnosticQuestionResult]] = Field(None, description="Results of the diagnostic test")

class SessionResponse(BaseModel):
    """Response model with session information and the first step's result."""
    session_id: str
    topic_id: str
    result: Dict[str, Any] 
    requires_input: bool 

class SubmitAnswerRequest(BaseModel):
    """Model for submitting a user answer."""
    answer: str = Field(..., description="User's answer")

class SubmitAnswerResponse(BaseModel):
    """Response model for submitting an answer, potentially containing multiple steps."""
    results: List[Dict[str, Any]]

@router.post("/api/sessions", response_model=SessionResponse)
async def create_session(request: Request, body: StartSessionRequest = Body(...)):
    """
    Creates a new learning session, optionally using diagnostic results.
    """
    learning_agent = request.app.state.learning_agent

    try:
        initial_mastery = body.initial_mastery

        if body.diagnostic_results:
            total_questions = len(body.diagnostic_results)
            correct_answers = sum(1 for result in body.diagnostic_results if result.correct)

            if total_questions > 0:
                calculated_mastery = 0.1 + (0.7 * (correct_answers / total_questions))
                initial_mastery = calculated_mastery
                print(f"Calculated initial mastery from diagnostics: {initial_mastery:.2f} ({correct_answers}/{total_questions} correct)")

        session_result = await learning_agent.create_session(
            topic_id=body.topic_id,
            personalized_theme=body.personalized_theme,
            initial_mastery=initial_mastery,
            user_id=body.user_id
        )

        session_id = session_result.get("session_id")
        first_action_result = session_result.get("initial_result", {})
        requires_input = first_action_result.get("waiting_for_input", False)

        if not session_id:
             raise HTTPException(status_code=500, detail="Failed to create session ID")

        return SessionResponse(
            session_id=session_id,
            topic_id=body.topic_id,
            result=first_action_result,
            requires_input=requires_input
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@router.post("/api/sessions/{session_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    request: Request,
    session_id: str = Path(..., description="ID of the session"),
    body: SubmitAnswerRequest = Body(...)
):
    """
    Submits the user's answer for evaluation and gets the next step(s).
    """
    learning_agent = request.app.state.learning_agent

    if not learning_agent.get_session_state(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        results_list = await learning_agent.handle_user_input(
            session_id=session_id,
            user_input=body.answer
        )

        if isinstance(results_list, list) and results_list and results_list[0].get("action") == "error":
             error_detail = results_list[0].get("error", "Unknown error processing answer")
             status_code = 400
             if "not found" in str(error_detail).lower(): status_code = 404
             raise HTTPException(status_code=status_code, detail=error_detail)

        if not isinstance(results_list, list):
            print(f"Warning: handle_user_input returned unexpected type: {type(results_list)}. Wrapping in list.")
            results_list = [results_list] if isinstance(results_list, dict) else []
            if not results_list:
                 raise HTTPException(status_code=500, detail="Invalid response structure from agent")


        return SubmitAnswerResponse(results=results_list)

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")

@router.get("/api/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session_state(
    request: Request,
    session_id: str = Path(..., description="ID of the session")
):
    """
    Gets the current state of a session.
    """
    learning_agent = request.app.state.learning_agent
    state = learning_agent.get_session_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return state

@router.get("/api/sessions/{session_id}/continue", response_model=Dict[str, Any])
async def continue_session(
    request: Request,
    session_id: str = Path(..., description="ID of the session")
):
    """
    Continues the execution of a session by processing the next step.
    """
    learning_agent = request.app.state.learning_agent

    if not learning_agent.get_session_state(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await learning_agent.process_step(session_id)

        if result.get("action") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Error continuing session"))

        return result

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error continuing session: {str(e)}")

@router.get("/api/roadmaps", response_model=List[Dict[str, Any]])
async def get_roadmaps(request: Request):
    """
    Gets the list of available learning roadmaps.
    """
    learning_agent = request.app.state.learning_agent
    roadmaps = learning_agent.get_available_roadmaps()
    return roadmaps

@router.get("/api/sessions", response_model=List[Dict[str, Any]])
async def get_active_sessions(request: Request):
    """
    Gets the list of active sessions.
    """
    learning_agent = request.app.state.learning_agent
    sessions = learning_agent.get_active_sessions()
    return sessions

@router.get("/api/health")
async def health_check():
    """
    Service health check endpoint.
    """
    return {"status": "ok", "service": "adaptive-learning-agent"}
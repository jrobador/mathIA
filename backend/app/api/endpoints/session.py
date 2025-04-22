# -*- coding: utf-8 -*-
"""
API endpoints for managing math tutor sessions.
Defines routes and handlers for interacting with the agent.
"""
from fastapi import APIRouter, HTTPException, Body, Query, Response, status
# Assuming schemas are defined with English names or are standard Pydantic models
from app.schemas.session import (
    StartSessionRequest, StartSessionResponse, 
    ProcessInputRequest, ProcessInputResponse, 
    AgentOutput, DifficultySetting, 
    LearningPath, SessionStatusResponse
)
# Assuming these modules/functions are correctly named in English
from app.agent.state import initialize_state 
from app.agent.graph import get_compiled_app
from app.agent.diagnostic import create_diagnostic_result_from_json, apply_diagnostic_to_state
from langchain_core.messages import HumanMessage # For representing user input
import time
import uuid # For generating unique session IDs
import asyncio # For creating locks and asynchronous operations
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks

# Create API router instance
router = APIRouter()

# In production, we would use a database or distributed cache (like Redis).
# For this example/hackathon, we use an in-memory dictionary.
active_sessions: Dict[str, Dict[str, Any]] = {} 

# For performance, compile the graph once on startup
compiled_app = get_compiled_app() 

async def generate_session_content_background(session_id: str, state: Dict[str, Any], diagnostic_results: Optional[Dict[str, Any]] = None):
    """
    Background task to generate initial content for a session.
    This runs asynchronously after the session creation response is returned.
    
    Args:
        session_id: The ID of the session to generate content for
        state: The initial state to use
        diagnostic_results: Optional diagnostic results to apply
    """
    try:
        print(f"Starting background content generation for session {session_id}")
        
        # Check if session still exists
        if session_id not in active_sessions:
            print(f"Session {session_id} no longer exists, aborting content generation")
            return
            
        # Apply diagnostic results if provided
        if diagnostic_results:
            diagnostic_obj = create_diagnostic_result_from_json(diagnostic_results)
            if diagnostic_obj:
                apply_diagnostic_to_state(state, diagnostic_obj)
                
        # Run the graph to generate content
        print(f"Running graph for session {session_id} with topic: {state.get('current_topic')}")
        result_state = await compiled_app.ainvoke(state)
        
        # After getting the initial output, clear the next state to prevent automatic execution
        if "next" in result_state:
            del result_state["next"]
            
        # Store the updated state in the active sessions dictionary
        active_sessions[session_id]["state"] = result_state
        active_sessions[session_id]["last_updated"] = time.time()
        
        # BUGFIX: Debug the current_step_output to see if it exists
        if "current_step_output" in result_state:
            print(f"DEBUG: current_step_output exists in result_state: {result_state['current_step_output']}")
        else:
            print(f"ERROR: current_step_output not found in result_state!")
            print(f"Result state keys: {result_state.keys()}")
            # Try to examine any potential output data that might be stored elsewhere
            print(f"Checking for last_problem_details: {result_state.get('last_problem_details')}")
            
            # BUGFIX: Create a default current_step_output if missing
            if "last_problem_details" in result_state:
                problem_details = result_state.get("last_problem_details", {})
                # Create a basic current_step_output from the problem details
                result_state["current_step_output"] = {
                    "text": problem_details.get("problem", "Practice problem is ready."),
                    "prompt_for_answer": True
                }
                print(f"Created default current_step_output from problem details")
            else:
                # Last resort fallback
                result_state["current_step_output"] = {
                    "text": "Your math practice is ready.",
                    "prompt_for_answer": True
                }
                print(f"Created basic fallback current_step_output")
                
        # Update the state again after potential fixes
        active_sessions[session_id]["state"] = result_state        
        
        # CRITICAL FIX: Make sure to set content_ready flag to True
        active_sessions[session_id]["content_ready"] = True
        
        print(f"Background content generation completed for session {session_id}")
        print(f"Content ready flag set to: {active_sessions[session_id].get('content_ready', False)}")
        
    except Exception as e:
        print(f"Error in background content generation for session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update session with error state if it still exists
        if session_id in active_sessions:
            active_sessions[session_id]["error"] = str(e)
            active_sessions[session_id]["last_updated"] = time.time()
            # Still mark as ready so the frontend can detect the error
            active_sessions[session_id]["content_ready"] = True
            print(f"Error occurred, content_ready set to True to indicate completion with error")

def map_learning_path_to_topic(learning_path: Optional[LearningPath]) -> str:
    """Maps the selected learning path enum to an initial topic ID string."""
    if not learning_path:
        return "fractions_introduction" # Default topic if no path is specified
        
    # Mapping from LearningPath enum members to starting topic IDs
    path_to_topic = {
        LearningPath.FRACTIONS: "fractions_introduction",
        LearningPath.ADDITION: "addition_introduction",
        LearningPath.SUBTRACTION: "subtraction_introduction",
        LearningPath.MULTIPLICATION: "multiplication_introduction",
        LearningPath.DIVISION: "division_introduction"
    }
    
    # Return the mapped topic, or default if the path is unknown
    return path_to_topic.get(learning_path, "fractions_introduction")

def map_difficulty_to_mastery(difficulty: Optional[DifficultySetting]) -> float:
    """Maps the selected difficulty setting enum to an initial mastery level (0.0-1.0)."""
    if not difficulty:
        return 0.1 # Default mastery if no difficulty is specified
        
    # Mapping from DifficultySetting enum members to initial mastery values
    difficulty_to_mastery = {
        DifficultySetting.INITIAL: 0.1,
        DifficultySetting.BEGINNER: 0.3,
        DifficultySetting.INTERMEDIATE: 0.5,
        DifficultySetting.ADVANCED: 0.7
    }
    
    # Return the mapped mastery, or default if the difficulty is unknown
    return difficulty_to_mastery.get(difficulty, 0.1)

@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest = Body(...), background_tasks: BackgroundTasks = None):
    """
    Starts a new learning session with the tutor agent.
    Returns quickly with a session ID, then processes content in the background.
    
    - Generates a unique session ID.
    - Initializes basic state.
    - Queues the heavy content generation for background processing.
    
    Returns:
        StartSessionResponse: Contains the session ID and minimal initial output.
    """
    try:
        # BUGFIX: Tracking for this specific request
        request_id = str(uuid.uuid4())
        print(f"Processing start session request {request_id}")
        
        # Generate a unique ID for the session
        session_id = str(uuid.uuid4())
        print(f"Creating new session {session_id}")
        
        # Create basic initial state with minimal processing
        initial_state = initialize_state(personalized_theme=request.personalized_theme)
        
        # Set initial topic if specified
        if request.learning_path:
            initial_topic = map_learning_path_to_topic(request.learning_path)
            initial_state["current_topic"] = initial_topic
        
        # Get initial mastery level from diagnostic results or defaults
        initial_difficulty = None
        if request.diagnostic_results:
            initial_difficulty = request.diagnostic_results.recommended_level
        elif request.config and request.config.initial_difficulty:
            initial_difficulty = request.config.initial_difficulty
        
        initial_mastery = map_difficulty_to_mastery(initial_difficulty or "beginner")
        
        # Set mastery for the current topic
        current_topic = initial_state["current_topic"]
        initial_state["topic_mastery"] = {current_topic: initial_mastery}
        
        # Add initial message if provided
        if request.initial_message:
            initial_state["messages"] = [HumanMessage(content=request.initial_message)]
        
        # Apply additional configurations if provided
        if request.config:
            if request.config.initial_cpa_phase:
                initial_state["current_cpa_phase"] = request.config.initial_cpa_phase.value
        
        # Initialize tracking fields
        initial_state["theory_presented_for_topics"] = []
        initial_state["next"] = "determine_next_step"
        
        # Create session with minimal initial data
        active_sessions[session_id] = {
            "state": initial_state,
            "created_at": time.time(),
            "last_updated": time.time(),
            "content_ready": False  # Flag to indicate content is still being generated
        }
        
        # Prepare a simple initial output
        initial_output = {
            "text": f"Welcome! Setting up your personalized {request.personalized_theme} math experience...",
            "prompt_for_answer": False,
            "is_loading": True
        }
        
        # IMPORTANT: Start content generation in the background
        if background_tasks:
            background_tasks.add_task(
                generate_session_content_background,
                session_id=session_id,
                state=initial_state,
                diagnostic_results=request.diagnostic_results.dict() if request.diagnostic_results else None
            )
        else:
            # Fallback if background_tasks is not available (should not happen)
            asyncio.create_task(
                generate_session_content_background(
                    session_id=session_id,
                    state=initial_state,
                    diagnostic_results=request.diagnostic_results.dict() if request.diagnostic_results else None
                )
            )
        
        print(f"Completed initial session creation {session_id} for request {request_id}")
        print(f"Content generation is now happening in the background")
        
        # Return quickly with just the session ID and minimal output
        return StartSessionResponse(
            session_id=session_id,
            initial_output=AgentOutput(**initial_output),
            status="initializing"  # Signal that content is still being generated
        )
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error starting session: {str(e)}")
        import traceback
        traceback.print_exc()
        # Raise an HTTP exception to inform the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )
            
@router.post("/{session_id}/process", response_model=ProcessInputResponse)
async def process_input(session_id: str, request: ProcessInputRequest = Body(...)):
    try:
        # Retrieve the session data
        session_data = active_sessions[session_id]
        current_state = session_data["state"]
        
        # Add the user's new message to the message history
        if "messages" not in current_state:
            current_state["messages"] = []
        
        current_state["messages"].append(HumanMessage(content=request.message))
        
        # CRITICAL FIX: Set appropriate next node based on current state
        last_action = current_state.get("last_action_type", "")
        if last_action in ["present_independent_practice", "present_guided_practice"]:
            # If we're answering any practice problem (guided or independent), route to evaluation
            current_state["next"] = "evaluate_answer"
            print(f"User provided answer for session {session_id}. Routing to evaluation...")
        else:
            # For other types of input, just determine the next step
            current_state["next"] = "determine_next_step"
        
        try:
            # Use wait_for instead of timeout for Python compatibility
            result_state = await compiled_app.ainvoke(current_state)
            
            # After processing, clear the next state marker
            if "next" in result_state:
                del result_state["next"]
            
            # Update the session state
            session_data["state"] = result_state
            session_data["last_updated"] = time.time()
            
            # Prepare the response
            agent_output_data = result_state.get("current_step_output", {})
            agent_output = AgentOutput(**agent_output_data)
            
            # Get the current mastery level
            current_topic = result_state.get("current_topic", "")
            mastery_level = result_state.get("topic_mastery", {}).get(current_topic, 0.0)
            
            # CRITICAL BUGFIX: Add debug output to help with troubleshooting
            print(f"Processed input successfully for session {session_id}")
            
            return ProcessInputResponse(
                session_id=session_id, 
                agent_output=agent_output,
                mastery_level=mastery_level
            )
            
        except asyncio.TimeoutError:
            print(f"WARNING: Processing timed out for session {session_id}")
            # Return an error response but keep the session
            error_output = {
                "text": "I'm having trouble processing your answer. Please try again.",
                "prompt_for_answer": True
            }
            return ProcessInputResponse(
                session_id=session_id,
                agent_output=AgentOutput(**error_output),
                mastery_level=current_state.get("topic_mastery", {}).get(current_state.get("current_topic", ""), 0.0)
            )
    
    except Exception as e:
        print(f"Error processing input for session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Important: Don't end the session here! Just return an error
        # DO NOT call endSession or terminate the session
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to process input: {str(e)}"
        )
        
@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Retrieves the current status of an active session, including content generation progress.
    """
    # Check if the session exists
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    
    # Get session data and current state
    session_data = active_sessions[session_id]
    current_state = session_data["state"]
    
    # Extract relevant information from the state
    current_topic = current_state.get("current_topic", "")
    topic_mastery = current_state.get("topic_mastery", {})
    current_cpa_phase = current_state.get("current_cpa_phase", "Concrete")
    
    # Check if content is ready (default to False if not set)
    content_ready = session_data.get("content_ready", False)
    
    # Debug log the content ready flag
    print(f"Status check for session {session_id}: content_ready={content_ready}")
    
    # Debug log the state structure
    print(f"DEBUG: State keys: {list(current_state.keys())}")
    print(f"DEBUG: current_step_output in state: {current_state.get('current_step_output')}")
    
    # Get any error message
    error = session_data.get("error")
    
    # Get the current output - IMPROVED LOGIC
    agent_output = None
    
    # Approach 1: First check if current_step_output exists in the state returned by the graph
    if "current_step_output" in current_state and current_state["current_step_output"]:
        print(f"DEBUG: Found current_step_output in state: {current_state['current_step_output']}")
        try:
            agent_output = AgentOutput(**current_state["current_step_output"])
        except Exception as e:
            print(f"ERROR: Failed to create AgentOutput from current_step_output: {str(e)}")
    
    # Approach 2: If content is ready but agent_output is missing, try to build from last_problem_details
    if content_ready and not agent_output:
        last_problem_details = current_state.get("last_problem_details", {})
        if last_problem_details:
            print(f"DEBUG: Building agent_output from last_problem_details: {last_problem_details}")
            try:
                # Build output from problem details
                agent_output_dict = {
                    "text": last_problem_details.get("problem", "Your math practice is ready."),
                    "prompt_for_answer": True
                }
                
                # Add image and audio URLs from last_problem_details
                if "image_url" in last_problem_details:
                    agent_output_dict["image_url"] = last_problem_details["image_url"]
                
                if "audio_url" in last_problem_details:
                    agent_output_dict["audio_url"] = last_problem_details["audio_url"]
                
                agent_output = AgentOutput(**agent_output_dict)
                
                # Fix the state by updating current_step_output
                current_state["current_step_output"] = agent_output_dict
                active_sessions[session_id]["state"] = current_state
                
                print(f"DEBUG: Created agent_output from last_problem_details")
            except Exception as e:
                print(f"ERROR: Failed to create AgentOutput from last_problem_details: {str(e)}")
    
    # If still no output but content is ready, create a minimal fallback
    if content_ready and not agent_output:
        print(f"DEBUG: Creating minimal fallback agent_output")
        agent_output = AgentOutput(
            text="Your math practice is ready.", 
            prompt_for_answer=True
        )
    
    # Construct and return the status response
    response = SessionStatusResponse(
        session_id=session_id,
        current_topic=current_topic,
        mastery_levels=topic_mastery,
        current_cpa_phase=current_cpa_phase,
        is_active=True,
        content_ready=content_ready,
        agent_output=agent_output,
        error=error,
        created_at=session_data.get("created_at"),
        last_updated=session_data.get("last_updated")
    )
    
    # Final debug output 
    print(f"DEBUG: Returning response with content_ready={response.content_ready}, agent_output={'present' if response.agent_output else 'missing'}")
    
    return response

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: str):
    """
    Ends an active session and removes it from memory.
    
    Args:
        session_id: The ID of the session to end.
    """
    # BUGFIX: Add debug log to trace session deletions
    print(f"Session deletion requested for {session_id}. Stack trace:")
    import traceback
    traceback.print_stack()
    
    # Check if the session exists
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    
    print(f"Ending session {session_id}")
    
    # BUGFIX: This is the only place sessions should be removed
    try:
        del active_sessions[session_id]
    except KeyError:
        # Should not happen due to the check above, but handle defensively
        pass 
        
    # Return No Content response on successful deletion
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{session_id}/feedback", status_code=status.HTTP_202_ACCEPTED)
async def submit_session_feedback(
    session_id: str,
    rating: int = Query(..., description="User rating for the session (1-5)", ge=1, le=5),
    comments: Optional[str] = Query(None, description="Optional user comments about the session")
):
    """
    Allows the user to submit feedback (rating and comments) about a learning session.
    
    Args:
        session_id: The ID of the session.
        rating: Numerical rating (1-5).
        comments: Optional textual feedback.
    """
    # Check if the session exists (or existed recently, might need different logic)
    if session_id not in active_sessions:
         # Consider allowing feedback even if session just ended? 
         # For now, require session to be active.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found. Feedback can only be submitted for active sessions."
        )
    
    # In a real system, this feedback would be stored persistently (e.g., database)
    print(f"Received feedback for session {session_id}: Rating={rating}, Comments='{comments}'")
    
    # Optionally, store the feedback within the session data itself (if needed later)
    session_data = active_sessions[session_id]
    if "feedback" not in session_data:
        session_data["feedback"] = [] # Initialize feedback list if needed
    
    session_data["feedback"].append({
        "rating": rating,
        "comments": comments,
        "timestamp": time.time()
    })
    
    # Return a simple confirmation message
    return {"message": "Feedback received successfully. Thank you!"}

# --- Maintenance Endpoint ---
@router.post("/maintenance/cleanup", status_code=status.HTTP_200_OK, include_in_schema=False) # Hide from public docs
async def cleanup_inactive_sessions(
    max_age_hours: float = Query(24.0, description="Maximum age of inactive sessions in hours before cleanup")
):
    """
    Administrative endpoint to clean up inactive sessions from memory.
    Should be protected in a real application (e.g., require admin auth).
    
    Args:
        max_age_hours: The maximum duration (in hours) a session can be inactive 
                       (based on last_updated time) before being removed.
    
    Returns:
        dict: A summary of the cleanup operation.
    """
    # This endpoint should ideally be protected by authentication/authorization
    now = time.time()
    max_age_seconds = max_age_hours * 3600 # Convert hours to seconds
    
    inactive_session_ids = []
    # Iterate over a copy of the keys to allow deletion during iteration
    for session_id, data in list(active_sessions.items()):
        # Use last_updated time, fallback to created_at if last_updated is missing
        last_activity = data.get("last_updated", data.get("created_at", 0))
        if (now - last_activity) > max_age_seconds:
            inactive_session_ids.append(session_id)
            # Remove the inactive session
            try:
                del active_sessions[session_id]
            except KeyError:
                pass # Already removed, ignore

    print(f"Cleanup performed: Removed {len(inactive_session_ids)} inactive sessions older than {max_age_hours} hours.")
    
    return {
        "message": f"Cleanup complete. Removed sessions inactive for more than {max_age_hours} hours.",
        "cleaned_sessions_count": len(inactive_session_ids),
        "remaining_sessions_count": len(active_sessions),
        "cleaned_session_ids": inactive_session_ids # Optionally return IDs for logging
    }
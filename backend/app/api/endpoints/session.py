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
from typing import Dict, Any, Optional

# Create API router instance
router = APIRouter()

# In production, we would use a database or distributed cache (like Redis).
# For this example/hackathon, we use an in-memory dictionary.
active_sessions: Dict[str, Dict[str, Any]] = {} 

# For performance, compile the graph once on startup
compiled_app = get_compiled_app() 

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
async def start_session(request: StartSessionRequest = Body(...)):
    """
    Starts a new learning session with the tutor agent.
    
    - Generates a unique session ID.
    - Initializes the state with the provided configuration (theme, path, diagnostic).
    - Runs the graph to get the first agent message.
    
    Returns:
        StartSessionResponse: Contains the session ID and the initial agent output.
    """
    try:
        # Generate a unique ID for the session
        session_id = str(uuid.uuid4())
        
        # Determine the initial topic based on learning path or config
        initial_topic = None
        if request.learning_path:
            initial_topic = map_learning_path_to_topic(request.learning_path)
        elif request.config and request.config.initial_topic:
            initial_topic = request.config.initial_topic
        # Default topic is set within initialize_state if none is provided here
        
        # Determine initial difficulty from diagnostic or config
        initial_difficulty = None
        if request.diagnostic_results:
            initial_difficulty = request.diagnostic_results.recommended_level
        elif request.config and request.config.initial_difficulty:
            initial_difficulty = request.config.initial_difficulty
            
        # Map difficulty setting to initial mastery level
        initial_mastery = map_difficulty_to_mastery(initial_difficulty)
        
        # Create the initial state with the personalized theme
        initial_state = initialize_state(personalized_theme=request.personalized_theme)
        
        # If an initial topic is determined, set it in the state
        if initial_topic:
            initial_state["current_topic"] = initial_topic
            # Initialize mastery for this specific topic
            initial_state["topic_mastery"] = {initial_topic: initial_mastery}
        else:
            # If no specific topic, ensure default topic has initial mastery
            default_topic = initial_state["current_topic"]
            initial_state["topic_mastery"] = {default_topic: initial_mastery}

        # If there's an initial message from the user, add it to the history
        if request.initial_message:
            initial_state["messages"] = [HumanMessage(content=request.initial_message)]
        
        # Apply additional configurations if provided
        if request.config:
            if request.config.initial_cpa_phase:
                initial_state["current_cpa_phase"] = request.config.initial_cpa_phase.value # Ensure enum value is used

        # If diagnostic results are provided, apply them to the state
        if request.diagnostic_results:
            # Convert Pydantic model to dict, then create DiagnosticResult object
            diagnostic_dict = request.diagnostic_results.dict() 
            diagnostic_obj = create_diagnostic_result_from_json(diagnostic_dict)
            if diagnostic_obj:
                # This function modifies initial_state in place
                apply_diagnostic_to_state(initial_state, diagnostic_obj) 
            else:
                print(f"Warning: Could not process provided diagnostic results for session {session_id}.")

        # Make sure we set the initial node to determine_next_step
        initial_state["next"] = "determine_next_step"

        # Run the compiled graph with the initial state
        print(f"Starting new session {session_id} with topic: {initial_state.get('current_topic', 'N/A')}, mastery: {initial_state.get('topic_mastery', {}).get(initial_state.get('current_topic', ''), 'N/A')}")
        # The graph execution starts, usually leading to the first agent output
        result_state = await compiled_app.ainvoke(initial_state)
        
        # After getting the initial output, clear the next state to prevent automatic execution
        if "next" in result_state:
            del result_state["next"]
            
        # Make sure not to proceed to evaluation automatically
        if result_state.get("current_step_output", {}).get("prompt_for_answer", False):
            # If this is prompting for an answer, store that fact but don't auto-progress
            print(f"Session {session_id} initialized with a practice problem. Waiting for user input before evaluation.")
        
        # Store the updated state in our active sessions dictionary
        active_sessions[session_id] = {
            "state": result_state, 
            "created_at": time.time(),
            "last_updated": time.time()
        }
        
        # If diagnostic results were provided, store them alongside the state
        if request.diagnostic_results:
            active_sessions[session_id]["diagnostic_results"] = request.diagnostic_results.dict()
        
        # Prepare the response using the output generated by the graph run
        agent_output = AgentOutput(**result_state.get("current_step_output", {}))
        
        return StartSessionResponse(
            session_id=session_id, 
            initial_output=agent_output,
            status="active" # Indicate the session is now active
        )
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error starting session: {str(e)}")
        import traceback
        traceback.print_exc() # Print the full traceback
        # Raise an HTTP exception to inform the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to start session: {str(e)}"
        )
    
@router.post("/{session_id}/process", response_model=ProcessInputResponse)
async def process_input(
    session_id: str, 
    request: ProcessInputRequest = Body(...),
    response: Response = None # Inject Response object to set headers
):
    """
    Processes user input for an active session.
    
    - Verifies that the session exists.
    - Adds the user's message to the state's message history.
    - Runs the graph with the updated state to get the next agent action/response.
    
    Args:
        session_id: The ID of the active session.
        request: Contains the user's message input.
        response: FastAPI Response object for setting headers.
        
    Returns:
        ProcessInputResponse: Contains the agent's output after processing the input.
    """
    # Verify that the session ID exists in our active sessions
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found. Please start a new session."
        )

    try:
        # Retrieve the session data (which includes the state)
        session_data = active_sessions[session_id]
        current_state = session_data["state"]
        
        # Add the user's new message to the message history in the state
        if "messages" not in current_state:
            current_state["messages"] = [] # Initialize if it doesn't exist
        
        # Append the new HumanMessage
        current_state["messages"].append(HumanMessage(content=request.message))
        
        # --- Determine how to resume the graph ---
        # Get the output from the *previous* step to see if it expected an answer
        last_output = current_state.get("current_step_output", {})
        
        # CLEAR DECISION: If the previous output was a question/practice problem
        # then route to evaluation, otherwise to the decision node
        if last_output.get("prompt_for_answer", False):
            print(f"User provided answer for session {session_id}. Routing to evaluation...")
            # Explicitly set the next node to evaluate_answer
            current_state["next"] = "evaluate_answer"
        else:
            # For regular conversation, start with determine_next_step
            current_state["next"] = "determine_next_step"
            print(f"Regular input for session {session_id}. Routing to decision node...")

        # Execute the graph with the updated state (including the new user message)
        start_time = time.time()
        print(f"Processing input for session {session_id}. Current topic: {current_state.get('current_topic')}, Phase: {current_state.get('current_cpa_phase')}")
        
        # Invoke the compiled graph asynchronously
        result_state = await compiled_app.ainvoke(current_state)
        
        # After processing, clear the next state to prevent automatic execution
        if "next" in result_state:
            del result_state["next"]
        
        # Update the session data with the new state returned by the graph
        session_data["state"] = result_state
        session_data["last_updated"] = time.time() # Update the timestamp
        
        # Prepare the response for the client
        agent_output_data = result_state.get("current_step_output", {})
        agent_output = AgentOutput(**agent_output_data)
        
        # Get the current mastery level for the response
        current_topic = result_state.get("current_topic", "")
        mastery_level = result_state.get("topic_mastery", {}).get(current_topic, 0.0)
        
        # Log performance
        processing_time = time.time() - start_time
        print(f"Processed input in {processing_time:.2f} seconds for session {session_id}")
        
        # Set a custom header for monitoring processing time (optional)
        if response:
            response.headers["X-Processing-Time"] = f"{processing_time:.2f}"
        
        return ProcessInputResponse(
            session_id=session_id, 
            agent_output=agent_output,
            mastery_level=mastery_level # Include current mastery in response
        )
        
    except Exception as e:
        # Log errors and return a server error response
        print(f"Error processing input for session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to process input: {str(e)}"
        )
    
@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Retrieves the current status of an active session, including progress information.
    
    Args:
        session_id: The ID of the session.
        
    Returns:
        SessionStatusResponse: Information about the session's current state.
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
    current_cpa_phase = current_state.get("current_cpa_phase", "Concrete") # Default if not set
    
    # Construct and return the status response
    return SessionStatusResponse(
        session_id=session_id,
        current_topic=current_topic,
        mastery_levels=topic_mastery, # Dictionary of mastery levels per topic
        current_cpa_phase=current_cpa_phase,
        is_active=True, # Assumed active if found
        created_at=session_data.get("created_at"),
        last_updated=session_data.get("last_updated")
    )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: str):
    """
    Ends an active session and removes it from memory (or marks as inactive).
    
    Args:
        session_id: The ID of the session to end.
    """
    # Check if the session exists
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
    
    # In a real system, we might archive session data for analysis before deleting
    print(f"Ending session {session_id}")
    
    # Remove the session from the in-memory dictionary
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
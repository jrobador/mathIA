from fastapi import APIRouter, HTTPException, Body
from app.schemas.session import (
    StartSessionRequest, StartSessionResponse,
    ProcessInputRequest, ProcessInputResponse, AgentOutput
)
from app.agent.graph import build_math_tutor_graph
from app.agent.state import StudentSessionState, CPAPhase # Import necessary types
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import uuid
from typing import Dict, Any

router = APIRouter()

# In-memory storage for active sessions (Hackathon approach)
# Store the compiled app and the *current state*
active_sessions: Dict[str, Dict[str, Any]] = {}

# Build the graph once (can be reused if stateless, but stateful needs instances)
# For simplicity, we rebuild on start, but could cache the compiled graph structure
# compiled_app = build_math_tutor_graph().compile() # Compile once if possible

@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest = Body(...)):
    """Starts a new learning session."""
    session_id = str(uuid.uuid4())

    try:
        # Compile a new graph instance for the session
        graph = build_math_tutor_graph()
        app = graph.compile()

        # Define initial state
        initial_state: StudentSessionState = {
            "messages": [],
            "current_topic": "fractions_introduction", # Or get from request
            "current_cpa_phase": CPAPhase.CONCRETE,
            "topic_mastery": {"fractions_introduction": 0.1},
            "consecutive_correct": 0,
            "consecutive_incorrect": 0,
            "error_feedback_given_count": 0,
            "last_action_type": None,
            "last_evaluation": None,
            "last_problem_details": None,
            "current_step_output": {}, # Will be populated by first run
            "personalized_theme": request.personalized_theme or "espacio",
            "next": None # Add 'next' key for conditional edges
        }

        # Run the graph once to get the initial message/state
        # The graph should start at 'determine_next_step'
        result_state = await app.ainvoke(initial_state)

        # Store the app and the latest state
        active_sessions[session_id] = {"app": app, "state": result_state}

        # Prepare response
        agent_output = AgentOutput(**result_state.get("current_step_output", {}))

        return StartSessionResponse(session_id=session_id, initial_output=agent_output)

    except Exception as e:
        print(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start session")


@router.post("/{session_id}/process", response_model=ProcessInputResponse)
async def process_input(session_id: str, request: ProcessInputRequest = Body(...)):
    """Processes user input for an active session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = active_sessions[session_id]
    app = session_data["app"]
    current_state: StudentSessionState = session_data["state"]

    # Add user message to the state's message history
    # Ensure messages list exists and is mutable
    if 'messages' not in current_state or current_state['messages'] is None:
        current_state['messages'] = []
    current_state["messages"].append(HumanMessage(content=request.message))

    try:
        # --- Hackathon Logic (Option 3 from previous thought process) ---
        # Determine where to re-invoke the graph.
        # If the last output prompted for an answer, we invoke 'evaluate_answer' directly.
        # Otherwise, we invoke the entry point ('determine_next_step') or follow 'next'.

        last_output = current_state.get("current_step_output", {})
        start_node = "determine_next_step" # Default start

        if last_output.get("prompt_for_answer"):
            print(f"User provided answer for session {session_id}. Invoking evaluate_answer.")
            # We need to directly call the evaluation node.
            # This bypasses the graph's normal entry point for this specific case.
            # Note: ainvoke typically starts from the entry point or resumes.
            # Directly invoking a specific node might need different LangGraph setup
            # or manual function call followed by invoke.
            # Simplification: Let's assume evaluate_answer is always reachable from determine_next_step
            # and the state contains enough info for determine_next_step to route correctly
            # *after* the user message is added. We just reinvoke normally.
            pass # Let the normal invoke handle routing based on updated state


        # Invoke the graph with the updated state
        # The graph's internal logic (determine_next_step) should route correctly now
        # because the user message is in the history and last_action_type might indicate practice
        result_state = await app.ainvoke(current_state)

        # Update the stored state for the session
        active_sessions[session_id]["state"] = result_state

        # Prepare response
        agent_output = AgentOutput(**result_state.get("current_step_output", {}))

        return ProcessInputResponse(session_id=session_id, agent_output=agent_output)

    except Exception as e:
        print(f"Error processing input for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to process input")
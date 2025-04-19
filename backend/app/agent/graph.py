from langgraph.graph import StateGraph, END
from app.agent.state import StudentSessionState
from app.agent.nodes import (
    determine_next_step,
    present_theory,
    present_guided_practice,
    present_independent_practice,
    evaluate_answer,
    provide_targeted_feedback,
    check_advance_topic,
)

def should_continue(state: StudentSessionState) -> str:
    """Determines the next node based on the output of the previous node."""
    # The 'next' key should be populated by the node functions
    next_node = state.get("current_step_output", {}).get("next") # Check if node returned 'next'
    if next_node:
        return next_node

    # Fallback or specific logic if 'next' isn't directly provided
    # Example: if last action was practice, next is evaluate (handled by API structure)
    # If we just evaluated, the decision logic node runs.
    # Let's assume the node returns {"next": "node_name"}
    raise ValueError("Node did not specify the next step")

def build_math_tutor_graph() -> StateGraph:
    """
    Construye y retorna el grafo del agente tutor de matemáticas.
    """
    graph = StateGraph(StudentSessionState)

    # Add nodes
    graph.add_node("determine_next_step", determine_next_step)
    graph.add_node("present_theory", present_theory)
    graph.add_node("present_guided_practice", present_guided_practice)
    graph.add_node("present_independent_practice", present_independent_practice)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("provide_targeted_feedback", provide_targeted_feedback)
    graph.add_node("check_advance_topic", check_advance_topic)

    # --- Define Edges ---

    # Entry point
    graph.set_entry_point("determine_next_step")

    # Conditional edges from the main decision node
    graph.add_conditional_edges(
        "determine_next_step",
        # Function to determine the path (extracts 'next' from state, set by the node)
        lambda state: state.get("next"), # The node function should return {"next": "node_name"}
        {
            "present_theory": "present_theory",
            "present_guided_practice": "present_guided_practice",
            "present_independent_practice": "present_independent_practice",
            "provide_targeted_feedback": "provide_targeted_feedback",
            "check_advance_topic": "check_advance_topic",
            # Add END possibility if decision node can end it
            END: END,
        }
    )

    # Edges FROM action/evaluation nodes BACK to decision making or END

    # After theory is presented, decide what's next
    graph.add_edge("present_theory", "determine_next_step")

    # After feedback is provided, decide what's next
    graph.add_edge("provide_targeted_feedback", "determine_next_step")

    # After evaluation is done, decide what's next
    graph.add_edge("evaluate_answer", "determine_next_step")

    # After checking advancement
    graph.add_edge("check_advance_topic", "determine_next_step") # If advancing, decide next step for new topic
    # The END edge from check_advance_topic is handled conditionally above

    # Nodes that require user input (practice) don't have automatic outgoing edges here.
    # The API endpoint for processing input will invoke the 'evaluate_answer' node.
    # We need a way to compile this graph correctly. Let's re-evaluate the node returns.
    # The node functions should return the *updated state dictionary* directly.
    # The conditional edge logic will then operate on the *result* of the node.

    # --- Revised Edge Logic ---
    # Let nodes return the full state dictionary.
    # Edges will be defined based on that state or explicit 'next' key if needed.

    # Let's stick to the pattern where nodes return {"next": "node_name"} for clarity.

    # Re-verify node returns:
    # - determine_next_step: Returns {"next": "target_node_name"}
    # - present_theory: Returns {"next": "determine_next_step"}
    # - present_guided_practice: Returns state (API triggers eval) - Needs adjustment for graph flow.
    # - present_independent_practice: Returns state (API triggers eval) - Needs adjustment.
    # - evaluate_answer: Returns {"next": "determine_next_step"}
    # - provide_targeted_feedback: Returns {"next": "determine_next_step"}
    # - check_advance_topic: Returns {"next": "determine_next_step"} or {"next": END}

    # **How to handle the wait for user input within LangGraph?**
    # Option 1: Use `interrupt_before=["evaluate_answer"]`. The API calls `ainvoke`, it runs until the interrupt, returns the state. API sends response to frontend. Frontend sends user input back. API calls `ainvoke` *again* with the *interrupted state* + user message. This requires state persistence or passing state back and forth.
    # Option 2: Split the graph. One graph for deciding and presenting, another for evaluating. The API manages switching. Too complex for hackathon.
    # Option 3 (Hackathon Simplification): The graph *always* flows back to `determine_next_step`. The API knows if the last output had `prompt_for_answer=True`. If so, the *next* call to the API (`/process`) will *first* manually bundle the user message with the current state and *then* invoke the graph starting from `evaluate_answer`. This bypasses the standard graph flow temporarily but keeps graph simple.

    # Let's go with Option 3 for simplicity, but acknowledge it's not pure LangGraph flow.
    # We will design the API endpoint to handle this logic.
    # The graph definition itself can assume a direct flow back to decision making after evaluation.

    print("Graph built successfully.")
    return graph
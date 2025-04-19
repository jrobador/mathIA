# backend/app/agent/graph.py

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

# Helper function for conditional edge logic (extracts 'next' from state)
def route_based_on_state(state: StudentSessionState) -> str:
    """Determines the next node based on the 'next' key in the state."""
    next_node = state.get("next")
    if not next_node:
         # This should ideally not happen if nodes always set 'next' before returning
         # or if the graph logic handles states where 'next' is missing (like waiting)
         print("Warning: 'next' key not found in state for routing.")
         # Decide a fallback? Or maybe this indicates a wait state?
         # For now, assume it should always be set by the previous node if transition is needed.
         # If the previous node was practice, the API handles the next step (evaluate).
         # If the graph reaches here without 'next', maybe default to decision?
         return "determine_next_step" # Fallback?
    return next_node


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

    # Conditional edges FROM decision nodes based on the 'next' value set in the state
    graph.add_conditional_edges(
        "determine_next_step",
        route_based_on_state, # Use the helper function
        {
            "present_theory": "present_theory",
            "present_guided_practice": "present_guided_practice",
            "present_independent_practice": "present_independent_practice",
            "provide_targeted_feedback": "provide_targeted_feedback",
            "check_advance_topic": "check_advance_topic",
            "__end__": END # Map the special string to the actual END constant
        }
    )

    graph.add_conditional_edges(
        "check_advance_topic",
        route_based_on_state, # Use the helper function
        {
            "determine_next_step": "determine_next_step",
            "__end__": END # Map the special string to the actual END constant
        }
    )


    # Simple edges FROM action/evaluation nodes BACK to the decision node
    # These nodes *always* go back to decide what's next
    graph.add_edge("present_theory", "determine_next_step")
    graph.add_edge("evaluate_answer", "determine_next_step")
    graph.add_edge("provide_targeted_feedback", "determine_next_step")


    # **Important:** No edges ORIGINATING from `present_guided_practice`
    # or `present_independent_practice` because the graph pauses here.
    # The API call handling the user's answer will trigger the `evaluate_answer` node's execution
    # (or more accurately, it will reinvoke the graph, and the state+message history will
    # likely lead `determine_next_step` to call `evaluate_answer` if designed that way, OR
    # the API could potentially invoke `evaluate_answer` directly if the framework allows).
    # Our API logic currently reinvokes normally, relying on the state update.

    print("Graph built successfully with END mapping.")
    return graph
# -*- coding: utf-8 -*-
from langgraph.graph import StateGraph, END # Core LangGraph classes for building stateful graphs
from app.agent.state import StudentSessionState # The defined state object for the graph
from app.agent.nodes import ( # Import the node functions defined in another file
    determine_next_step,
    present_theory,
    present_guided_practice,
    present_independent_practice,
    evaluate_answer,
    provide_targeted_feedback,
    check_advance_topic,
    wait_for_input
)

def route_based_on_next(state: StudentSessionState) -> str:
    """
    Determines the next node to execute based on the 'next' value stored in the state.
    This function is used for conditional routing within the graph.
    
    Args:
        state: The current state of the graph.
        
    Returns:
        A string representing the name of the next node to execute, or END.
    """
    next_node = state.get("next") # Get the 'next' value set by the previous node
    
    if not next_node:
        # Fallback if 'next' is not defined in the state (should generally not happen if nodes set it)
        print("Warning: No 'next' key found in state. Defaulting to determine_next_step.")
        return "determine_next_step"
    
    # To handle the special case of graph termination
    if next_node == "__end__":
        return END # Use the special END constant from LangGraph
    
    # Otherwise, return the name of the node specified in 'next'
    return next_node

def build_math_tutor_graph() -> StateGraph:
    """
    Builds and returns the StateGraph for the math tutor agent.
    Defines the nodes and edges of the conversational flow.
    
    Returns:
        A configured StateGraph instance.
    """
    print("Building the math tutor graph...")
    graph = StateGraph(StudentSessionState) # Initialize the graph with the defined state structure

    # Add nodes to the graph
    # Each node is associated with an async function that modifies the state
    graph.add_node("determine_next_step", determine_next_step)
    graph.add_node("present_theory", present_theory)
    graph.add_node("present_guided_practice", present_guided_practice)
    graph.add_node("present_independent_practice", present_independent_practice)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("provide_targeted_feedback", provide_targeted_feedback)
    graph.add_node("check_advance_topic", check_advance_topic)
    # BUGFIX: Add wait_for_input node
    graph.add_node("wait_for_input", wait_for_input)

    # --- Define Edges (Transitions between nodes) ---

    # Set the entry point of the graph
    graph.set_entry_point("determine_next_step")

    # Conditional edges from the main decision node ('determine_next_step')
    # The 'route_based_on_next' function will inspect the state and decide which node to go to next.
    graph.add_conditional_edges(
        "determine_next_step", # Source node
        route_based_on_next,   # Function to determine the route based on state['next']
        {
            # Mapping from the value returned by 'route_based_on_next' to the target node name
            "present_theory": "present_theory",
            "present_guided_practice": "present_guided_practice",
            "present_independent_practice": "present_independent_practice",
            "provide_targeted_feedback": "provide_targeted_feedback",
            "check_advance_topic": "check_advance_topic",
            "evaluate_answer": "evaluate_answer",
            "wait_for_input": "wait_for_input",  # BUGFIX: Add edge to wait_for_input
            END: END  # Direct mapping to the END constant for termination
        }
    )

    # Add edges from practice nodes to the determine_next_step node
    graph.add_edge("present_guided_practice", "determine_next_step")
    
    # BUGFIX: No edge from present_independent_practice - it now goes to wait_for_input

    # Conditional edges for 'check_advance_topic' node
    # This node can either loop back to the decision node or end the graph.
    graph.add_conditional_edges(
        "check_advance_topic", # Source node
        route_based_on_next,   # Routing function
        {
            # Possible outcomes set in state['next'] by check_advance_topic
            "determine_next_step": "determine_next_step", # Go back to decide next action for new topic
            END: END # End the graph if roadmap is complete
        }
    )

    # Simple edges from nodes that always lead back to the main decision node
    graph.add_edge("present_theory", "determine_next_step")
    graph.add_edge("provide_targeted_feedback", "determine_next_step")
    
    # The evaluate_answer node should also return to determine_next_step after processing
    graph.add_edge("evaluate_answer", "determine_next_step")
    
    # BUGFIX: wait_for_input has no outgoing edges, it's a terminal node for each session iteration

    print("Graph built successfully.")
    return graph

# Singleton pattern: Build and compile the graph once to improve performance for subsequent requests.
_compiled_app = None

def get_compiled_app():
    """
    Builds the graph and compiles it once for reuse.
    Subsequent calls will return the already compiled application.
    Useful for reusing the graph structure efficiently between sessions/requests.
    
    Returns:
        The compiled LangGraph application.
    """
    global _compiled_app
    if _compiled_app is None:
        print("Compiling graph for the first time...")
        graph = build_math_tutor_graph()
        _compiled_app = graph.compile()
        print("Graph compiled.")
    return _compiled_app
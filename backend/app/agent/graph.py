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

def route_based_on_next(state: StudentSessionState) -> str:
    """
    Determina el siguiente nodo basado en el valor de 'next' en el estado.
    Esta función se usa para el enrutamiento condicional en el grafo.
    """
    next_node = state.get("next")
    if not next_node:
        # Fallback si no hay 'next' definido
        print("Warning: No 'next' key found in state. Defaulting to determine_next_step.")
        return "determine_next_step"
    
    # Para manejar el caso especial de finalización
    if next_node == "__end__":
        return END
    
    return next_node

def build_math_tutor_graph() -> StateGraph:
    """
    Construye y retorna el grafo del agente tutor de matemáticas.
    """
    print("Building the math tutor graph...")
    graph = StateGraph(StudentSessionState)

    # Añadir nodos
    graph.add_node("determine_next_step", determine_next_step)
    graph.add_node("present_theory", present_theory)
    graph.add_node("present_guided_practice", present_guided_practice)
    graph.add_node("present_independent_practice", present_independent_practice)
    graph.add_node("evaluate_answer", evaluate_answer)
    graph.add_node("provide_targeted_feedback", provide_targeted_feedback)
    graph.add_node("check_advance_topic", check_advance_topic)

    # --- Definir Bordes ---

    # Punto de entrada
    graph.set_entry_point("determine_next_step")

    # Bordes condicionales desde el nodo de decisión principal
    graph.add_conditional_edges(
        "determine_next_step",
        route_based_on_next,  # Función para determinar la ruta basada en 'next'
        {
            "present_theory": "present_theory",
            "present_guided_practice": "present_guided_practice",
            "present_independent_practice": "present_independent_practice",
            "provide_targeted_feedback": "provide_targeted_feedback",
            "check_advance_topic": "check_advance_topic",
            END: END  # Mapeo directo al END constante
        }
    )

    # Bordes condicionales para check_advance_topic
    graph.add_conditional_edges(
        "check_advance_topic",
        route_based_on_next,
        {
            "determine_next_step": "determine_next_step",
            END: END
        }
    )

    # Bordes simples desde nodos hacia determine_next_step
    graph.add_edge("present_theory", "determine_next_step")
    graph.add_edge("provide_targeted_feedback", "determine_next_step")
    
    # El nodo evaluate_answer también debería volver a determine_next_step
    graph.add_edge("evaluate_answer", "determine_next_step")

    # Los nodos que requieren input del usuario (present_guided_practice, present_independent_practice)
    # no tienen bordes automáticos. La API gestionará esto como se describe abajo.

    print("Graph built successfully.")
    return graph

def get_compiled_app():
    """
    Construye el grafo y lo compila una sola vez para reutilizarlo.
    Útil para reutilizar la estructura del grafo entre sesiones.
    """
    graph = build_math_tutor_graph()
    return graph.compile()
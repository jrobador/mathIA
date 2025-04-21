import pytest
from unittest.mock import patch, AsyncMock
from app.agent.state import CPAPhase

@pytest.mark.asyncio
async def test_complete_learning_path():
    """Test progression through a complete learning path with graph integration."""
    # Setup initial state for a complete learning journey
    initial_state = {
        "current_topic": "fractions_introduction",
        "current_cpa_phase": CPAPhase.CONCRETE.value,
        "topic_mastery": {"fractions_introduction": 0.1},
        "theory_presented_for_topics": [],
        "consecutive_correct": 0,
        "consecutive_incorrect": 0,
        "personalized_theme": "space"
    }
    
    # Get the compiled graph app
    with patch('app.agent.graph.get_compiled_app') as mock_get_app:
        mock_app = AsyncMock()
        mock_get_app.return_value = mock_app
        
        # Counter to track number of invocations
        invocation_count = [0]
        
        # Setup mock to simulate topic advancement after enough steps
        async def simulate_graph_execution(state):
            # Track calls to change behavior
            invocation_count[0] += 1
            
            # First invocation just increases mastery
            if invocation_count[0] < 3:
                state["consecutive_correct"] = state.get("consecutive_correct", 0) + 1
                topic = state.get("current_topic")
                state["topic_mastery"][topic] = min(1.0, state["topic_mastery"].get(topic, 0) + 0.2)
                state["next"] = "present_independent_practice"
            # Third invocation advances the topic
            else:
                # Force topic advancement
                state["current_topic"] = "fractions_equivalent"  # New topic
                state["topic_mastery"]["fractions_equivalent"] = 0.1  # Initialize new topic mastery
                state["consecutive_correct"] = 0
                state["next"] = "present_theory"
            
            state["current_step_output"] = {
                "text": f"Processing topic {state.get('current_topic')} with mastery {state['topic_mastery'].get(state.get('current_topic'), 0)}",
                "prompt_for_answer": True
            }
            
            return state
            
        mock_app.ainvoke.side_effect = simulate_graph_execution
        
        # Execute graph multiple times to simulate learning progression
        from app.agent.graph import get_compiled_app
        graph = get_compiled_app()
        
        # First step 
        state = await graph.ainvoke(initial_state)
        assert state["current_topic"] == "fractions_introduction"
        
        # Second step
        state = await graph.ainvoke(state)
        assert state["current_topic"] == "fractions_introduction"
        
        # Third step - should advance topic
        state = await graph.ainvoke(state)
        assert state["current_topic"] == "fractions_equivalent"  # Now topic has changed
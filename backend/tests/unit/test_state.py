from app.agent.state import (
    CPAPhase, EvaluationOutcome,
    initialize_state, get_current_mastery, update_mastery
)
from langchain_core.messages import HumanMessage, AIMessage

class TestStateManagement:
    """Tests for state initialization and management functions."""
    
    def test_initialize_state(self):
        """Test initializing a new student session state."""
        # Default initialization
        state = initialize_state()
        
        # Check required keys
        assert "current_topic" in state
        assert "current_cpa_phase" in state
        assert "topic_mastery" in state
        assert "consecutive_correct" in state
        assert "consecutive_incorrect" in state
        assert "personalized_theme" in state
        
        # Check default values
        assert state["current_topic"] == "fractions_introduction"
        assert state["current_cpa_phase"] == CPAPhase.CONCRETE.value
        assert state["topic_mastery"]["fractions_introduction"] == 0.1
        assert state["consecutive_correct"] == 0
        assert state["consecutive_incorrect"] == 0
        
        # Check initialization with specific theme
        space_state = initialize_state(personalized_theme="space")
        assert space_state["personalized_theme"] == "space"
        
        ocean_state = initialize_state(personalized_theme="ocean")
        assert ocean_state["personalized_theme"] == "ocean"
    
    def test_get_current_mastery(self):
        """Test retrieving current mastery level from state."""
        # Create test state
        state = {
            "current_topic": "fractions_introduction",
            "topic_mastery": {
                "fractions_introduction": 0.5,
                "fractions_equivalent": 0.3
            }
        }
        
        # Test getting mastery for current topic
        assert get_current_mastery(state) == 0.5
        
        # Test with missing topic_mastery
        state_no_mastery = {"current_topic": "fractions_introduction"}
        assert get_current_mastery(state_no_mastery) == 0.0
        
        # Test with unknown topic
        state["current_topic"] = "unknown_topic"
        assert get_current_mastery(state) == 0.0
        
    def test_update_mastery(self):
        """Test updating mastery levels in state."""
        # Create initial state
        state = {
            "current_topic": "fractions_introduction",
            "topic_mastery": {
                "fractions_introduction": 0.5
            }
        }
        
        # Test positive update
        update_mastery(state, 0.1)
        assert round(state["topic_mastery"]["fractions_introduction"], 1) == 0.6  # Round to fix floating point issue
        
        # Test negative update
        update_mastery(state, -0.2)
        assert round(state["topic_mastery"]["fractions_introduction"], 1) == 0.4
    
    def test_enums(self):
        """Test enum values and conversions."""
        # CPAPhase enum values
        assert CPAPhase.CONCRETE.value == "Concrete"
        assert CPAPhase.PICTORIAL.value == "Pictorial"
        assert CPAPhase.ABSTRACT.value == "Abstract"
        
        # EvaluationOutcome enum values
        assert EvaluationOutcome.CORRECT.value == "Correct"
        assert EvaluationOutcome.INCORRECT_CONCEPTUAL.value == "Incorrect_Conceptual"
        assert EvaluationOutcome.INCORRECT_CALCULATION.value == "Incorrect_Calculation"
        assert EvaluationOutcome.UNCLEAR.value == "Unclear"
    
    def test_state_with_messages(self):
        """Test state with message history."""
        # Create initial state with messages
        state = initialize_state()
        state["messages"] = [
            HumanMessage(content="Hello, I want to learn fractions"),
            AIMessage(content="Great! Let's start with the basics of fractions")
        ]
        
        # Add a message
        state["messages"].append(HumanMessage(content="What's a fraction?"))
        
        # Verify messages
        assert len(state["messages"]) == 3
        assert state["messages"][0].content == "Hello, I want to learn fractions"
        assert state["messages"][2].content == "What's a fraction?"
        
        # Verify message types
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)
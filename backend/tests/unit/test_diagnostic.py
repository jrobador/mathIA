import pytest
from app.agent.diagnostic import (
    DifficultySetting, DiagnosticResult, difficulty_to_mastery_level,
    apply_diagnostic_to_state, create_diagnostic_result_from_json
)

class TestDiagnosticFunctions:
    """Tests for diagnostic result processing and application."""
    
    def test_difficulty_to_mastery_level(self):
        """Test conversion of difficulty settings to mastery levels."""
        # Test all enum values
        assert difficulty_to_mastery_level(DifficultySetting.INITIAL) == 0.1
        assert difficulty_to_mastery_level(DifficultySetting.BEGINNER) == 0.3
        assert difficulty_to_mastery_level(DifficultySetting.INTERMEDIATE) == 0.5
        assert difficulty_to_mastery_level(DifficultySetting.ADVANCED) == 0.7
        
        # Test fallback behavior
        assert difficulty_to_mastery_level("not_a_real_setting") == 0.1
    
    def test_create_diagnostic_result(self):
        """Test creation of DiagnosticResult from JSON data."""
        # Valid data
        data = {
            "score": 75.0,
            "correct_answers": 3,
            "total_questions": 4,
            "recommended_level": "intermediate",
            "question_results": [
                {"question_id": "q1", "correct": True, "concept_tested": "fractions_introduction"},
                {"question_id": "q2", "correct": True, "concept_tested": "fractions_equivalent"},
                {"question_id": "q3", "correct": False, "concept_tested": "fractions_comparison"}
            ]
        }
        
        result = create_diagnostic_result_from_json(data)
        
        assert result is not None
        assert result.score == 75.0
        assert result.correct_answers == 3
        assert result.total_questions == 4
        assert result.recommended_level == DifficultySetting.INTERMEDIATE
        assert len(result.question_results) == 3
        
        # Test invalid data
        invalid_data = "not a dictionary"
        assert create_diagnostic_result_from_json(invalid_data) is None
        
        # Test missing fields with defaults
        minimal_data = {
            "score": 50.0,
            "correct_answers": 2,
            "total_questions": 4,
            "recommended_level": "beginner"
        }
        
        minimal_result = create_diagnostic_result_from_json(minimal_data)
        assert minimal_result is not None
        assert minimal_result.question_results == []
    
    def test_diagnostic_result_properties(self):
        """Test DiagnosticResult calculated properties and methods."""
        # Create a diagnostic result with mixed correct/incorrect answers
        result = DiagnosticResult(
            score=60.0,
            correct_answers=3,
            total_questions=5,
            recommended_level=DifficultySetting.INTERMEDIATE,
            question_results=[
                {"question_id": "q1", "correct": True, "concept_tested": "fractions_introduction"},
                {"question_id": "q2", "correct": True, "concept_tested": "fractions_equivalent"},
                {"question_id": "q3", "correct": False, "concept_tested": "fractions_comparison"},
                {"question_id": "q4", "correct": True, "concept_tested": "fractions_equivalent"},
                {"question_id": "q5", "correct": False, "concept_tested": "fractions_comparison"}
            ]
        )
        
        # Test percent_correct calculation
        assert result.percent_correct == 60.0
        
        # Test strengths identification
        strengths = result.get_strengths()
        assert "fractions_introduction" in strengths
        assert "fractions_equivalent" in strengths
        assert len(strengths) == 2
        
        # Test weaknesses identification
        weaknesses = result.get_weaknesses()
        assert "fractions_comparison" in weaknesses
        assert len(weaknesses) == 1
        
        # Test to_dict conversion
        result_dict = result.to_dict()
        assert result_dict["score"] == 60.0
        assert result_dict["recommended_level"] == "intermediate"
        assert "strengths" in result_dict
        assert "weaknesses" in result_dict
    
    def test_apply_diagnostic_to_state(self):
        """Test application of diagnostic results to student state."""
        # Create a diagnostic result with BEGINNER level
        diagnostic = DiagnosticResult(
            score=30.0,
            correct_answers=1,
            total_questions=4,
            recommended_level=DifficultySetting.BEGINNER,
            question_results=[
                {"question_id": "q1", "correct": True, "concept_tested": "fractions_introduction"},
                {"question_id": "q2", "correct": False, "concept_tested": "fractions_equivalent"}
            ]
        )
        
        # Create initial state
        state = {
            "current_topic": "fractions_introduction",
            "topic_mastery": {}
        }
        
        # Apply diagnostic to state
        updated_state = apply_diagnostic_to_state(state, diagnostic)
        
        # Check if state was updated correctly
        assert updated_state["topic_mastery"]["fractions_introduction"] == 0.3  # From BEGINNER
        
        # Testing the actual behavior from the code which sets Pictorial for mastery 0.3
        # Let's check the code in app/agent/diagnostic.py:
        # if mastery < 0.3: state["current_cpa_phase"] = "Concrete"
        # elif mastery < 0.6: state["current_cpa_phase"] = "Pictorial"
        # else: state["current_cpa_phase"] = "Abstract"
        # Since 0.3 is equal or greater than 0.3, it gets set to Pictorial
        assert updated_state["current_cpa_phase"] == "Pictorial"  # For mastery level 0.3
        
        assert "diagnostic_results" in updated_state
        
        # Test with very low mastery (set initial to 0.1)
        very_basic_diagnostic = DiagnosticResult(
            score=10.0,
            correct_answers=0,
            total_questions=4,
            recommended_level=DifficultySetting.INITIAL,  # Maps to 0.1 mastery
            question_results=[]
        )
        
        concrete_state = apply_diagnostic_to_state(
            {"current_topic": "fractions_introduction"}, 
            very_basic_diagnostic
        )
        # With mastery 0.1 < 0.3, it should be Concrete
        assert concrete_state["current_cpa_phase"] == "Concrete"
def test_diagnostic_application():
    """Test the application of diagnostic results to student state."""
    from app.agent.diagnostic import create_diagnostic_result_from_json, apply_diagnostic_to_state
    
    # Create diagnostic data
    diagnostic_data = {
        "score": 75.0,
        "correct_answers": 3,
        "total_questions": 4,
        "recommended_level": "intermediate",
        "question_results": [
            {"question_id": "q1", "correct": True, "concept_tested": "fractions_introduction"},
            {"question_id": "q2", "correct": True, "concept_tested": "fractions_equivalent"},
            {"question_id": "q3", "correct": False, "concept_tested": "fractions_comparison"},
            {"question_id": "q4", "correct": True, "concept_tested": "fractions_addition"}
        ]
    }
    
    # Create state
    state = {
        "current_topic": "fractions_introduction",
        "topic_mastery": {}
    }
    
    # Create diagnostic result and apply to state
    diagnostic = create_diagnostic_result_from_json(diagnostic_data)
    updated_state = apply_diagnostic_to_state(state, diagnostic)
    
    # Verify state updates
    assert updated_state["topic_mastery"]["fractions_introduction"] == 0.5  # Intermediate level
    assert updated_state["current_cpa_phase"] == "Pictorial"  # Appropriate for intermediate
    assert "diagnostic_results" in updated_state
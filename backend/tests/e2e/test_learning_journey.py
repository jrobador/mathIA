# backend/tests/e2e/test_learning_journey.py

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from app.schemas.session import LearningPath, DiagnosticData, DifficultySetting
import uuid

class TestCompleteLearningJourney:
    """Test the complete student learning journey from start to mastery."""
    
    def test_full_learning_progression(self):
        """
        Test a complete learning flow from initial assessment to topic mastery.
        
        This test simulates:
        1. Starting with a diagnostic assessment
        2. Learning with theory presentation
        3. Practicing with guided exercises
        4. Independent practice with increasing difficulty
        5. Mastery building through correct answers
        6. Handling incorrect answers
        7. Eventually advancing to the next topic
        """
        client = TestClient(app)
        
        # --- Step 1: Start session with diagnostic assessment ---
        with patch('uuid.uuid4', return_value="journey-session-id"):
            # Create diagnostic results indicating beginner level
            diagnostic_data = {
                "score": 25.0,
                "correct_answers": 1,
                "total_questions": 4,
                "recommended_level": DifficultySetting.BEGINNER.value,
                "question_results": [
                    {"question_id": "q1", "correct": True, "concept_tested": "fractions_introduction"},
                    {"question_id": "q2", "correct": False, "concept_tested": "fractions_equivalent"},
                    {"question_id": "q3", "correct": False, "concept_tested": "fractions_comparison"},
                    {"question_id": "q4", "correct": False, "concept_tested": "fractions_addition"}
                ]
            }
            
            # Start session with diagnostic results
            response = client.post(
                "/session/start",
                json={
                    "personalized_theme": "space",
                    "learning_path": LearningPath.FRACTIONS.value,
                    "diagnostic_results": diagnostic_data
                }
            )
            
            # Verify session started successfully
            assert response.status_code == 200
            session_data = response.json()
            assert session_data["session_id"] == "journey-session-id"
        
        # --- Setup complete session state tracking ---
        session_state = {
            "current_topic": "fractions_introduction",
            "topic_mastery": {"fractions_introduction": 0.3},  # Beginner level
            "current_cpa_phase": "Concrete",
            "theory_presented_for_topics": [],
            "consecutive_correct": 0,
            "consecutive_incorrect": 0,
            "messages": []
        }
        
        # Mock the session for other API endpoints
        with patch('app.api.endpoints.session.active_sessions') as mock_sessions:
            mock_sessions.get.return_value = {
                "journey-session-id": {
                    "state": session_state,
                    "content_ready": True,
                    "created_at": 1682600000.0,
                    "last_updated": 1682600100.0
                }
            }
            mock_sessions.__getitem__.side_effect = lambda x: mock_sessions.get.return_value[x]
            
            # --- Step 2: First session should present theory ---
            with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                # Theory presentation response
                mock_invoke.return_value = {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.3},
                    "current_cpa_phase": "Concrete",
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "last_action_type": "present_theory",
                    "current_step_output": {
                        "text": "A fraction represents a part of a whole...",
                        "image_url": "http://example.com/fractions_image.png",
                        "prompt_for_answer": False
                    }
                }
                
                # Check session status
                status_response = client.get("/session/journey-session-id/status")
                assert status_response.status_code == 200
                
                # Update tracking state
                session_state.update(mock_invoke.return_value)
            
            # --- Step 3: Next, guided practice ---
            with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                # Guided practice response
                mock_invoke.return_value = {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.3},
                    "current_cpa_phase": "Concrete",
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "last_action_type": "present_guided_practice",
                    "last_problem_details": {
                        "problem": "If you have 2 equal parts and you take 1, what fraction do you have?",
                        "solution": "1/2"
                    },
                    "current_step_output": {
                        "text": "If you have 2 equal parts and you take 1, what fraction do you have?",
                        "image_url": "http://example.com/practice_image.png",
                        "prompt_for_answer": True
                    }
                }
                
                # Process an empty input to move forward
                response = client.post(
                    "/session/journey-session-id/process",
                    json={"message": "I'm ready to learn"}
                )
                
                assert response.status_code == 200
                assert response.json()["agent_output"]["prompt_for_answer"] == True
                
                # Update tracking state
                session_state.update(mock_invoke.return_value)
            
            # --- Step 4: Answer correctly ---
            with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                # Correct answer evaluation
                mock_invoke.return_value = {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.4},  # Increased mastery
                    "current_cpa_phase": "Concrete",
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "last_action_type": "evaluate_answer",
                    "last_evaluation": "Correct",
                    "consecutive_correct": 1,
                    "consecutive_incorrect": 0,
                    "current_step_output": {
                        "text": "Correct! 1/2 is the right answer.",
                        "evaluation": "Correct",
                        "prompt_for_answer": False
                    }
                }
                
                # Submit the answer
                response = client.post(
                    "/session/journey-session-id/process",
                    json={"message": "The answer is 1/2"}
                )
                
                assert response.status_code == 200
                assert response.json()["agent_output"]["evaluation"] == "Correct"
                
                # Update tracking state
                session_state.update(mock_invoke.return_value)
            
            # --- Step 5: Get an independent practice problem ---
            with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                # Independent practice problem
                mock_invoke.return_value = {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.4},
                    "current_cpa_phase": "Concrete",
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "last_action_type": "present_independent_practice",
                    "last_problem_details": {
                        "problem": "If a spaceship has 4 equal sections and astronauts occupy 3 sections, what fraction is occupied?",
                        "solution": "3/4"
                    },
                    "current_step_output": {
                        "text": "If a spaceship has 4 equal sections and astronauts occupy 3 sections, what fraction is occupied?",
                        "image_url": "http://example.com/spaceship_image.png",
                        "prompt_for_answer": True
                    }
                }
                
                # Process input to get the next problem
                response = client.post(
                    "/session/journey-session-id/process",
                    json={"message": "Let me try another problem"}
                )
                
                assert response.status_code == 200
                assert "spaceship" in response.json()["agent_output"]["text"]
                
                # Update tracking state
                session_state.update(mock_invoke.return_value)
            
            # --- Step 6: Answer incorrectly ---
            with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                # Incorrect answer evaluation
                mock_invoke.return_value = {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.35},  # Decreased mastery
                    "current_cpa_phase": "Concrete",
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "last_action_type": "evaluate_answer",
                    "last_evaluation": "Incorrect_Calculation",
                    "consecutive_correct": 0,
                    "consecutive_incorrect": 1,
                    "current_step_output": {
                        "text": "Not quite. You made a calculation error. The correct answer is 3/4.",
                        "evaluation": "Incorrect_Calculation",
                        "prompt_for_answer": False
                    }
                }
                
                # Submit incorrect answer
                response = client.post(
                    "/session/journey-session-id/process",
                    json={"message": "The answer is 1/4"}
                )
                
                assert response.status_code == 200
                assert response.json()["agent_output"]["evaluation"] == "Incorrect_Calculation"
                
                # Update tracking state
                session_state.update(mock_invoke.return_value)
            
            # --- Steps 7-9: Answer several problems correctly to build mastery ---
            for i in range(3):
                with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                    # Practice problem
                    mock_invoke.return_value = {
                        "current_topic": "fractions_introduction",
                        "topic_mastery": {"fractions_introduction": 0.35 + (i+1)*0.15},  # Increasing mastery
                        "current_cpa_phase": "Pictorial" if i > 0 else "Concrete",  # Phase progresses
                        "theory_presented_for_topics": ["fractions_introduction"],
                        "last_action_type": "evaluate_answer",
                        "last_evaluation": "Correct",
                        "consecutive_correct": i+1,
                        "consecutive_incorrect": 0,
                        "current_step_output": {
                            "text": f"Correct! Problem {i+1} solved correctly.",
                            "evaluation": "Correct",
                            "prompt_for_answer": False
                        }
                    }
                    
                    # Submit correct answer
                    response = client.post(
                        "/session/journey-session-id/process",
                        json={"message": f"The answer is {i+1}/4"}
                    )
                    
                    assert response.status_code == 200
                    assert response.json()["agent_output"]["evaluation"] == "Correct"
                    
                    # Update tracking state
                    session_state.update(mock_invoke.return_value)
            
            # --- Step 10: High mastery triggers topic advancement ---
            with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
                # Topic advancement
                mock_invoke.return_value = {
                    "current_topic": "fractions_equivalent",  # Advanced to next topic
                    "topic_mastery": {
                        "fractions_introduction": 0.85,
                        "fractions_equivalent": 0.1  # Initial mastery for new topic
                    },
                    "current_cpa_phase": "Concrete",  # Reset to concrete for new topic
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "last_action_type": "advance_topic",
                    "consecutive_correct": 0,
                    "consecutive_incorrect": 0,
                    "current_step_output": {
                        "text": "Excellent progress! You've mastered introduction to fractions. Let's move on to equivalent fractions.",
                        "prompt_for_answer": False
                    }
                }
                
                # Submit one more correct answer
                response = client.post(
                    "/session/journey-session-id/process",
                    json={"message": "I think I understand fractions now"}
                )
                
                assert response.status_code == 200
                # Check for topic advancement
                status_response = client.get("/session/journey-session-id/status")
                assert "fractions_equivalent" in status_response.json()["current_topic"]
                
                # Update tracking state
                session_state.update(mock_invoke.return_value)
            
            # --- Verify session status at the end ---
            status_response = client.get("/session/journey-session-id/status")
            status_data = status_response.json()
            
            # Verify progression
            assert status_data["current_topic"] == "fractions_equivalent"
            assert status_data["mastery_levels"]["fractions_introduction"] >= 0.8
            assert "fractions_equivalent" in status_data["mastery_levels"]
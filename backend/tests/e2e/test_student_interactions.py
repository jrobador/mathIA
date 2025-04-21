# backend/tests/e2e/test_student_interactions.py

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

class TestStudentInteractions:
    """Test realistic student interactions with the math tutor."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a properly mocked session."""
        # Define session data structure
        session_data = {
            "test-session-id": {
                "state": {
                    "current_topic": "fractions_introduction",
                    "current_cpa_phase": "Concrete",
                    "topic_mastery": {"fractions_introduction": 0.3},
                    "current_step_output": {
                        "text": "Let's learn about fractions!",
                        "prompt_for_answer": True
                    },
                    "theory_presented_for_topics": ["fractions_introduction"],
                    "consecutive_correct": 0,
                    "consecutive_incorrect": 0,
                    "messages": []
                },
                "created_at": 1682600000.0,
                "last_updated": 1682600100.0,
                "content_ready": True
            }
        }
        
        # Patch the active_sessions dictionary
        with patch('app.api.endpoints.session.active_sessions', session_data):
            yield session_data
    
    def test_correct_answer_progression(self, mock_session):
        """Test progression when student provides correct answers."""
        # Use TestClient for actual requests
        client = TestClient(app)
        
        # Patch the processing function directly
        with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
            # Set up the return value structure
            mock_invoke.return_value = {
                "current_topic": "fractions_introduction",
                "topic_mastery": {"fractions_introduction": 0.4},
                "consecutive_correct": 1,
                "consecutive_incorrect": 0,
                "last_evaluation": "Correct",
                "current_step_output": {
                    "text": "That's correct! Let's try another problem.",
                    "evaluation": "Correct",
                    "prompt_for_answer": True
                }
            }
            
            # Submit the request
            response = client.post(
                "/session/test-session-id/process",
                json={"message": "The answer is 1/2"}
            )
            
            # Verify the response
            assert response.status_code == 200
            data = response.json()
            assert data["agent_output"]["text"] == "That's correct! Let's try another problem."
            assert data["agent_output"]["evaluation"] == "Correct"
            
            # Verify the mock was called
            assert mock_invoke.called
    
    def test_incorrect_answer_feedback(self, mock_session):
        """Test feedback when student provides incorrect answers."""
        client = TestClient(app)
        
        # Patch processing function
        with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
            # Configure return value for incorrect answer
            mock_invoke.return_value = {
                "current_topic": "fractions_introduction",
                "topic_mastery": {"fractions_introduction": 0.2}, 
                "consecutive_correct": 0,
                "consecutive_incorrect": 1,
                "last_evaluation": "Incorrect_Conceptual",
                "current_step_output": {
                    "text": "Not quite right. Remember that when adding fractions, you need a common denominator.",
                    "evaluation": "Incorrect_Conceptual",
                    "prompt_for_answer": False
                }
            }
            
            # Submit the request
            response = client.post(
                "/session/test-session-id/process",
                json={"message": "The answer is 2/6"}
            )
            
            # Check the response
            assert response.status_code == 200
            data = response.json()
            assert data["agent_output"]["evaluation"] == "Incorrect_Conceptual"
            assert "Not quite right" in data["agent_output"]["text"]
            
            # Verify the mock was called
            assert mock_invoke.called
    
    def test_multiple_interactions_sequence(self, mock_session):
        """Test a sequence of interactions with varying answers."""
        client = TestClient(app)
        
        # Mock the processing function differently for each call
        with patch('app.api.endpoints.session.compiled_app.ainvoke') as mock_invoke:
            # Set up sequence of return values
            mock_invoke.side_effect = [
                # First call - correct answer
                {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.3},
                    "consecutive_correct": 1,
                    "consecutive_incorrect": 0,
                    "last_evaluation": "Correct",
                    "current_step_output": {
                        "text": "Correct! Well done.",
                        "evaluation": "Correct",
                        "prompt_for_answer": True
                    }
                },
                # Second call - incorrect answer
                {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.25},
                    "consecutive_correct": 0,
                    "consecutive_incorrect": 1,
                    "last_evaluation": "Incorrect_Calculation",
                    "current_step_output": {
                        "text": "You made a calculation error. Check your arithmetic.",
                        "evaluation": "Incorrect_Calculation",
                        "prompt_for_answer": False
                    }
                },
                # Third call - correct answer
                {
                    "current_topic": "fractions_introduction",
                    "topic_mastery": {"fractions_introduction": 0.35},
                    "consecutive_correct": 1,
                    "consecutive_incorrect": 0,
                    "last_evaluation": "Correct",
                    "current_step_output": {
                        "text": "That's right! Good job.",
                        "evaluation": "Correct",
                        "prompt_for_answer": True
                    }
                }
            ]
            
            # Make the first request
            response1 = client.post(
                "/session/test-session-id/process",
                json={"message": "The answer is 1/2"}
            )
            data1 = response1.json()
            assert data1["agent_output"]["evaluation"] == "Correct"
            
            # Make the second request
            response2 = client.post(
                "/session/test-session-id/process",
                json={"message": "The answer is 2/8"}
            )
            data2 = response2.json()
            assert data2["agent_output"]["evaluation"] == "Incorrect_Calculation"
            
            # Make the third request
            response3 = client.post(
                "/session/test-session-id/process",
                json={"message": "The answer is 3/4"}
            )
            data3 = response3.json()
            assert data3["agent_output"]["evaluation"] == "Correct"
            
            # Verify the mock was called three times
            assert mock_invoke.call_count == 3